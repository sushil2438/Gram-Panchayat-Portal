from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- VILLAGER SECTION ---
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, phone, password) VALUES (?, ?, ?)', (name, phone, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "This phone number is already registered!"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE phone = ? AND password = ?', (phone, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('index'))
        else:
            return "Invalid Phone Number or Password!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        category = request.form['issue_category']
        description = request.form['description']
        conn.execute('INSERT INTO complaints (user_id, issue_category, description) VALUES (?, ?, ?)',
                     (session['user_id'], category, description))
        conn.commit()

    # Fetching with Date formatting
    my_complaints = conn.execute('''
        SELECT id, issue_category, description, status, sarpanch_reply, 
        datetime(created_at, 'localtime') as date 
        FROM complaints WHERE user_id = ? ORDER BY id DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('index.html', name=session['user_name'], complaints=my_complaints)


# --- ADMIN (SARPANCH) SECTION ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Galat Admin ID ya Password!"
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    # Advanced: URL filter check karega (?status=Pending)
    filter_status = request.args.get('status', 'All')
    conn = get_db_connection()
    
    query = '''
        SELECT complaints.id, users.name, users.phone, complaints.issue_category, 
               complaints.description, complaints.status, complaints.sarpanch_reply,
               datetime(complaints.created_at, 'localtime') as date
        FROM complaints
        JOIN users ON complaints.user_id = users.id
    '''
    if filter_status != 'All':
        query += f" WHERE complaints.status = '{filter_status}'"
    query += " ORDER BY complaints.id DESC"
    
    complaints = conn.execute(query).fetchall()
    conn.close()

    return render_template('admin_dashboard.html', complaints=complaints, current_filter=filter_status)

# Advanced: Ab sirf resolve nahi, reply bhi save hoga
@app.route('/update_complaint/<int:id>', methods=['POST'])
def update_complaint(id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
        
    new_status = request.form['status']
    reply = request.form['sarpanch_reply']
    
    conn = get_db_connection()
    conn.execute("UPDATE complaints SET status = ?, sarpanch_reply = ? WHERE id = ?", (new_status, reply, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)