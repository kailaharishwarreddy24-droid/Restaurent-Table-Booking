from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import uuid
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "super_secret_key"

DATABASE = "database.db"

# ===============================
# EMAIL CONFIG
# ===============================

SENDER_EMAIL = "culinarycrown.official@gmail.com"
APP_PASSWORD = "hbeuvdvwokowxleo"
BASE_URL = "http://127.0.0.1:5000"

# ===============================
# EMAIL FUNCTION
# ===============================

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email error:", e)

# ===============================
# DATABASE
# ===============================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        branch TEXT,
        date TEXT,
        time TEXT,
        seating_type TEXT,
        guests INTEGER,
        status TEXT DEFAULT 'Confirmed'
    )
    """)
    conn.commit()
    conn.close()

# ===============================
# ROUTES
# ===============================

@app.route('/')
def index():
    return render_template("index.html")

# ===============================
# USER DETAILS (VALIDATION)
# ===============================

@app.route('/user-details', methods=['GET', 'POST'])
def user_details():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        if not name or not email or not phone:
            return "All fields are required!"

        if len(name) < 3:
            return "Name must be at least 3 characters"

        if not phone.isdigit() or len(phone) != 10:
            return "Phone must be 10 digits"

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return "Invalid email"

        session['name'] = name
        session['email'] = email
        session['phone'] = phone

        return redirect(url_for('select_slot'))

    return render_template("user_details.html")

# ===============================
# SELECT SLOT
# ===============================

@app.route('/select-slot', methods=['GET', 'POST'])
def select_slot():
    if request.method == 'POST':
        branch = request.form.get('branch')
        date = request.form.get('date')
        guests = request.form.get('guests')
        seating_type = request.form.get('seating_type')
        time = request.form.get('time')

        if not all([branch, date, guests, seating_type, time]):
            return "All fields required"

        if int(guests) <= 0:
            return "Invalid guests"

        session['branch'] = branch
        session['date'] = date
        session['guests'] = int(guests)
        session['seating_type'] = seating_type
        session['time'] = time

        return redirect(url_for('confirmation'))

    return render_template("select_slot.html")

# ===============================
# CONFIRMATION
# ===============================

@app.route('/confirmation')
def confirmation():

    if 'name' not in session:
        return redirect(url_for('index'))

    booking_id = str(uuid.uuid4())[:8]

    conn = get_connection()
    conn.execute("""
        INSERT INTO bookings
        (booking_id, name, email, phone, branch, date, time, seating_type, guests)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_id,
        session['name'],
        session['email'],
        session['phone'],
        session['branch'],
        session['date'],
        session['time'],
        session['seating_type'],
        session['guests']
    ))
    conn.commit()
    conn.close()

    data = dict(session)
    session.clear()

    return render_template("confirmation.html", data=data, booking_id=booking_id)

# ===============================
# MANAGE BOOKING
# ===============================

@app.route('/manage-booking/<booking_id>')
def manage_booking(booking_id):
    conn = get_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,)
    ).fetchone()
    conn.close()

    if not booking:
        return "Invalid Booking ID"

    return render_template("manage_booking.html", booking=booking)

# ===============================
# ADMIN LOGIN (FIXED)
# ===============================

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == "admin" and password == "admin123":
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid credentials"

    return render_template("admin/admin_login.html")

# ===============================
# ADMIN DASHBOARD
# ===============================

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    bookings = conn.execute("SELECT * FROM bookings").fetchall()
    conn.close()

    return render_template("admin/admin_dashboard.html", bookings=bookings)

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)