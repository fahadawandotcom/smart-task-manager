import sqlite3
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.secret_key = "smart-task-manager-secret-key-change-me"
DB_PATH = "tasks.db"


# ---------------------- Database helpers ----------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            priority TEXT NOT NULL DEFAULT 'Medium',
            due_date TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()


# ---------------------- Auth helpers ----------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------- Routes: Auth ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("Username already taken.", "danger")
            return redirect(url_for("register"))

        # NOTE: For production, hash passwords (e.g. werkzeug.security.generate_password_hash)
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------- Routes: Tasks ----------------------
@app.route("/dashboard")
@login_required
def dashboard():
    query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "All")

    db = get_db()
    sql = "SELECT * FROM tasks WHERE user_id = ?"
    params = [session["user_id"]]

    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{query}%", f"%{query}%"]

    if status_filter in ("Pending", "Completed"):
        sql += " AND status = ?"
        params.append(status_filter)

    sql += " ORDER BY created_at DESC"
    tasks = db.execute(sql, params).fetchall()

    total = db.execute("SELECT COUNT(*) c FROM tasks WHERE user_id = ?", (session["user_id"],)).fetchone()["c"]
    completed = db.execute(
        "SELECT COUNT(*) c FROM tasks WHERE user_id = ? AND status = 'Completed'",
        (session["user_id"],),
    ).fetchone()["c"]
    pending = total - completed

    return render_template(
        "dashboard.html",
        tasks=tasks,
        query=query,
        status_filter=status_filter,
        total=total,
        completed=completed,
        pending=pending,
    )


@app.route("/task/add", methods=["GET", "POST"])
@login_required
def add_task():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium")
        due_date = request.form.get("due_date", "")

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("add_task"))

        db = get_db()
        db.execute(
            """INSERT INTO tasks (user_id, title, description, status, priority, due_date, created_at)
               VALUES (?, ?, ?, 'Pending', ?, ?, ?)""",
            (session["user_id"], title, description, priority, due_date, datetime.now().isoformat()),
        )
        db.commit()
        flash("Task added successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("task_form.html", task=None, action="Add")


@app.route("/task/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    db = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"])
    ).fetchone()

    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium")
        due_date = request.form.get("due_date", "")

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("edit_task", task_id=task_id))

        db.execute(
            """UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?
               WHERE id = ? AND user_id = ?""",
            (title, description, priority, due_date, task_id, session["user_id"]),
        )
        db.commit()
        flash("Task updated successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("task_form.html", task=task, action="Edit")


@app.route("/task/delete/<int:task_id>")
@login_required
def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"]))
    db.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/task/toggle/<int:task_id>")
@login_required
def toggle_task(task_id):
    db = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"])
    ).fetchone()

    if task:
        new_status = "Pending" if task["status"] == "Completed" else "Completed"
        db.execute(
            "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
            (new_status, task_id, session["user_id"]),
        )
        db.commit()
        flash(f"Task marked as {new_status}.", "success")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
