# Дипломный проект: Сайт класса для родителей с автоматизацией CI/CD
import os
import math
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-dev-secret-key")

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME", "class_db"),
        user=os.environ.get("DB_USER", "db_admin"),
        password=os.environ.get("DB_PASSWORD"),
        sslmode="require"
    )
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                fio VARCHAR(255) NOT NULL,
                phone VARCHAR(50) UNIQUE NOT NULL,
                child_fio VARCHAR(255),
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'parent'
            );
        """)
        cur.execute("SELECT * FROM users WHERE phone = 'admin';")
        if not cur.fetchone():
            admin_pass = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin2026"))
            cur.execute("""
                INSERT INTO users (fio, phone, child_fio, password, role)
                VALUES ('Администратор системы', 'admin', 'Нет', %s, 'admin');
            """, (admin_pass,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database initialization warning: {e}")

# Инициализируем БД только если это не тестовый прогон pytest
if not app.config.get('TESTING'):
    init_db()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    phone = request.form.get('phone')
    password = request.form.get('password')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT * FROM users WHERE phone = %s;", (phone,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['fio'] = user['fio']
        if user['role'] == 'admin':
            return redirect(url_for('users_page'))
        return redirect(url_for('contacts'))

    flash("Неверный номер телефона или пароль!", "danger")
    return redirect(url_for('index'))

@app.route('/admin/users')
def users_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('users.html')

@app.route('/api/admin/users')
def get_users_api():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    if search_query:
        sql_data = f"%{search_query}%"
        cur.execute("""
            SELECT COUNT(*) FROM users
            WHERE role = 'parent' AND (fio ILIKE %s OR phone ILIKE %s);
        """, (sql_data, sql_data))
        total_users = cur.fetchone()[0]

        cur.execute("""
            SELECT id, fio, phone, child_fio FROM users
            WHERE role = 'parent' AND (fio ILIKE %s OR phone ILIKE %s)
            ORDER BY id DESC LIMIT %s OFFSET %s;
        """, (sql_data, sql_data, per_page, offset))
    else:
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'parent';")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT id, fio, phone, child_fio FROM users WHERE role = 'parent' ORDER BY id DESC LIMIT %s OFFSET %s;", (per_page, offset))

    users = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()

    total_pages = math.ceil(total_users / per_page) if total_users > 0 else 1

    return jsonify({
        "users": users,
        "page": page,
        "total_pages": total_pages,
        "total_users": total_users
    })

@app.route('/admin/users/create', methods=['POST'])
def create_user():
    if session.get('role') != 'admin':
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403

    data = request.get_json() or {}
    fio = data.get('fio', '').strip()
    phone = data.get('phone', '').strip()
    child_fio = data.get('child_fio', '').strip()
    raw_password = data.get('password', '').strip()

    if not fio or not phone or not raw_password:
        return jsonify({"success": False, "error": "Поля ФИО, Телефон и Пароль обязательны!"}), 400

    hashed_password = generate_password_hash(raw_password)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (fio, phone, child_fio, password, role)
            VALUES (%s, %s, %s, %s, 'parent');
        """, (fio, phone, child_fio, hashed_password))
        conn.commit()
        return jsonify({"success": True, "message": f"Пользователь {fio} успешно создан!"})
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({"success": False, "error": f"Пользователь с телефоном {phone} уже зарегистрирован."}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/board')
def board():
    if not session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('board.html')

@app.route('/contacts')
def contacts():
    if not session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('contacts.html', role=session.get('role'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
