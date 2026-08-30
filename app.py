import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'agarwal_estates_secure_key_999'

ADMIN_PIN = "1234"  # Default Admin PIN

# Global or Session-based dynamic portfolio storage
PORTFOLIO_DATA = [
    {'title': 'Luxury 3BHK Villa', 'location': 'Whitefield', 'type': 'Residential', 'purchase_price': '75,00,000', 'current_value': '85,00,000', 'status': 'Active'}
]

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('price_predict'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role', 'user')
        pin = request.form.get('admin_pin', '')

        if role == 'admin' and pin != ADMIN_PIN:
            flash("Invalid Admin PIN! Access denied.", "danger")
            return render_template('login.html')

        if username:
            session['user'] = username
            session['role'] = role
            return redirect(url_for('price_predict'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('name')
        role = request.form.get('role', 'user')
        pin = request.form.get('admin_pin', '')

        if role == 'admin' and pin != ADMIN_PIN:
            flash("Invalid Admin PIN! Cannot register as Admin.", "danger")
            return render_template('register.html')

        if username:
            session['user'] = username
            session['role'] = role
            return redirect(url_for('price_predict'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# PREDICT PRICE ROUTE
# ==========================================

@app.route('/price_predict', methods=['GET', 'POST'])
def price_predict():
    if 'user' not in session:
        return redirect(url_for('login'))

    prediction = None
    if request.method == 'POST':
        try:
            sqft = float(request.form.get('sqft', 1000))
            bhk = int(request.form.get('bhk', 2))
            bath = int(request.form.get('bathrooms', 2))
            location = request.form.get('location', 'General Area')

            # Prediction formula logic
            estimated_price = round((sqft * 6200) + (bhk * 300000) + (bath * 150000))
            prediction = {
                'location': location,
                'sqft': sqft,
                'bhk': bhk,
                'price': f"₹{estimated_price:,.0f}"
            }
        except ValueError:
            prediction = None

    return render_template('price_predict.html', prediction=prediction)

# ==========================================
# PORTFOLIO & ADD ASSET ROUTE
# ==========================================

@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('price_predict'))

    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        p_type = request.form.get('type')
        p_price = request.form.get('purchase_price')
        c_val = request.form.get('current_value')

        if title and location:
            PORTFOLIO_DATA.append({
                'title': title,
                'location': location,
                'type': p_type,
                'purchase_price': f"₹{int(p_price):,}" if p_price.isdigit() else p_price,
                'current_value': f"₹{int(c_val):,}" if c_val.isdigit() else c_val,
                'status': 'Active'
            })
            flash("New property asset added successfully!", "success")

    summary = {
        'total_value': '₹1,25,00,000',
        'total_properties': len(PORTFOLIO_DATA),
        'avg_yield': 5.4
    }
    return render_template('portfolio.html', summary=summary, properties=PORTFOLIO_DATA)

# ==========================================
# UPLOAD DATASET & PREVIEW ROUTE
# ==========================================

@app.route('/dataset_management', methods=['GET', 'POST'])
def dataset_management():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('price_predict'))

    tables = None
    row_count = 0
    col_count = 0
    message = None

    if request.method == 'POST':
        file = request.files.get('dataset_file')
        if file and file.filename.endswith('.csv'):
            try:
                # Read CSV using Pandas
                df = pd.read_csv(file)
                row_count, col_count = df.shape
                
                # Display up to first 50 rows for performance
                preview_df = df.head(50)
                tables = preview_df.to_html(classes='table table-striped table-hover table-bordered table-dark', index=False)
                message = f"Dataset uploaded successfully! Total Rows: {row_count:,} | Columns: {col_count}"
            except Exception as e:
                message = f"Error processing file: {str(e)}"

    return render_template('dataset_management.html', tables=tables, row_count=row_count, col_count=col_count, message=message)

# ==========================================
# OTHER ROUTES
# ==========================================

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('compare.html')

@app.route('/emi', methods=['GET', 'POST'])
def emi():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('emi.html')

@app.route('/nri_desk', methods=['GET', 'POST'])
def nri_desk():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('nri_desk.html')

@app.route('/audit_logs')
def audit_logs():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('price_predict'))

    logs = [
        {'timestamp': '2026-08-30 11:30:00', 'username': session.get('user'), 'action': 'LOGIN', 'details': f"Logged in as {session.get('role')}"}
    ]
    return render_template('audit_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
