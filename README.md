EventOn - Event Registration & Management Platform
EventOn is a full-stack Event Management & Registration web platform built with Python (Django MVT). It provides a dual-portal interface for attendees and event administrators.

🚀 Key Features
Attendee Portal: Event discovery across categories (Tech Fests, Hackathons, Seminars), instant registration, automated QR-pass generation via qrcode & Pillow, and profile customization (Dark/Light mode).

Admin Dashboard: Real-time KPI summary widgets, Chart.js analytics for registrations and budget tracking, and a built-in camera QR scanner for attendee check-ins.

Logistics & Financials: Full CRUD management for venues, resources, vendor assignments, sponsorship tiers, and budget approval workflows.

🛠️ Tech Stack
Backend: Python, Django (MVT)

Frontend: HTML5, CSS3, JavaScript, Bootstrap 5, AdminLTE, Chart.js

Libraries: Pillow, qrcode, asgiref, colorama, django-mongodb-backend

Database: MongoDB

⚡ Quick Start
Bash
# 1. Clone repo & create virtual environment
git clone https://github.com/your-username/EventOn.git
cd EventOn
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure MongoDB (PowerShell example)
$env:MONGODB_URI = "mongodb://localhost:27017/"
$env:MONGODB_DB = "event_management"

# 4. Migrate database & create admin
python manage.py migrate
python manage.py createsuperuser

# 5. Start server
python manage.py runserver

Access the app at: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
