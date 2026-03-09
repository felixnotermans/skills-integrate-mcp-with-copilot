# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Students can sign up for activities
- Teacher admin mode for removing participants

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Student self-signup for an activity                                 |
| POST   | `/auth/login`                                                    | Authenticate teacher/admin mode and receive a short-lived token     |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remove a participant (teacher token required)                  |

## Teacher Login (Admin Mode)

Use the user button in the top-right corner of the web UI to login as a teacher.

Teacher credentials are loaded from JSON in this order:

- `src/teachers.json` (local, ignored by git)
- `src/teachers.example.json` (fallback template)

Each user entry contains a `username` and SHA-256 `password_hash`.

To generate a hash for a password:

```bash
python -c "import hashlib; print(hashlib.sha256('your-password'.encode()).hexdigest())"
```

After login, use the returned token for privileged requests:

- Header: `X-Teacher-Token: <token>`

The signup endpoint remains open for student self-registration.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
