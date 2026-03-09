"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

# Session duration for teacher admin mode.
SESSION_DURATION_MINUTES = 60


def _load_teacher_password_hashes() -> dict[str, str]:
    """Load teacher credential hashes from JSON configuration."""
    base_dir = Path(__file__).parent
    teachers_file = base_dir / "teachers.json"
    fallback_file = base_dir / "teachers.example.json"
    source_file = teachers_file if teachers_file.exists() else fallback_file

    with source_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    users = data.get("users", [])
    return {
        entry["username"]: entry["password_hash"]
        for entry in users
        if "username" in entry and "password_hash" in entry
    }


teacher_password_hashes = _load_teacher_password_hashes()

# In-memory token store for short-lived teacher sessions.
teacher_sessions: dict[str, dict[str, str | datetime]] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


def _create_session_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=SESSION_DURATION_MINUTES)
    teacher_sessions[token] = {
        "username": username,
        "expires_at": expires_at,
    }
    return token


def _get_username_from_token(token: str | None) -> str | None:
    if token is None:
        return None

    session = teacher_sessions.get(token)
    if session is None:
        return None

    expires_at = session["expires_at"]
    if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
        teacher_sessions.pop(token, None)
        return None

    username = session.get("username")
    return username if isinstance(username, str) else None


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.post("/auth/login")
def login(payload: LoginRequest):
    """Validate teacher credentials for admin mode."""
    expected_hash = teacher_password_hashes.get(payload.username)
    provided_hash = hashlib.sha256(payload.password.encode("utf-8")).hexdigest()
    if expected_hash is None or expected_hash != provided_hash:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    token = _create_session_token(payload.username)

    return {
        "message": "Teacher login successful",
        "role": "teacher",
        "username": payload.username,
        "token": token,
        "token_type": "bearer",
        "expires_in": SESSION_DURATION_MINUTES * 60,
    }


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    x_teacher_token: str | None = Header(default=None)
):
    """Unregister a student from an activity"""
    # Restrict unregister operation to authenticated teachers.
    if _get_username_from_token(x_teacher_token) is None:
        raise HTTPException(
            status_code=401,
            detail="Only logged-in teachers can remove participants"
        )

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
