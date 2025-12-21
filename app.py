from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
from dotenv import load_dotenv
import random, smtplib, os, sqlite3, requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Config
EMAIL_USER = os.getenv("MAIL_USER")
EMAIL_PASS = os.getenv("MAIL_PASS")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI client
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print("OpenAI error:", e)

# OTP storage
otp_store = {}

# Initialize Database
def init_db():
    with sqlite3.connect("students.db") as conn:
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


# Generate OTP
def generate_otp(length=4):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


# Send OTP Email
def send_email(to_email, otp):
    if not EMAIL_USER or not EMAIL_PASS:
        print("Email credentials missing.")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "AI Scholarship App - OTP Verification"
    msg.attach(MIMEText(f"Your OTP is: {otp}", "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email sending error:", e)
        return False


# ----------------- ROUTES ----------------- #

@app.route("/", methods=["GET", "POST"])
def index():
    """Signup → Send OTP"""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email & Password required!", "error")
            return redirect(url_for("index"))

        with sqlite3.connect("students.db") as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE email=?", (email,))
            if c.fetchone():
                flash("Account already exists. Login instead.", "error")
                return redirect(url_for("login"))

        otp = generate_otp()
        otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.now() + timedelta(minutes=3),
            "password": generate_password_hash(password)
        }

        if send_email(email, otp):
            session["email"] = email
            flash("OTP sent! Check your email.", "success")
            return redirect(url_for("verify"))
        else:
            flash("Failed to send OTP.", "error")

    return render_template("signup.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("email")
    if not email:
        return redirect(url_for("index"))

    if request.method == "POST":
        otp_input = request.form.get("otp")
        record = otp_store.get(email)

        if not record:
            flash("OTP expired or not found.", "error")
            return redirect(url_for("index"))

        if datetime.now() > record["expires_at"]:
            del otp_store[email]
            flash("OTP expired.", "error")
            return redirect(url_for("index"))

        if otp_input != record["otp"]:
            flash("Wrong OTP!", "error")
            return redirect(url_for("verify"))

        session["verified_email"] = email
        session["password"] = record["password"]
        del otp_store[email]
        return redirect(url_for("details"))

    return render_template("verify.html", email=email)


@app.route("/details", methods=["GET", "POST"])
def details():
    email = session.get("verified_email")
    password = session.get("password")
    if not email:
        return redirect(url_for("index"))

    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "gender": request.form.get("gender"),
            "dob": request.form.get("dob"),
            "total_income": request.form.get("total_income"),
            "caste": request.form.get("caste"),
            "father_occupation": request.form.get("father_occupation"),
            "mother_occupation": request.form.get("mother_occupation")
        }

        with sqlite3.connect("students.db") as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO students 
                (name, gender, dob, total_income, caste, father_occupation, mother_occupation, email, password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["name"], data["gender"], data["dob"],
                data["total_income"], data["caste"],
                data["father_occupation"], data["mother_occupation"],
                email, password
            ))
            conn.commit()

        session["student_email"] = email
        session["student_name"] = data["name"]
        return redirect(url_for("chat"))

    return render_template("details.html", email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Normal Login"""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        with sqlite3.connect("students.db") as conn:
            c = conn.cursor()
            c.execute("SELECT name, password FROM students WHERE email=?", (email,))
            user = c.fetchone()

        if not user:
            flash("Account not found.", "error")
            return redirect(url_for("login"))

        if not check_password_hash(user[1], password):
            flash("Wrong password.", "error")
            return redirect(url_for("login"))

        session["student_email"] = email
        session["student_name"] = user[0]
        return redirect(url_for("chat"))

    return render_template("login.html")


@app.route("/chat", methods=["GET", "POST"])
def chat():
    """Scholarship Chatbot"""
    email = session.get("student_email")
    if not email:
        return redirect(url_for("index"))

    name = session.get("student_name", "Student")
    
    # Initialize chats dictionary if not exists
    if "chats" not in session:
        session["chats"] = {}
    
    # Get current chat ID or create new one
    current_chat_id = request.args.get("chat_id")
    if not current_chat_id:
        current_chat_id = session.get("current_chat_id", "default")
    
    # Initialize chat if it doesn't exist
    if current_chat_id not in session["chats"]:
        session["chats"][current_chat_id] = []
    
    chat_history = session["chats"][current_chat_id]
    session["current_chat_id"] = current_chat_id
    
    # Handle new chat
    if request.form.get("new_chat"):
        import uuid
        current_chat_id = str(uuid.uuid4())
        session["chats"][current_chat_id] = []
        session["current_chat_id"] = current_chat_id
        chat_history = []
        return redirect(url_for("chat", chat_id=current_chat_id))
    
    # Handle reset chat
    if request.form.get("reset_chat"):
        session["chats"][current_chat_id] = []
        chat_history = []
        session["chats"][current_chat_id] = chat_history
        return redirect(url_for("chat", chat_id=current_chat_id))
    
    response_text = ""

    if request.method == "POST":
        user_message = request.form.get("message")

        # Save user message
        chat_history.append(("user", user_message))

        # STRICT SCHOLARSHIP DETECTION
        keywords = ["scholarship", "grant", "fellowship", "financial aid", "stipend", "bursary"]
        is_scholarship = any(k in user_message.lower() for k in keywords)

        # ❌ If NOT scholarship → show fixed message
        if not is_scholarship:
            response_text = (
                "❌ This assistant only searches about **scholarships**.\n"
                "Please ask something like:\n"
                "- Scholarship for engineering students\n"
                "- Merit scholarship\n"
                "- OBC scholarship"
            )
            chat_history.append(("bot", response_text))
            session["chats"][current_chat_id] = chat_history
            
            # Generate chat title from first user message if this is the first exchange
            if len(chat_history) == 2:  # First user message + first bot response
                title = user_message[:50] + ("..." if len(user_message) > 50 else "")
                if "chat_titles" not in session:
                    session["chat_titles"] = {}
                session["chat_titles"][current_chat_id] = title
            session["current_chat_id"] = current_chat_id
            return redirect(url_for("chat", chat_id=current_chat_id))

        # 🟢 GOOGLE SEARCH (only for scholarship queries)
        results = None
        search_success = False

        if GOOGLE_API_KEY and SEARCH_ENGINE_ID:
            try:
                q = f"{user_message} scholarship India"
                url = (
                    f"https://www.googleapis.com/customsearch/v1?q={q}"
                    f"&key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}"
                )
                data = requests.get(url, timeout=10).json()

                if "items" in data and len(data["items"]) > 0:
                    results = data["items"][0]  # top result
                    search_success = True

            except Exception as e:
                print("Search error:", e)

        # Fetch student info
        with sqlite3.connect("students.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT name, gender, dob, total_income, caste, 
                father_occupation, mother_occupation 
                FROM students WHERE email=?
            """, (email,))
            student = c.fetchone()

        # Create AI Prompt
        if search_success:
            title = results["title"]
            snippet = results.get("snippet", "")
            link = results["link"]

            prompt = f"""
You are a scholarship assistant.

### Student Info
Name: {student[0]}
Gender: {student[1]}
DOB: {student[2]}
Income: {student[3]}
Caste: {student[4]}
Father: {student[5]}
Mother: {student[6]}

### Scholarship Found
**{title}**
{snippet}
Link: {link}

### Task:
Explain in clear sections:
- Summary
- Eligibility
- Student Eligibility (Yes/No)
- Documents Needed
- Benefits
- Application Link
"""
        else:
            prompt = f"""
No specific scholarship found for: {user_message}

Provide:
- 5 matching scholarships
- Eligibility
- Benefits
- Apply links
"""

        # OpenAI call
        try:
            ai = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a scholarship assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            response_text = ai.choices[0].message.content
        except Exception as e:
            response_text = "OpenAI API Error."

        chat_history.append(("bot", response_text))
        session["chats"][current_chat_id] = chat_history
        
        # Generate chat title from first user message if this is the first exchange
        if len(chat_history) == 2:  # First user message + first bot response
            title = user_message[:50] + ("..." if len(user_message) > 50 else "")
            if "chat_titles" not in session:
                session["chat_titles"] = {}
            session["chat_titles"][current_chat_id] = title
        session["current_chat_id"] = current_chat_id

    # Get all chat titles for sidebar
    chat_titles = session.get("chat_titles", {})
    # Create list of chats with IDs and titles
    all_chats = []
    for chat_id, title in chat_titles.items():
        all_chats.append({"id": chat_id, "title": title})
    # Reverse to show newest first
    all_chats.reverse()

    return render_template("chat.html", chat_history=chat_history, name=name, 
                         all_chats=all_chats, current_chat_id=current_chat_id)


@app.route("/logout")
def logout():
    """Logout user and clear session"""
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))


# Run the app
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
