# Bengaluru Real Estate Price Decision Support System

A working web application built for Agarwal Estates: predicts fair property
prices using Machine Learning, plus EMI, taxation, and locality comparison
tools — with role-based logins for Admin, Employee, and User.

## How to run this on your laptop

1. Install Python 3.9+ if you don't already have it.
2. Open a terminal/command prompt in this folder and install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
   python app.py
   ```
4. Open your browser to: **http://127.0.0.1:5000**

The first time you run it, `users.db` is created automatically with one demo admin account.

## Demo login

- **Admin:** admin@agarwal.demo / admin123 (this account also sees the Model Accuracy dashboard)
- Or click **Register** on the login page to create your own Employee or User account.

## What's inside

- `app.py` — Flask backend: all routes, authentication, role-based access control
- `database.py` — SQLite database setup (Users + Predictions tables, password hashing)
- `train_model.py` — the script that cleaned the Kaggle dataset and trained the ML model
- `model.pkl` — the trained model (Linear Regression was auto-selected for the higher R²)
- `model_meta.json` — model metrics (R², MAE, RMSE) and the list of locations the model knows
- `locality_stats.json` — average price/sqft per locality, used by Compare Localities
- `Bengaluru_House_Data.csv` — the original Kaggle dataset (13,320 rows, 9 columns)
- `templates/` — all HTML pages (login, register, dashboard, predict, emi, tax, compare, history, profile, metrics)
- `static/css/style.css` — styling

## Model performance (real numbers, from actually training on this data)

Linear Regression was automatically selected as the better model:
- **R² Score: 0.83** — explains 83% of price variation, strong for a college project
- **MAE: ₹20.43 Lakhs**, **RMSE: ₹37.39 Lakhs**

Random Forest was also trained and compared (R² 0.82) — both are shown side by
side on the Model Accuracy tab (visible only when logged in as Admin).

## The 7 tabs (as required)

1. Dashboard
2. Price Prediction — the ML feature, trained on real data
3. Compare Localities
4. EMI Calculator
5. Taxation & Stamp Duty — current Karnataka rates (2%/3%/5% slabs + 10% cess + 2%/3% urban/rural surcharge + 2% registration)
6. History — your past predictions; Admin sees everyone's
7. Profile — change password

Plus **Model Accuracy** (Admin only) — showing R²/MAE/RMSE live, answering "how do
you measure accuracy and error" directly inside the app.

## Notes on scope

This is a fully working demo suitable for a college submission and for showing
Agarwal Estates. If you want to extend it further (e.g. an Admin page to
bulk-upload new listings via Excel), the codebase is structured simply enough
(one `app.py`, one `database.py`) to add that as a next step.
