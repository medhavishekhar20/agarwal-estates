import io
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "agarwal_estates_secret_key"
DB_NAME = "database.db"

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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS properties (
            property_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            location TEXT NOT NULL,
            sqft REAL NOT NULL,
            bhk INTEGER NOT NULL,
            bathrooms INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE properties ADD COLUMN username TEXT NOT NULL DEFAULT 'admin'")
    except sqlite3.OperationalError:
        pass

    cursor.execute("UPDATE audit_logs SET user = 'admin' WHERE user = 'Anonymous' OR user IS NULL OR user = ''")
        
    conn.commit()
    conn.close()

init_db()

def log_event(user, action_route, details):
    active_user = user or session.get('user') or 'admin'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (user, action_route, details)
        VALUES (?, ?, ?)
    ''', (active_user, action_route, details))
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

        # 1. Handle Admin Authentication
        if role == 'admin':
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['user'] = ADMIN_USERNAME
                session['role'] = 'admin'
                log_event(ADMIN_USERNAME, '/login', 'Admin logged in successfully')
                return redirect(url_for('price_predict'))
            else:
                flash("Invalid Admin username or password.", "danger")
                return redirect(url_for('login'))

        # 2. Handle Regular User / Buyer / Employer Authentication
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            log_event(user['username'], '/login', f'Logged in as {user["role"]}')
            return redirect(url_for('price_predict'))
        else:
            # Rejects invalid credentials and keeps the user on the login screen
            flash("Invalid username or password. Please try again.", "danger")
            return redirect(url_for('login'))

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

@app.route('/price_predict', methods=['GET', 'POST'])
def price_predict():
    if 'user' not in session:
        return redirect(url_for('login'))

    default_locations = [
        "Whitefield", "Koramangala", "Indiranagar", "HSR Layout", 
        "Electronic City", "Jayanagar", "JP Nagar", "Hebbal", 
        "Banashankari", "Marathahalli", "Yelahanka", "Sarjapur Road"
    ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM properties ORDER BY location ASC")
        rows = cursor.fetchall()
        conn.close()
        locations = [row['location'] for row in rows if row['location']]
        if not locations:
            locations = default_locations
    except Exception:
        locations = default_locations

    prediction = None

    if request.method == 'POST':
        location = request.form.get('location')
        sqft = float(request.form.get('sqft', 1200))
        bhk = int(request.form.get('bhk', 2))
        bathrooms = int(request.form.get('bathrooms', 2))

        estimated_val = round((sqft * 5500) + (bhk * 250000) + (bathrooms * 100000))

        prediction = {
            'location': location,
            'sqft': sqft,
            'bhk': bhk,
            'bathrooms': bathrooms,
            'price': estimated_val,
            'formatted_price': f"₹ {estimated_val:,.2f}"
        }

        log_event(session.get('user'), '/price_predict', f'Predicted price for {location}')

    return render_template('price_predict.html', locations=locations, prediction=prediction)

@app.route('/add_to_portfolio', methods=['POST'])
def add_to_portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session.get('user', 'admin')
    location = request.form.get('location')
    sqft = float(request.form.get('sqft', 0))
    bhk = int(request.form.get('bhk', 0))
    bathrooms = int(request.form.get('bathrooms', 0))
    price = float(request.form.get('price', 0))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO properties (username, location, sqft, bhk, bathrooms, price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (username, location, sqft, bhk, bathrooms, price))
    conn.commit()
    conn.close()

    log_event(username, '/add_to_portfolio', f'Saved property in {location} to portfolio')
    flash("Property saved to portfolio successfully!", "success")
    return redirect(url_for('portfolio'))

@app.route('/portfolio')
def portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session.get('user', 'admin')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM properties WHERE username = ?", (username,))
        properties = cursor.fetchall()
    except Exception:
        properties = []
    finally:
        conn.close()

    total_props = len(properties)
    total_val_num = sum([p['price'] for p in properties if p['price']]) if properties else 0
    formatted_total_val = f"₹ {total_val_num:,.2f}"
    
    avg_sqft_num = (sum([p['sqft'] for p in properties if p['sqft']]) / total_props) if total_props > 0 else 0
    formatted_avg_sqft = f"{avg_sqft_num:,.1f}"

    return render_template(
        'portfolio.html',
        properties=properties,
        total_properties=total_props,
        total_value=formatted_total_val,
        avg_sqft=formatted_avg_sqft
    )

@app.route('/nri-desk', methods=['GET', 'POST'])
@app.route('/nri_desk', methods=['GET', 'POST'])
def nri_desk():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST' and session.get('role') != 'admin':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        country = request.form.get('country')
        phone = request.form.get('phone')
        details = request.form.get('details')
        username = session.get('user', 'admin')

        cursor.execute('''
            INSERT INTO nri_inquiries (username, full_name, email, country, phone_number, inquiry_details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, full_name, email, country, phone, details))
        
        conn.commit()
        log_event(username, '/nri_desk', 'Submitted new NRI inquiry')
        flash("Your inquiry has been submitted successfully!", "success")

    if session.get('role') == 'admin':
        cursor.execute('SELECT * FROM nri_inquiries ORDER BY created_at DESC')
    else:
        cursor.execute('SELECT * FROM nri_inquiries WHERE username = ? ORDER BY created_at DESC', (session.get('user', 'admin'),))

    my_inquiries = cursor.fetchall()
    conn.close()

    return render_template('nri_desk.html', inquiries=my_inquiries)

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

@app.route('/dataset_management', methods=['GET', 'POST'])
def dataset_management():
    if session.get('role') != 'admin':
        flash("Access Denied.", "danger")
        return redirect(url_for('login'))

    table_html = None
    row_count = 0
    col_count = 0
    columns = []

    if request.method == 'POST':
        if 'dataset_file' not in request.files:
            flash("No file uploaded.", "danger")
            return redirect(request.url)
            
        file = request.files['dataset_file']
        
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.StringIO(file.stream.read().decode("utf-8", errors="ignore")))
                
                row_count = len(df)
                col_count = len(df.columns)
                columns = df.columns.tolist()
                
                table_html = df.to_html(
                    classes='table table-striped table-hover table-bordered align-middle',
                    index=False,
                    na_rep='N/A'
                )
                
                current_user = session.get('user', 'admin')
                log_event(current_user, '/dataset_management', f'Uploaded dataset: {file.filename}')
                flash(f"Dataset '{file.filename}' loaded successfully!", "success")
            except Exception as e:
                flash(f"Error processing CSV file: {str(e)}", "danger")
        else:
            flash("Please upload a valid .csv file.", "warning")

    return render_template(
        'dataset_management.html', 
        table_html=table_html, 
        row_count=row_count, 
        col_count=col_count,
        columns=columns
    )

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
