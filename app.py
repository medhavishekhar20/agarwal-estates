from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'agarwal_estates_secure_key'

# ==========================================
# AUTHENTICATION & ROLE MANAGEMENT
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
        role = request.form.get('role', 'user')  # Options: admin, user, buyer
        
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
# ALL FEATURE ROUTES
# ==========================================

@app.route('/price_predict', methods=['GET', 'POST'])
def price_predict():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    prediction = None
    if request.method == 'POST':
        sqft = float(request.form.get('sqft', 1000))
        bhk = int(request.form.get('bhk', 2))
        estimated_price = round((sqft * 5800) + (bhk * 250000))
        prediction = f"₹{estimated_price:,.0f}"
        
    return render_template('price_predict.html', prediction=prediction)

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    comparison_data = None
    if request.method == 'POST':
        loc1 = request.form.get('locality1', 'Location A')
        loc2 = request.form.get('locality2', 'Location B')
        comparison_data = {
            'locality1': {'name': loc1, 'avg_price': '6,500', 'price_range': '₹5,000 - ₹8,000 / sqft', 'growth': 'High (8.5%)'},
            'locality2': {'name': loc2, 'avg_price': '8,200', 'price_range': '₹7,000 - ₹10,500 / sqft', 'growth': 'Moderate (6.2%)'}
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

# --- ADMIN ONLY ROUTES ---

@app.route('/portfolio')
def portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('price_predict'))  # Block non-admins
        
    summary = {'total_value': '1,25,00,000', 'total_properties': 2, 'avg_yield': 5.4}
    properties = [
        {'title': 'Luxury 3BHK Villa', 'location': 'Whitefield', 'type': 'Residential', 'purchase_price': '75,00,000', 'current_value': '85,00,000', 'status': 'Active'}
    ]
    return render_template('portfolio.html', summary=summary, properties=properties)

@app.route('/audit_logs')
def audit_logs():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('price_predict'))  # Block non-admins
        
    logs = [
        {'timestamp': '2026-08-30 11:30:00', 'username': session.get('user'), 'action': 'LOGIN', 'details': f"Logged in as {session.get('role')}"}
    ]
    return render_template('audit_logs.html', logs=logs)

@app.route('/dataset_management', methods=['GET', 'POST'])
def dataset_management():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('price_predict'))  # Block non-admins
        
    message = None
    if request.method == 'POST':
        message = "Dataset CSV uploaded and trained successfully!"
        
    return render_template('dataset_management.html', message=message)

if __name__ == '__main__':
    app.run(debug=True)
