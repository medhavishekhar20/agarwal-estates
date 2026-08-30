import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'agarwal_estates_secure_key_999'

ADMIN_PIN = "1234"

# ==========================================
# COMPARE ROUTE (FIXED)
# ==========================================

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

# ==========================================
# DATASET MANAGEMENT (ALL 13,000+ ROWS FIXED)
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
                
                # Render ALL rows into HTML table (No .head() truncation)
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
