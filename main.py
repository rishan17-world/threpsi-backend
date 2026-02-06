import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

# ✅ DATABASE
from db import get_connection, init_db

# APP INIT

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# STARTUP (DB ONLY)

@app.on_event("startup")
def startup_tasks():
    init_db()

# ERROR HANDLER

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse("Invalid or missing form data.", status_code=400)

# USER HELPERS (SQLITE)

def user_exists(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def email_exists(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def save_user(username, email, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (username, email, password, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (username, email, password, datetime.now())
    )
    conn.commit()
    conn.close()

def validate_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    valid = cur.fetchone() is not None
    conn.close()
    return valid

# AUTH ROUTES

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if validate_user(username, password):
        return RedirectResponse("/dashboard", status_code=302)
    return HTMLResponse("<h3>❌ Invalid credentials</h3><a href='/'>Try again</a>")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    if user_exists(username):
        return HTMLResponse("<h3>❌ Username already exists</h3><a href='/register'>Try again</a>")
    if email_exists(email):
        return HTMLResponse("<h3>❌ Email already registered</h3><a href='/register'>Try again</a>")

    save_user(username, email, password)
    return HTMLResponse("<h3>✅ Registration successful</h3><a href='/'>Login</a>")


# DASHBOARD

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# DOCTOR APPOINTMENT

@app.get("/doctor", response_class=HTMLResponse)
async def doctor_page(request: Request):
    return templates.TemplateResponse("doctor.html", {"request": request})

@app.post("/submit_appointment", response_class=HTMLResponse)
async def submit_appointment(
    name: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    date: str = Form(...),
    time: str = Form(...)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO appointments
        (name, email, department, date, time, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, email, department, date, time, datetime.now())
    )
    conn.commit()
    conn.close()

    return HTMLResponse("""
        <h3>✅ Appointment Booked Successfully</h3>
        <a href="/dashboard">Back to Dashboard</a>
    """)


# VIEW APPOINTMENTS

@app.get("/appointments", response_class=HTMLResponse)
async def view_appointments(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name, email, department, date, time, created_at
        FROM appointments
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()

    appointments = [
        {
            "name": r[0],
            "email": r[1],
            "department": r[2],
            "date": r[3],
            "time": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]

    return templates.TemplateResponse(
        "appointments.html",
        {"request": request, "appointments": appointments}
    )


# MEDICINE PRICE (SAFE REDIRECT)

@app.get("/medicine-price", response_class=HTMLResponse)
async def medicine_price_form(request: Request):
    return templates.TemplateResponse("medicine_price.html", {"request": request})

@app.post("/medicine-price", response_class=HTMLResponse)
async def compare_price(brand: str = Form(...), generic: str = Form(...)):
    brand_link = f"https://www.1mg.com/search/all?name={brand.replace(' ', '%20')}"
    generic_link = f"https://www.1mg.com/search/all?name={generic.replace(' ', '%20')}"

    return HTMLResponse(f"""
        <h2>💊 Medicine Price Comparison</h2>
        <p>Brand: <a href="{brand_link}" target="_blank">{brand}</a></p>
        <p>Generic: <a href="{generic_link}" target="_blank">{generic}</a></p>
        <a href="/dashboard">Back</a>
    """)

