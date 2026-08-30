import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'agarwal_estates_secure_key_999'

ADMIN_PIN = "1234"

# Global portfolio storage
PORTFOLIO_DATA = [
    {'title': 'Luxury 3BHK Villa', 'location': 'Whitefield', 'type': 'Residential', 'purchase_price': '₹75,00,000', 'current_value': '₹85,00,000', 'status': 'Active'}
]

# ==========================================
# AUTHENTICATION & ROOT ROUTE (PREVENTS 404)
# ==========================================

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
# FEATURE ROUTES
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

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    comparison_data = None
    if request.method == 'POST':
        loc1 = request.form.get('locality1', '').strip()
        loc2 = request.form.get('locality2', '').strip()
        
        if loc1 and loc2:
            comparison_data = {
                'locality1': {
                    'name': loc1,
                    'avg_price': '₹6,850 / sqft',
                    'price_range': '₹5,200 - ₹8,500 / sqft',
                    'growth': '8.5% p.a.',
                    'connectivity': 'High (Metro / Ring Road)',
                    'livability': '8.8 / 10'
                },
                'locality2': {
                    'name': loc2,
                    'avg_price': '₹8,400 / sqft',
                    'price_range': '₹7,100 - ₹11,200 / sqft',
                    'growth': '6.2% p.a.',
                    'connectivity': 'Moderate (Bus / Highway)',
                    'livability': '8.2 / 10'
                }
            }
            
    return render_template('compare.html', comparison_data=comparison_data)

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

# ==========================================
# ADMIN ONLY ROUTES
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
                'purchase_price': f"₹{int(p_price):,}" if p_price and p_price.isdigit() else p_price,
                'current_value': f"₹{int(c_val):,}" if c_val and c_val.isdigit() else c_val,
                'status': 'Active'
            })
            flash("New property asset added successfully!", "success")

    summary = {
        'total_value': '₹1,25,00,000',
        'total_properties': len(PORTFOLIO_DATA),
        'avg_yield': 5.4
    }
    return render_template('portfolio.html', summary=summary, properties=PORTFOLIO_DATA)

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
                df = pd.read_csv(file)
                row_count, col_count = df.shape
                
                tables = df.to_html(
                    classes='table table-striped table-hover table-bordered table-dark text-nowrap', 
                    index=True
                )
                message = f"Full Dataset Loaded Successfully! Total Records: {row_count:,} Rows | {col_count} Columns"
            except Exception as e:
                message = f"Error processing CSV: {str(e)}"

    return render_template(
        'dataset_management.html', 
        tables=tables, 
        row_count=row_count, 
        col_count=col_count, 
        message=message
    )

if __name__ == '__main__':
    app.run(debug=True)
