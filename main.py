import sqlite3
import hashlib
import secrets
from pathlib import Path
from urllib.parse import quote_plus
from html import escape

import requests
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader

app = FastAPI(title="Smart AI Job Portal")

Path("resumes").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

DB_NAME = "job_portal.db"
SESSIONS = {}

SKILLS = [
    "python", "java", "c++", "html", "css", "javascript", "react", "node",
    "django", "fastapi", "flask", "sql", "mysql", "postgresql", "mongodb",
    "machine learning", "ai", "data science", "pandas", "numpy",
    "tensorflow", "pytorch", "excel", "power bi", "git", "github",
    "api", "rest api", "bootstrap"
]


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        job_title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        extracted_skills TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


init_db()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in SESSIONS:
        return None

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (SESSIONS[token],)).fetchone()
    conn.close()
    return user


def require_login(request: Request):
    user = get_current_user(request)
    return user


def layout(title: str, body: str, user=None) -> HTMLResponse:
    auth_links = """
        <a href="/signup">Signup</a>
        <a href="/login">Login</a>
    """

    if user:
        auth_links = f"""
            <a href="/dashboard">Dashboard</a>
            <a href="/upload">Upload Resume</a>
            <a href="/logout">Logout</a>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{escape(title)}</title>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #eef4ff;
                color: #172554;
            }}
            nav {{
                background: #1d4ed8;
                padding: 16px 8%;
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: white;
            }}
            nav a {{
                color: white;
                text-decoration: none;
                margin-left: 18px;
                font-weight: bold;
            }}
            .logo {{
                font-size: 22px;
                margin-left: 0;
            }}
            .hero {{
                width: 80%;
                margin: 60px auto;
                background: white;
                padding: 55px;
                border-radius: 22px;
                box-shadow: 0 12px 35px rgba(0,0,0,0.08);
            }}
            .hero h1 {{
                font-size: 42px;
                margin-top: 0;
            }}
            .box {{
                width: 440px;
                margin: 60px auto;
                background: white;
                padding: 32px;
                border-radius: 18px;
                box-shadow: 0 12px 35px rgba(0,0,0,0.08);
            }}
            .page {{
                width: 82%;
                margin: 35px auto;
            }}
            input, textarea, select {{
                width: 100%;
                padding: 13px;
                margin: 9px 0;
                border: 1px solid #b8c2d6;
                border-radius: 10px;
                font-size: 15px;
            }}
            textarea {{
                min-height: 120px;
            }}
            button, .btn {{
                background: #2563eb;
                color: white;
                padding: 12px 18px;
                border: none;
                border-radius: 10px;
                margin: 8px 8px 8px 0;
                cursor: pointer;
                font-weight: bold;
                text-decoration: none;
                display: inline-block;
            }}
            button:hover, .btn:hover {{
                background: #1e40af;
            }}
            .green {{
                background: #16a34a;
            }}
            .green:hover {{
                background: #15803d;
            }}
            .red {{
                background: #dc2626;
            }}
            .job-card, .dash-card {{
                background: white;
                margin: 18px 0;
                padding: 22px;
                border-radius: 16px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.07);
                position: relative;
            }}
            .match {{
                position: absolute;
                right: 20px;
                top: 20px;
                background: #dcfce7;
                color: #166534;
                padding: 8px 12px;
                border-radius: 20px;
                font-weight: bold;
            }}
            .error {{
                color: #dc2626;
                font-weight: bold;
            }}
            .success {{
                color: #15803d;
                font-weight: bold;
            }}
            .skills span {{
                display: inline-block;
                background: #dbeafe;
                color: #1e40af;
                padding: 8px 12px;
                margin: 6px;
                border-radius: 18px;
                font-weight: bold;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 18px;
            }}
        </style>
    </head>
    <body>
        <nav>
            <a class="logo" href="/">Smart AI Job Portal</a>
            <div>
                <a href="/jobs">Jobs</a>
                {auth_links}
            </div>
        </nav>
        {body}
    </body>
    </html>
    """
    return HTMLResponse(html)


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += (page.extract_text() or "") + " "
    except Exception:
        return ""
    return text.lower()


def extract_skills(text: str):
    return sorted({skill for skill in SKILLS if skill in text})


def calculate_match(job_title: str, skills):
    if not skills:
        return 40

    title = job_title.lower()
    matched = sum(1 for skill in skills if skill in title)
    score = 50 + matched * 15

    if "developer" in title and any(s in skills for s in ["python", "java", "javascript", "django", "react"]):
        score += 10

    if "ai" in title and any(s in skills for s in ["ai", "machine learning", "python"]):
        score += 15

    return min(score, 95)


def get_jobs(keyword="python", skills=None):
    jobs = []

    try:
        response = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": keyword},
            timeout=8
        )
        data = response.json()

        for job in data.get("jobs", [])[:15]:
            title = job.get("title", "No Title")
            company = job.get("company_name", "No Company")
            location = job.get("candidate_required_location", "Remote")
            url = job.get("url", "#")

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "match": calculate_match(title, skills or [])
            })
    except Exception:
        pass

    if jobs:
        return jobs

    fallback_jobs = [
        ("Python Developer", "Infosys", "Chennai", "#"),
        ("AI Engineer", "TCS", "Bangalore", "#"),
        ("Django Backend Developer", "Zoho", "Coimbatore", "#"),
        ("Machine Learning Intern", "Startup India", "Remote", "#"),
        ("React Developer", "Freshworks", "Chennai", "#"),
        ("Data Analyst", "Wipro", "Hyderabad", "#"),
        ("FastAPI Backend Intern", "Tech Startup", "Remote", "#")
    ]

    return [
        {
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "match": calculate_match(title, skills or [])
        }
        for title, company, location, url in fallback_jobs
    ]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_current_user(request)
    body = """
    <section class="hero">
        <h1>AI Powered Smart Job Portal</h1>
        <p>
            A real working FastAPI project with signup, login, resume analysis,
            skill extraction, job recommendation, saved jobs and application tracking.
        </p>
        <a class="btn" href="/signup">Create Account</a>
        <a class="btn green" href="/jobs">Search Jobs</a>
    </section>

    <div class="page grid">
        <div class="dash-card">
            <h3>Resume Analysis</h3>
            <p>Upload a PDF resume and extract skills automatically.</p>
        </div>
        <div class="dash-card">
            <h3>Real Job Search</h3>
            <p>Search jobs using live remote jobs API with fallback results.</p>
        </div>
        <div class="dash-card">
            <h3>Application Tracking</h3>
            <p>Apply for jobs and view your submitted applications.</p>
        </div>
    </div>
    """
    return layout("Smart AI Job Portal", body, user)


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    user = get_current_user(request)
    body = """
    <div class="box">
        <h1>Create Account</h1>
        <form method="post" action="/signup">
            <input type="text" name="name" placeholder="Full Name" required>
            <input type="email" name="email" placeholder="Email Address" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Signup</button>
        </form>
        <p>Already have account? <a href="/login">Login</a></p>
    </div>
    """
    return layout("Signup", body, user)


@app.post("/signup", response_class=HTMLResponse)
def signup(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.lower().strip(), hash_password(password))
        )
        conn.commit()
        conn.close()
        return RedirectResponse("/login", status_code=303)
    except sqlite3.IntegrityError:
        conn.close()
        return layout("Signup Error", """
        <div class="box">
            <h2 class="error">Email already exists</h2>
            <a class="btn" href="/signup">Try Again</a>
        </div>
        """)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user = get_current_user(request)
    body = """
    <div class="box">
        <h1>Login</h1>
        <form method="post" action="/login">
            <input type="email" name="email" placeholder="Email Address" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <p>New user? <a href="/signup">Create account</a></p>
    </div>
    """
    return layout("Login", body, user)


@app.post("/login", response_class=HTMLResponse)
def login(email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password_hash=?",
        (email.lower().strip(), hash_password(password))
    ).fetchone()
    conn.close()

    if not user:
        return layout("Login Error", """
        <div class="box">
            <h2 class="error">Invalid email or password</h2>
            <a class="btn" href="/login">Try Again</a>
        </div>
        """)

    token = secrets.token_hex(32)
    SESSIONS[token] = user["id"]

    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("session_token", token, httponly=True)
    return response


@app.get("/logout")
def logout(request: Request):
    token = request.cookies.get("session_token")
    if token in SESSIONS:
        del SESSIONS[token]

    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session_token")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    applications = conn.execute(
        "SELECT * FROM applications WHERE user_id=? ORDER BY id DESC",
        (user["id"],)
    ).fetchall()
    saved_jobs = conn.execute(
        "SELECT * FROM saved_jobs WHERE user_id=? ORDER BY id DESC",
        (user["id"],)
    ).fetchall()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id=? ORDER BY id DESC",
        (user["id"],)
    ).fetchall()
    conn.close()

    app_html = ""
    for app_row in applications:
        app_html += f"""
        <div class="job-card">
            <h3>{escape(app_row["job_title"])}</h3>
            <p><b>Company:</b> {escape(app_row["company"])}</p>
            <p><b>Location:</b> {escape(app_row["location"])}</p>
            <p><b>Applied On:</b> {escape(str(app_row["created_at"]))}</p>
        </div>
        """

    saved_html = ""
    for job in saved_jobs:
        saved_html += f"""
        <div class="job-card">
            <h3>{escape(job["title"])}</h3>
            <p><b>Company:</b> {escape(job["company"])}</p>
            <p><b>Location:</b> {escape(job["location"])}</p>
            <a class="btn" href="{escape(job["url"] or "#")}" target="_blank">Open Job</a>
        </div>
        """

    resume_html = ""
    for res in resumes:
        resume_html += f"""
        <div class="job-card">
            <h3>{escape(res["filename"])}</h3>
            <p><b>Extracted Skills:</b> {escape(res["extracted_skills"] or "No skills found")}</p>
            <p><b>Uploaded:</b> {escape(str(res["created_at"]))}</p>
        </div>
        """

    body = f"""
    <div class="page">
        <h1>Welcome, {escape(user["name"])}</h1>
        <a class="btn" href="/upload">Upload Resume</a>
        <a class="btn green" href="/jobs">Search Jobs</a>

        <h2>Your Resumes</h2>
        {resume_html or "<p>No resume uploaded yet.</p>"}

        <h2>Your Applications</h2>
        {app_html or "<p>No applications submitted yet.</p>"}

        <h2>Saved Jobs</h2>
        {saved_html or "<p>No saved jobs yet.</p>"}
    </div>
    """
    return layout("Dashboard", body, user)


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    body = """
    <div class="box">
        <h1>Upload Resume</h1>
        <p>Upload PDF resume. The system extracts skills and recommends jobs.</p>
        <form method="post" action="/upload" enctype="multipart/form-data">
            <input type="file" name="resume" accept=".pdf" required>
            <button type="submit">Analyze Resume</button>
        </form>
    </div>
    """
    return layout("Upload Resume", body, user)


@app.post("/upload", response_class=HTMLResponse)
async def upload_resume(request: Request, resume: UploadFile = File(...)):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    safe_filename = resume.filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    file_path = f"resumes/{user['id']}_{safe_filename}"

    with open(file_path, "wb") as f:
        f.write(await resume.read())

    text = extract_text_from_pdf(file_path)
    skills = extract_skills(text)
    skills_text = ", ".join(skills)

    conn = get_db()
    conn.execute(
        "INSERT INTO resumes (user_id, filename, extracted_skills) VALUES (?, ?, ?)",
        (user["id"], safe_filename, skills_text)
    )
    conn.commit()
    conn.close()

    keyword = skills[0] if skills else "python"
    return RedirectResponse(f"/jobs?keyword={quote_plus(keyword)}&resume_skills={quote_plus(skills_text)}", status_code=303)


@app.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request, keyword: str = "python", resume_skills: str = ""):
    user = get_current_user(request)

    skills = [s.strip() for s in resume_skills.split(",") if s.strip()]
    jobs = get_jobs(keyword, skills)

    skills_html = ""
    if skills:
        skills_html = "<div class='skills'><h3>Skills Found From Resume</h3>"
        for skill in skills:
            skills_html += f"<span>{escape(skill)}</span>"
        skills_html += "</div>"

    cards = ""
    for job in jobs:
        title = job["title"]
        company = job["company"]
        location = job["location"]
        url = job["url"]

        apply_link = f"/apply?title={quote_plus(title)}&company={quote_plus(company)}&location={quote_plus(location)}&url={quote_plus(url)}"
        save_link = f"/save-job?title={quote_plus(title)}&company={quote_plus(company)}&location={quote_plus(location)}&url={quote_plus(url)}"

        cards += f"""
        <div class="job-card">
            <div class="match">{job["match"]}% Match</div>
            <h2>{escape(title)}</h2>
            <p><b>Company:</b> {escape(company)}</p>
            <p><b>Location:</b> {escape(location)}</p>
            <a class="btn" href="{escape(url)}" target="_blank">View Original</a>
            <a class="btn green" href="{apply_link}">Apply</a>
            <a class="btn" href="{save_link}">Save</a>
        </div>
        """

    body = f"""
    <div class="page">
        <h1>Recommended Jobs</h1>
        <form method="get" action="/jobs">
            <input type="text" name="keyword" value="{escape(keyword)}" placeholder="Search python, ai, django, react">
            <button type="submit">Search</button>
        </form>
        {skills_html}
        {cards}
    </div>
    """
    return layout("Jobs", body, user)


@app.get("/apply", response_class=HTMLResponse)
def apply_page(request: Request, title: str = "", company: str = "", location: str = "", url: str = "#"):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    body = f"""
    <div class="box">
        <h1>Apply for Job</h1>
        <form method="post" action="/apply">
            <input type="text" name="student_name" value="{escape(user["name"])}" required>
            <input type="email" name="email" value="{escape(user["email"])}" required>
            <input type="text" name="phone" placeholder="Phone Number" required>

            <input type="text" name="job_title" value="{escape(title)}" readonly>
            <input type="text" name="company" value="{escape(company)}" readonly>
            <input type="text" name="location" value="{escape(location)}" readonly>

            <textarea name="message" required>I am interested in this role and my skills match the requirements.</textarea>

            <button type="submit">Submit Application</button>
        </form>
    </div>
    """
    return layout("Apply", body, user)


@app.post("/apply", response_class=HTMLResponse)
def apply_job(
    request: Request,
    student_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    job_title: str = Form(...),
    company: str = Form(...),
    location: str = Form(...),
    message: str = Form(...)
):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    conn.execute("""
    INSERT INTO applications
    (user_id, student_name, email, phone, job_title, company, location, message)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user["id"], student_name, email, phone, job_title, company, location, message))
    conn.commit()
    conn.close()

    return RedirectResponse("/dashboard", status_code=303)


@app.get("/save-job")
def save_job(request: Request, title: str = "", company: str = "", location: str = "", url: str = "#"):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    conn.execute(
        "INSERT INTO saved_jobs (user_id, title, company, location, url) VALUES (?, ?, ?, ?, ?)",
        (user["id"], title, company, location, url)
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/dashboard", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    user = require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    users = conn.execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC").fetchall()
    apps = conn.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()
    conn.close()

    users_html = ""
    for u in users:
        users_html += f"""
        <div class="job-card">
            <h3>{escape(u["name"])}</h3>
            <p>{escape(u["email"])}</p>
            <p>{escape(str(u["created_at"]))}</p>
        </div>
        """

    apps_html = ""
    for a in apps:
        apps_html += f"""
        <div class="job-card">
            <h3>{escape(a["job_title"])}</h3>
            <p>{escape(a["student_name"])} - {escape(a["email"])}</p>
            <p>{escape(a["company"])} - {escape(a["location"])}</p>
        </div>
        """

    body = f"""
    <div class="page">
        <h1>Admin Panel</h1>
        <h2>All Users</h2>
        {users_html}
        <h2>All Applications</h2>
        {apps_html}
    </div>
    """
    return layout("Admin", body, user)
