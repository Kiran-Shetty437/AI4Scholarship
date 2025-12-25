from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
from dotenv import load_dotenv
import random, smtplib, os, sqlite3, logging, uuid

# ----------------- BASIC SETUP ----------------- #

load_dotenv()

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

logging.basicConfig(level=logging.INFO)

# ----------------- CONFIG ----------------- #

EMAIL_USER = os.getenv("MAIL_USER")
EMAIL_PASS = os.getenv("MAIL_PASS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ----------------- DATABASE ----------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "students.db")

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gender TEXT,
            dob TEXT,
            total_income TEXT,
            caste TEXT,
            father_occupation TEXT,
            mother_occupation TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
        """)
        conn.commit()

# ✅ VERY IMPORTANT — CREATE TABLE ON STARTUP
init_db()

# ----------------- OTP LOGIC ----------------- #

otp_store = {}

def generate_otp(length=4):
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def send_email(to_email, otp):
    if not EMAIL_USER or not EMAIL_PASS:
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "AI4Scholarship - OTP Verification"
    msg.attach(MIMEText(f"Your OTP is: {otp}", "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        logging.error(f"Email error: {e}")
        return False

# ----------------- ROUTES ----------------- #

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email & Password required", "error")
            return redirect(url_for("index"))

        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM students WHERE email=?", (email,))
            if c.fetchone():
                flash("Account already exists", "error")
                return redirect(url_for("login"))

        otp = generate_otp()
        otp_store[email] = {
            "otp": otp,
            "expires": datetime.now() + timedelta(minutes=3),
            "password": generate_password_hash(password)
        }

        if send_email(email, otp):
            session["email"] = email
            flash("OTP sent to your email", "success")
            return redirect(url_for("verify"))
        else:
            flash("Failed to send OTP", "error")

    return render_template("signup.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("email")
    if not email:
        return redirect(url_for("index"))

    if request.method == "POST":
        otp_input = request.form.get("otp")
        record = otp_store.get(email)

        if not record or datetime.now() > record["expires"]:
            flash("OTP expired", "error")
            return redirect(url_for("index"))

        if otp_input != record["otp"]:
            flash("Wrong OTP", "error")
            return redirect(url_for("verify"))

        session["verified_email"] = email
        session["password"] = record["password"]
        del otp_store[email]
        return redirect(url_for("details"))

    return render_template("verify.html")

@app.route("/details", methods=["GET", "POST"])
def details():
    email = session.get("verified_email")
    password = session.get("password")
    if not email:
        return redirect(url_for("index"))

    if request.method == "POST":
        data = (
            request.form.get("name"),
            request.form.get("gender"),
            request.form.get("dob"),
            request.form.get("total_income"),
            request.form.get("caste"),
            request.form.get("father_occupation"),
            request.form.get("mother_occupation"),
            email,
            password
        )

        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO students
                (name, gender, dob, total_income, caste,
                 father_occupation, mother_occupation, email, password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()

        session["student_email"] = email
        session["student_name"] = data[0]
        return redirect(url_for("chat"))

    return render_template("details.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT name, password FROM students WHERE email=?", (email,))
            user = c.fetchone()

        if not user or not check_password_hash(user[1], password):
            flash("Invalid credentials", "error")
            return redirect(url_for("login"))

        session["student_email"] = email
        session["student_name"] = user[0]
        return redirect(url_for("chat"))

    return render_template("login.html")

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "student_email" not in session:
        return redirect(url_for("index"))

    name = session.get("student_name", "Student")

    if "chats" not in session:
        session["chats"] = {}

    chat_id = request.args.get("chat_id") or str(uuid.uuid4())
    session["chats"].setdefault(chat_id, [])
    chat_history = session["chats"][chat_id]

    if request.method == "POST":
        msg = request.form.get("message")
        chat_history.append(("user", msg))

        reply = "AI service unavailable."
        if client:
            try:
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": msg}]
                )
                reply = res.choices[0].message.content
            except Exception as e:
                logging.error(e)

        chat_history.append(("bot", reply))

    return render_template("chat.html", chat_history=chat_history, name=name)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/favicon.ico")
def favicon():
    return "", 204

# ----------------- ERROR HANDLER ----------------- #

@app.errorhandler(Exception)
def handle_error(e):
    logging.exception("Unhandled error")
    return "Something went wrong", 500

# ----------------- RUN ----------------- #

if __name__ == "__main__":
    app.run(debug=True)
