from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "agarwal_estates_secret_key"
DB_NAME = "database.db"

# Admin Credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpassword123"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user TEXT NOT NULL,
            action_route TEXT NOT NULL,
            details TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nri_inquiries (
            inquiry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            country TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            inquiry_details TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def log_event(user, action_route, details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (user, action_route, details)
        VALUES (?, ?, ?)
    ''', (user, action_route, details))
    conn.commit()
    conn.close()

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('price_predict'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if role == 'admin':
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['user'] = username
                session['role'] = 'admin'
                log_event(username, '/login', 'Admin logged in')
                return redirect(url_for('price_predict'))
            else:
                flash("Invalid Admin credentials.", "danger")
                return redirect(url_for('login'))

        # Check standard user database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            log_event(username, '/login', f'Logged in as {user["role"]}')
            return redirect(url_for('price_predict'))
        else:
            # Fallback direct session setup if testing without registered users
            session['user'] = username
            session['role'] = role
            log_event(username, '/login', f'Logged in as {role}')
            return redirect(url_for('price_predict'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'buyer')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           (username, password, role))
            conn.commit()
            flash("Account created successfully! Please sign in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists. Please pick another.", "danger")
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/price_predict')
def price_predict():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('price_predict.html')

@app.route('/compare')
def compare():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('compare.html')

@app.route('/emi')
def emi():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('emi.html')

@app.route('/portfolio')
def portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('portfolio.html')

@app.route('/nri-desk', methods=['GET', 'POST'])
def nri_desk():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        country = request.form.get('country')
        phone = request.form.get('phone')
        details = request.form.get('details')
        username = session.get('user')

        cursor.execute('''
            INSERT INTO nri_inquiries (username, full_name, email, country, phone_number, inquiry_details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, full_name, email, country, phone, details))
        
        conn.commit()
        log_event(username, '/nri-desk', 'Submitted new NRI inquiry')
        flash("Your inquiry has been submitted successfully!", "success")

    cursor.execute('''
        SELECT * FROM nri_inquiries 
        WHERE username = ? 
        ORDER BY created_at DESC
    ''', (session.get('user'),))
    my_inquiries = cursor.fetchall()
    conn.close()

    return render_template('nri_desk.html', inquiries=my_inquiries)

@app.route('/dataset_management')
def dataset_management():
    if session.get('role') != 'admin':
        flash("Access Denied.", "danger")
        return redirect(url_for('login'))
    return render_template('dataset_management.html')

@app.route('/audit_logs')
def audit_logs():
    if session.get('role') != 'admin':
        flash("Access Denied.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_logs ORDER BY timestamp DESC')
    logs = cursor.fetchall()
    conn.close()
    return render_template('audit_logs.html', logs=logs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
