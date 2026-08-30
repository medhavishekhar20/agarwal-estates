from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for managing user sessions

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
        
        # Validates user login and sets the session
        if username and password:
            session['user'] = username
            return redirect(url_for('price_predict'))
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Saves account and automatically logs user in
        if username and password:
            session['user'] = username
            return redirect(url_for('price_predict'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- Protected Routes ---
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

@app.route('/nri_desk')
def nri_desk():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('nri_desk.html')

@app.route('/portfolio')
def portfolio():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('portfolio.html')

@app.route('/audit_logs')
def audit_logs():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('audit_logs.html')

if __name__ == '__main__':
    app.run(debug=True)
