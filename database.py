"""
Database setup for the Real Estate Decision Support System.
Creates users.db (SQLite) with Users and Predictions tables,
and seeds one default Admin account.
"""
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "users.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'employee', 'user'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            bhk INTEGER NOT NULL,
            total_sqft REAL NOT NULL,
            bath INTEGER NOT NULL,
            predicted_price REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Seed one default admin account for demo/grading purposes
    c.execute("SELECT * FROM users WHERE email = ?", ("admin@agarwal.demo",))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Admin", "admin@agarwal.demo", generate_password_hash("admin123"), "admin"),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialised: users.db")
    print("Default admin login -> email: admin@agarwal.demo | password: admin123")
