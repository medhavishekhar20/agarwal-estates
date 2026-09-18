from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "agarwal_estates_secret_key"
DB_NAME = "database.db"

# ==========================================
# HARDCODED PRE-BUILT ADMIN CREDENTIALS
# ==========================================
ADMIN_USERNAME = "admin_master"
ADMIN_PIN = "1234"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer'
        )
    ''')
    
    # Audit Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user TEXT NOT NULL,
            action_route TEXT NOT NULL,
            details TEXT NOT NULL
        )
    ''')
    
    # NRI Inquiries Table
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

# ==========================================
# PUBLIC LOGIN (BUYER & EMPLOYEE ONLY)
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')  # Expects 'buyer' or 'employee'

        # Block any attempt to log in as Admin via public login
        if role == 'admin':
            flash("Admin login is disabled here. Use the secure portal link.", "danger")
            return redirect(url_for('login'))

        if role not in ['buyer', 'employee']:
            flash("Invalid role selected. Allowed: Buyer or Employee.", "danger")
            return redirect(url_for('login'))

        session['user'] = username
        session['role'] = role
        log_event(username, '/login', f'Logged in as {role}')
        flash(f'Successfully logged in as {role.capitalize()}!', 'success')
        return redirect(url_for('nri_desk'))

    return render_template('login.html')

# ==========================================
# PRE-BUILT SECRET ADMIN PORTAL
# ==========================================
@app.route('/secret-admin-portal', methods=['GET', 'POST'])
def secret_admin_login():
    """Hidden route for Admin authentication using pre-built code credentials."""
    if request.method == 'POST':
        entered_pin = request.form.get('admin_pin')
        
        if entered_pin == ADMIN_PIN:
            session['user'] = ADMIN_USERNAME
            session['role'] = 'admin'
            log_event(ADMIN_USERNAME, '/secret-admin-portal', 'Admin authenticated via master PIN')
            flash('Admin authentication successful.', 'success')
            return redirect(url_for('admin_inquiries'))
        else:
            log_event('UNKNOWN', '/secret-admin-portal', 'Failed Admin PIN attempt')
            flash('Invalid Security PIN.', 'danger')

    return render_template('admin_secret_login.html')

# ==========================================
# NRI DESK (BUYER & EMPLOYEE VIEW)
# ==========================================
@app.route('/nri-desk', methods=['GET', 'POST'])
def nri_desk():
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    # If Admin accesses this, redirect to Admin Inquiries Dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('admin_inquiries'))

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

    # Fetch inquiries submitted ONLY by the logged-in user
    cursor.execute('''
        SELECT * FROM nri_inquiries 
        WHERE username = ? 
        ORDER BY created_at DESC
    ''', (session.get('user'),))
    my_inquiries = cursor.fetchall()
    conn.close()

    return render_template('nri_desk.html', inquiries=my_inquiries)

# ==========================================
# ADMIN-ONLY INQUIRIES DASHBOARD
# ==========================================
@app.route('/admin/inquiries')
def admin_inquiries():
    if session.get('role') != 'admin':
        flash("Access Denied: Administrative privileges required.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM nri_inquiries ORDER BY created_at DESC')
    all_inquiries = cursor.fetchall()
    conn.close()

    log_event(session.get('user'), '/admin/inquiries', 'Viewed all NRI inquiries')
    return render_template('admin_inquiries.html', inquiries=all_inquiries)

@app.route('/logout')
def logout():
    user = session.get('user', 'Guest')
    log_event(user, '/logout', 'User logged out')
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
