from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
# Secret key is required to keep track of logged-in user sessions
app.secret_key = 'agarwal_estates_secret_key_123'

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('price_predict'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Safely extract form data without causing 400 Bad Request
        username = request.form.get('username') or request.form.get('name')
        password = request.form.get('password')
        
        if username and password:
            session['user'] = username  # Save user in session
            return redirect(url_for('price_predict'))  # Go straight to main app after login
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Accepts any variation of username/name inputs
        username = request.form.get('username') or request.form.get('name')
        password = request.form.get('password')
        
        if username and password:
            session['user'] = username  # Automatically log in after registration
            return redirect(url_for('price_predict'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)  # Clear session
    return redirect(url_for('login'))

# ==========================================
# APPLICATION FEATURE ROUTES
# ==========================================

@app.route('/price_predict', methods=['GET', 'POST'])
def price_predict():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    prediction = None
    if request.method == 'POST':
        # Placeholder calculation so form submission works immediately
        sqft = float(request.form.get('sqft', 1000))
        bhk = int(request.form.get('bhk', 2))
        estimated_price = round((sqft * 5500) + (bhk * 200000))
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
            'locality1': {'name': loc1, 'avg_price': '6,500', 'price_range': '₹5,000 - ₹8,000 / sqft', 'growth': 'High (8.5% p.a.)'},
            'locality2': {'name': loc2, 'avg_price': '8,200', 'price_range': '₹7,000 - ₹10,500 / sqft', 'growth': 'Moderate (6.2% p.a.)'}
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
    
    success_msg = None
    if request.method == 'POST':
        success_msg = "Thank you! Our NRI advisory team will contact you shortly."
        
    return render_template('nri_desk.html', success_msg=success_msg)

@app.route('/portfolio')
def portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    # Sample portfolio data so page isn't empty
    summary = {'total_value': '1,25,00,000', 'total_properties': 2, 'avg_yield': 5.4}
    properties = [
        {'title': 'Luxury 3BHK Apartment', 'location': 'Whitefield', 'type': 'Residential', 'purchase_price': '75,00,000', 'current_value': '85,00,000', 'status': 'Active'},
        {'title': 'Commercial Office Space', 'location': 'Indiranagar', 'type': 'Commercial', 'purchase_price': '35,00,000', 'current_value': '40,00,000', 'status': 'Active'}
    ]
    return render_template('portfolio.html', summary=summary, properties=properties)

@app.route('/audit_logs')
def audit_logs():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    # Sample log data so page loads correctly
    logs = [
        {'timestamp': '2026-08-30 11:20:15', 'username': session.get('user'), 'action': 'POST /price_predict', 'details': 'Property estimation requested'},
        {'timestamp': '2026-08-30 11:15:02', 'username': session.get('user'), 'action': 'POST /login', 'details': 'User logged in successfully'}
    ]
    return render_template('audit_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
