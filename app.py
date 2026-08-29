"""
Bengaluru Real Estate Price Decision Support System
Flask backend - authentication, roles, ML price prediction, EMI calculator,
Karnataka stamp duty/tax calculator, locality comparison, and an admin
model-accuracy dashboard.
"""
import json
import pickle
from functools import wraps

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db, init_db

app = Flask(__name__)
app.secret_key = "college-project-demo-secret-key-change-in-production"

# Initialize database tables on server startup
init_db()

# ---------- Load the trained model + metadata once at startup ----------
with open("model.pkl", "rb") as f:
    MODEL = pickle.load(f)

with open("model_meta.json") as f:
    META = json.load(f)

FEATURE_COLUMNS = META["feature_columns"]
LOCATIONS = META["locations"]

with open("locality_stats.json") as f:
    LOCALITY_STATS = {row["location"]: row for row in json.load(f)}


# ---------- Helpers ----------
def predict_price(location, bhk, total_sqft, bath):
    row = pd.DataFrame([[0] * len(FEATURE_COLUMNS)], columns=FEATURE_COLUMNS)
    row.at[0, "total_sqft"] = total_sqft
    row.at[0, "bath"] = bath
    row.at[0, "bhk"] = bhk
    if location in row.columns:
        row.at[0, location] = 1
    prediction = MODEL.predict(row)[0]
    return round(max(prediction, 0), 2)


def calculate_emi(principal, annual_rate, tenure_years):
    r = annual_rate / 12 / 100
    n = int(tenure_years * 12)
    if r == 0:
        return round(principal / n, 2)
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return round(emi, 2)


def calculate_tax(price_lakhs, area_type="urban"):
    price = price_lakhs * 100000
    if price <= 2000000:
        rate = 0.02
    elif price <= 4500000:
        rate = 0.03
    else:
        rate = 0.05
    stamp_duty = price * rate
    cess = stamp_duty * 0.10
    surcharge = stamp_duty * (0.02 if area_type == "urban" else 0.03)
    registration = price * 0.02
    total = stamp_duty + cess + surcharge + registration
    return {
        "slab_rate_pct": rate * 100,
        "stamp_duty": round(stamp_duty, 2),
        "cess": round(cess, 2),
        "surcharge": round(surcharge, 2),
        "registration": round(registration, 2),
        "total": round(total, 2),
        "total_pct_of_price": round(total / price * 100, 2),
    }


def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                flash("You don't have access to that page.")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ---------- Auth routes ----------
@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        if role not in ("employee", "user"):
            role = "user"  # admin accounts are never self-registered

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.")
            db.close()
            return redirect(url_for("register"))

        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), role),
        )
        db.commit()
        db.close()
        flash("Account created. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Dashboard ----------
@app.route("/dashboard")
@login_required()
def dashboard():
    db = get_db()
    total_predictions = db.execute("SELECT COUNT(*) c FROM predictions").fetchone()["c"]
    my_predictions = db.execute(
        "SELECT COUNT(*) c FROM predictions WHERE user_id = ?", (session["user_id"],)
    ).fetchone()["c"]
    total_users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    db.close()
    return render_template(
        "dashboard.html",
        total_predictions=total_predictions,
        my_predictions=my_predictions,
        total_users=total_users,
        num_locations=len(LOCATIONS),
    )


# ---------- Price Prediction ----------
@app.route("/predict", methods=["GET", "POST"])
@login_required()
def predict():
    result = None
    if request.method == "POST":
        location = request.form["location"]
        bhk = int(request.form["bhk"])
        total_sqft = float(request.form["total_sqft"])
        bath = int(request.form["bath"])

        price = predict_price(location, bhk, total_sqft, bath)
        margin = META["metrics"][
            "random_forest" if META["model_name"] == "Random Forest" else "linear_regression"
        ]["mae"]
        result = {
            "location": location, "bhk": bhk, "total_sqft": total_sqft, "bath": bath,
            "price": price, "low": round(max(price - margin, 0), 2), "high": round(price + margin, 2),
        }
        db = get_db()
        db.execute(
            "INSERT INTO predictions (user_id, location, bhk, total_sqft, bath, predicted_price) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session["user_id"], location, bhk, total_sqft, bath, price),
        )
        db.commit()
        db.close()

    return render_template("predict.html", locations=LOCATIONS, result=result)


# ---------- EMI Calculator ----------
@app.route("/emi", methods=["GET", "POST"])
@login_required()
def emi():
    result = None
    if request.method == "POST":
        principal = float(request.form["principal"]) * 100000  # lakhs -> rupees
        rate = float(request.form["rate"])
        tenure = float(request.form["tenure"])
        emi_amount = calculate_emi(principal, rate, tenure)
        total_payment = emi_amount * tenure * 12
        total_interest = total_payment - principal
        result = {
            "emi": emi_amount, "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2), "principal": principal,
        }
    return render_template("emi.html", result=result)


# ---------- Taxation & Stamp Duty ----------
@app.route("/tax", methods=["GET", "POST"])
@login_required()
def tax():
    result = None
    if request.method == "POST":
        price_lakhs = float(request.form["price"])
        area_type = request.form["area_type"]
        result = calculate_tax(price_lakhs, area_type)
        result["price_lakhs"] = price_lakhs
        result["area_type"] = area_type
    return render_template("tax.html", result=result)


# ---------- Locality Comparison ----------
@app.route("/compare", methods=["GET", "POST"])
@login_required()
def compare():
    result = None
    if request.method == "POST":
        loc1 = request.form["location1"]
        loc2 = request.form["location2"]
        result = {"loc1": LOCALITY_STATS.get(loc1), "loc2": LOCALITY_STATS.get(loc2)}
    return render_template("compare.html", locations=LOCATIONS, result=result)


# ---------- History ----------
@app.route("/history")
@login_required()
def history():
    db = get_db()
    if session["role"] == "admin":
        rows = db.execute(
            "SELECT p.*, u.name as user_name FROM predictions p JOIN users u ON p.user_id = u.id "
            "ORDER BY p.id DESC LIMIT 50"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (session["user_id"],),
        ).fetchall()
    db.close()
    return render_template("history.html", rows=rows)


# ---------- Profile / change password ----------
@app.route("/profile", methods=["GET", "POST"])
@login_required()
def profile():
    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

        if not check_password_hash(user["password_hash"], current_password):
            flash("Current password is incorrect.")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters.")
        else:
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new_password), session["user_id"]),
            )
            db.commit()
            flash("Password updated successfully.")
        db.close()
        return redirect(url_for("profile"))

    return render_template("profile.html")


# ---------- Admin: Model Accuracy Dashboard ----------
@app.route("/metrics")
@login_required(roles=["admin"])
def metrics():
    return render_template("metrics.html", meta=META)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
