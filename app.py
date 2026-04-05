"""
QuizGenius Web Application
Run: python app.py
"""

import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

print("=== STARTING APPLICATION ===")  # Debug
print(f"Environment keys: {list(os.environ.keys())}")  # Debug

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", str(uuid.uuid4()))

DATABASE_URL = os.environ.get("DATABASE_URL")
print(f"DATABASE_URL from env: {DATABASE_URL}")  # Debug
print(f"DATABASE_URL type: {type(DATABASE_URL)}")  # Debug
print(f"DATABASE_URL is None: {DATABASE_URL is None}")  # Debug
if DATABASE_URL:
    print(
        f"DATABASE_URL starts with postgresql: {DATABASE_URL.startswith('postgresql://')}"
    )  # Debug

USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgresql://")
print(f"USE_POSTGRES: {USE_POSTGRES}")  # Debug

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def get_db():
        print(f"[DEBUG] Connecting to PostgreSQL: {DATABASE_URL[:30]}...")  # Debug
        try:
            conn = psycopg2.connect(DATABASE_URL)
            print(f"[DEBUG] PostgreSQL connection successful")  # Debug
            return conn
        except Exception as e:
            print(f"[DEBUG] PostgreSQL connection failed: {e}")  # Debug
            raise

    def get_cursor(conn):
        return conn.cursor(cursor_factory=RealDictCursor)

    def init_db():
        print(f"[DEBUG] Initializing PostgreSQL DB")  # Debug
        conn = get_db()
        c = get_cursor(conn)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                groq_api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users (id),
                questions_solved INTEGER DEFAULT 0,
                correct_first_try INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                time_taken INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print(f"[DEBUG] PostgreSQL tables initialized")  # Debug

    def dict_row(cursor):
        return RealDictCursor
else:
    import sqlite3

    DB_PATH = os.path.join(os.path.dirname(__file__), "quizgenius.db")
    print(f"[DEBUG] Using SQLite database at: {DB_PATH}")  # Debug

    def get_db():
        print(f"[DEBUG] Connecting to SQLite: {DB_PATH}")  # Debug
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def get_cursor(conn):
        return conn.cursor()

    def init_db():
        print(f"[DEBUG] Initializing SQLite DB")  # Debug
        conn = get_db()
        c = get_cursor(conn)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                groq_api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                questions_solved INTEGER DEFAULT 0,
                correct_first_try INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                time_taken INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
        conn.close()
        print(f"[DEBUG] SQLite tables initialized")  # Debug

    def dict_row(cursor):
        return None


print(
    f"[DEBUG] USE_POSTGRES: {USE_POSTGRES}, DATABASE_URL: {bool(DATABASE_URL)}"
)  # Debug
if USE_POSTGRES:
    print(f"[DEBUG] DATABASE_URL: {DATABASE_URL[:50]}...")  # Debug
init_db()


def q(sql):
    """Convert SQL query to use correct parameter placeholders."""
    if USE_POSTGRES:
        return sql.replace("?", "%s")
    return sql


def get_user_id_from_cursor(c):
    """Get last inserted ID from cursor."""
    if USE_POSTGRES:
        return c.fetchone()[0]
    return c.lastrowid


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not email or not password:
            flash("Email and password required", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template("register.html")

        try:
    conn = get_db()
    c = get_cursor(conn)
            c.execute(q("SELECT id FROM users WHERE email = ?"), (email,))
            if c.fetchone():
                flash("Email already registered", "error")
                conn.close()
                return render_template("register.html")

            c.execute(
                q(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?) RETURNING id"
                    if USE_POSTGRES
                    else "INSERT INTO users (email, password_hash) VALUES (?, ?)"
                ),
                (email, generate_password_hash(password)),
            )
            conn.commit()
            user_id = get_user_id_from_cursor(c)
            conn.close()

            session["user_id"] = user_id
            session["email"] = email
            flash("Account created!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            q("SELECT id, email, password_hash FROM users WHERE email = ?"), (email,)
        )
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            flash("Logged in!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    print(f"[DEBUG Dashboard] user_id from session: {session['user_id']}")  # Debug

    conn = get_db()
    c = get_cursor(conn)

    c.execute(q("SELECT groq_api_key FROM users WHERE id = ?"), (session["user_id"],))
    user = c.fetchone()
    print(f"[DEBUG Dashboard] user query result: {user}")  # Debug
    if user:
        print(f"[DEBUG Dashboard] api_key from DB: '{user['groq_api_key']}'")  # Debug
    else:
        print(f"[DEBUG Dashboard] user NOT FOUND in database")  # Debug

    c.execute(
        q("""
        SELECT SUM(questions_solved) as total_questions,
               SUM(correct_first_try) as total_correct,
               AVG(score) as avg_score,
               COUNT(*) as total_quizzes
        FROM quiz_history WHERE user_id = ?
        """),
        (session["user_id"],),
    )
    stats = c.fetchone()

    c.execute(
        q("""
        SELECT * FROM quiz_history 
        WHERE user_id = ? 
        ORDER BY completed_at DESC LIMIT 10
        """),
        (session["user_id"],),
    )
    history = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        api_key=user["groq_api_key"] if user else "",
        stats=stats,
        history=history,
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    c = get_cursor(conn)
    c.execute(q("SELECT groq_api_key FROM users WHERE id = ?"), (session["user_id"],))
    user = c.fetchone()
    conn.close()

    if request.method == "POST":
        api_key = request.form.get("groq_api_key", "").strip()
        print(
            f"[DEBUG Settings] Saving API key for user_id={session['user_id']}, key_length={len(api_key)}"
        )  # Debug

        conn = get_db()
        c = conn.cursor()
        c.execute(
            q(
                "UPDATE users SET groq_api_key = %s WHERE id = %s"
                if USE_POSTGRES
                else "UPDATE users SET groq_api_key = ? WHERE id = ?"
            ),
            (api_key, session["user_id"]),
        )
        conn.commit()

        # Verify it was saved
        c.execute(
            q("SELECT groq_api_key FROM users WHERE id = ?"), (session["user_id"],)
        )
        verify = c.fetchone()
        print(
            f"[DEBUG Settings] After save: {verify['groq_api_key'] if verify else 'NOT FOUND'}"
        )  # Debug

        conn.close()

        flash("API key saved!", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "settings.html", api_key=user["groq_api_key"] if user else ""
    )


@app.route("/api/sync", methods=["POST"])
def api_sync():
    """API for local app to sync data."""
    data = request.get_json()
    user_id = data.get("user_id")
    action = data.get("action", "get_key")

    if not user_id:
        return jsonify({"error": "user_id required"}), 401

    conn = get_db()
    c = get_cursor(conn)

    c.execute(q("SELECT * FROM users WHERE id = ?"), (user_id,))
    user = c.fetchone()

    # Debug: log what we found
    print(
        f"API sync called: user_id={user_id}, action={action}, user_found={user is not None}"
    )
    if user:
        print(
            f"User email: {user['email']}, api_key present: {bool(user['groq_api_key'])}"
        )

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if action == "record_quiz":
        c.execute(
            q("""
            INSERT INTO quiz_history (user_id, questions_solved, correct_first_try, score, time_taken)
            VALUES (?, ?, ?, ?, ?)
        """),
            (
                user_id,
                data.get("questions", 0),
                data.get("correct", 0),
                data.get("score", 0),
                data.get("time", 0),
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # Default: return API key
    conn.close()
    return jsonify({"api_key": user["groq_api_key"] or ""})


@app.route("/api/key")
def api_key():
    """Return API key for logged-in user (for bookmarklet)."""
    if "user_id" not in session:
        print("[DEBUG] /api/key: Not logged in")
        return jsonify({"api_key": "", "user_id": ""})

    print(f"[DEBUG] /api/key: user_id={session['user_id']}")  # Debug

    conn = get_db()
    c = get_cursor(conn)
    c.execute(q("SELECT groq_api_key FROM users WHERE id = ?"), (session["user_id"],))
    user = c.fetchone()
    conn.close()

    print(f"[DEBUG] /api/key: user={user}")  # Debug
    if user:
        print(f"[DEBUG] /api/key: api_key={user['groq_api_key']}")  # Debug

    if user:
        return jsonify(
            {"api_key": user["groq_api_key"] or "", "user_id": session["user_id"]}
        )
    return jsonify({"api_key": "", "user_id": ""})


@app.route("/download")
def download():
    """Download page with the local app."""
    if "user_id" not in session:
        flash("Please login first", "error")
        return redirect(url_for("login"))
    return render_template("download.html")


@app.route("/userscript")
def userscript():
    """Serve the userscript file."""
    if "user_id" not in session:
        flash("Please login first", "error")
        return redirect(url_for("login"))
    import os

    script_path = os.path.join(os.path.dirname(__file__), "quizgenius.user.js")
    try:
        with open(script_path, "r") as f:
            content = f.read()
        from flask import Response

        return Response(content, mimetype="application/javascript")
    except:
        return "Userscript not found", 404


@app.route("/bookmarklet")
def bookmarklet():
    """Serve the bookmarklet page."""
    return render_template("bookmarklet.html")


@app.route("/templates/bookmarklet.html")
def bookmarklet_template():
    """Serve the bookmarklet HTML template."""
    import os

    template_path = os.path.join(os.path.dirname(__file__), "bookmarklet.html")
    try:
        with open(template_path, "r") as f:
            content = f.read()
        from flask import Response

        return Response(content, mimetype="text/html")
    except:
        return "Bookmarklet not found", 404


@app.route("/quizgenius.js")
def quizgenius_js():
    """Serve the quiz solver JavaScript."""
    import os

    js_path = os.path.join(os.path.dirname(__file__), "bookmark.js")
    try:
        with open(js_path, "r") as f:
            content = f.read()
        from flask import Response

        return Response(content, mimetype="application/javascript")
    except Exception as e:
        return f"Error: {e}", 500


@app.route("/bookmark.js")
def bookmark_js():
    """Serve the quiz solver JavaScript (alias)."""
    return quizgenius_js()


@app.route("/loader.js")
def loader_js():
    """Serve the minimal loader."""
    content = """var s=document.createElement('script');s.src='//quizgenius-nji8.onrender.com/quizgenius.js';s.onload=function(){console.log('QuizGenius loaded!')};s.onerror=function(){alert('Failed')};document.head.appendChild(s);"""
    from flask import Response

    return Response(content, mimetype="application/javascript")


@app.route("/chromebook")
def chromebook():
    """Serve the Chromebook solver page."""
    return render_template("chromebook.html")


@app.route("/remote")
def remote():
    """Serve the remote solver page."""
    return render_template("remote.html")


@app.route("/bookmark")
def bookmark_page():
    """Serve the bookmarklet creator page."""
    if "user_id" not in session:
        flash("Please login first", "error")
        return redirect(url_for("login"))

    conn = get_db()
    c = get_cursor(conn)
    c.execute(q("SELECT groq_api_key FROM users WHERE id = ?"), (session["user_id"],))
    user = c.fetchone()
    conn.close()

    return render_template(
        "bookmark.html", api_key=user["groq_api_key"] if user else ""
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
