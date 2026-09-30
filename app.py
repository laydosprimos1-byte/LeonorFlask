import os, secrets, sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        birth_date TEXT,
        phone TEXT,
        profession TEXT DEFAULT '',
        bio TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    db.commit()
    db.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para continuar.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = get_db().execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        from werkzeug.security import check_password_hash
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Email ou senha incorretos.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        from werkzeug.security import generate_password_hash
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        birth_date = request.form.get("birth_date", "")
        phone = request.form.get("phone", "")
        profession = request.form.get("profession", "")
        bio = request.form.get("bio", "")
        if len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "error")
            return render_template("register.html")
        try:
            db = get_db()
            db.execute("""INSERT INTO users
                (full_name,email,password_hash,birth_date,phone,profession,bio,created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (full_name, email, generate_password_hash(password), birth_date,
                 phone, profession, bio, datetime.utcnow().isoformat()))
            db.commit()
            flash("Conta criada. Agora faça login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Este email já está cadastrado.", "error")
    return render_template("register.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = get_db().execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + timedelta(minutes=30)
            db = get_db()
            db.execute("DELETE FROM reset_tokens WHERE user_id=?", (user["id"],))
            db.execute("INSERT INTO reset_tokens(user_id,token,expires_at) VALUES(?,?,?)",
                       (user["id"], token, expires.isoformat()))
            db.commit()
            # Para testar no Termux sem SMTP, mostramos o link no terminal.
            print(f"\n[RECUPERAÇÃO] Link: http://127.0.0.1:5000/reset/{token}\n")
        flash("Se o email estiver cadastrado, um link de recuperação foi gerado. No modo local, veja o terminal.", "success")
    return render_template("forgot.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    row = get_db().execute("""
        SELECT reset_tokens.*, users.email FROM reset_tokens
        JOIN users ON users.id=reset_tokens.user_id
        WHERE token=?
    """, (token,)).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        flash("Link inválido ou expirado.", "error")
        return redirect(url_for("forgot"))
    if request.method == "POST":
        password = request.form["password"]
        if len(password) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "error")
            return render_template("reset.html", token=token)
        from werkzeug.security import generate_password_hash
        db = get_db()
        db.execute("UPDATE users SET password_hash=? WHERE id=?",
                   (generate_password_hash(password), row["user_id"]))
        db.execute("DELETE FROM reset_tokens WHERE id=?", (row["id"],))
        db.commit()
        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("login"))
    return render_template("reset.html", token=token)

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return render_template("dashboard.html", user=user)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        db.execute("""UPDATE users SET full_name=?, birth_date=?, phone=?, profession=?, bio=?
                      WHERE id=?""",
                   (request.form["full_name"], request.form["birth_date"],
                    request.form["phone"], request.form["profession"],
                    request.form["bio"], session["user_id"]))
        db.commit()
        flash("Perfil atualizado.", "success")
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
