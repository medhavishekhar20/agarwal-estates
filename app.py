import io
import os
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
    
    # Portfolio properties table
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

    # Global dataset properties table (for comparison directly from datasets)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dataset_properties (
            dataset_id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Pre-populate dataset_properties from local file if empty
    seed_dataset_from_file()

def seed_dataset_from_file():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM dataset_properties")
    count = cursor.fetchone()['count']
    
    if count == 0:
        file_path = "Bengaluru_House_Data.csv"
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                populate_dataset_table(df)
            except Exception as e:
                print(f"Error seeding dataset: {e}")
    conn.close()

def populate_dataset_table(df):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dataset_properties")  # Refresh existing records

    # Normalize standard dataset column names
    df.columns = [c.strip().lower() for c in df.columns]

    for _, row in df.iterrows():
        try:
            location = str(row.get('location', 'Unknown')).strip()
            
            # Extract square feet
            raw_sqft = str(row.get('total_sqft', 0))
            if '-' in raw_sqft:
                parts = raw_sqft.split('-')
                sqft = (float(parts[0].strip()) + float(parts[1].strip())) / 2
            else:
                sqft = float(raw_sqft)

            # Extract BHK from size/bhk column
            raw_size = str(row.get('size', '0'))
            bhk = int(raw_size.split()[0]) if raw_size.split()[0].isdigit() else 0

            # Extract Bathrooms
            bath = row.get('bath', 0)
            bathrooms = int(bath) if pd.notnull(bath) else 0

            # Price in Lakhs converted to full INR value
            price_lakhs = float(row.get('price', 0))
            price = price_lakhs * 100000

            if location and sqft > 0 and price > 0:
                cursor.execute('''
                    INSERT INTO dataset_properties (location, sqft, bhk, bathrooms, price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (location, sqft, bhk, bathrooms, price))
        except Exception:
            continue

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
        cursor.execute("SELECT DISTINCT location FROM dataset_properties ORDER BY location ASC")
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

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session.get('user', 'admin')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Pull dataset properties to compare directly from the dataset
    cursor.execute("SELECT dataset_id AS property_id, location, sqft, bhk, bathrooms, price FROM dataset_properties LIMIT 200")
    available_properties = cursor.fetchall()

    prop1 = None
    prop2 = None

    if request.method == 'POST':
        prop1_id = request.form.get('prop1_id')
        prop2_id = request.form.get('prop2_id')

        if prop1_id:
            cursor.execute("SELECT dataset_id AS property_id, location, sqft, bhk, bathrooms, price FROM dataset_properties WHERE dataset_id = ?", (prop1_id,))
            prop1 = cursor.fetchone()

        if prop2_id:
            cursor.execute("SELECT dataset_id AS property_id, location, sqft, bhk, bathrooms, price FROM dataset_properties WHERE dataset_id = ?", (prop2_id,))
            prop2 = cursor.fetchone()

        log_event(username, '/compare', f'Compared dataset properties ID {prop1_id} and ID {prop2_id}')

    conn.close()

    return render_template('compare.html', properties=available_properties, prop1=prop1, prop2=prop2)

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
                raw_bytes = file.stream.read()
                df = pd.read_csv(io.StringIO(raw_bytes.decode("utf-8", errors="ignore")))
                
                # Populate database table so updated dataset is used across the site
                populate_dataset_table(df)

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
                flash(f"Dataset '{file.filename}' loaded into application successfully!", "success")
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
