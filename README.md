# Smart Task Manager

A simple, responsive Task Manager web app built with Python, Flask, SQLite, and Bootstrap.

## Features
- User registration & login (session-based auth)
- Add / Edit / Delete tasks
- Mark tasks Complete / Pending
- Search tasks by title or description
- Filter by status
- Responsive Bootstrap UI with priority color-coding and stats cards

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the app:
   ```
   python app.py
   ```

3. Open your browser at: http://127.0.0.1:5000

The SQLite database (`tasks.db`) is created automatically on first run.

## Project Structure
```
task_manager/
├── app.py                  # Main Flask application
├── requirements.txt
├── templates/
│   ├── base.html           # Shared layout + navbar + Bootstrap
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html      # Task list, search, filter, stats
│   └── task_form.html      # Add/Edit task form
└── static/                 # (for any custom CSS/JS, if you add it)
```

## Notes
- Passwords are stored in plain text for simplicity — for production use,
  switch to `werkzeug.security.generate_password_hash` / `check_password_hash`.
- Each user only sees and manages their own tasks.
- `app.secret_key` should be changed and stored as an environment variable in production.
