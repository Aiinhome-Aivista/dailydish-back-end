import jwt
import datetime
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db_connection


def admin_register_controller(data):
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not all([username, email, password, confirm_password]):
        return {"status": "error", "message": "All field required."}, 400

    if password != confirm_password:
        return {"status": "error", "message": "Password and Confirm password not match"}, 400

    clean_name = re.sub(r'\s+', '_', username.strip().lower())
    timestamp = datetime.datetime.now().strftime("%f")[:4]
    generated_admin_id = f"admin_{clean_name}_{timestamp}"

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM admins WHERE email = %s", (email,))
        if cursor.fetchone():
            return {"status": "error", "message": "Email already existed"}, 400

        sql = "INSERT INTO admins (admin_id, username, email, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (generated_admin_id, username, email, hashed_password))
        conn.commit()

        return {
            "status": "success",
            "message": "Admin registration successful!",
            "admin_id": generated_admin_id
        }, 201

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    finally:
        cursor.close()
        conn.close()


def admin_login_controller(data):
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return {"status": "error", "message": "Email and password required."}, 400

    conn = get_db_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE email = %s AND is_active = TRUE", (email,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin['password'], password):
            secret_key = os.getenv("JWT_SECRET")
            expire_hours = int(os.getenv("JWT_EXPIRATION_HOURS"))
            algo = os.getenv("JWT_ALGO", "HS256").strip().replace('"', '').replace("'", "")

            token_payload = {
                'admin_id': admin['admin_id'],
                'email': admin['email'],
                'username': admin['username'],
                'role': admin['role'],
                'is_admin': True,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expire_hours)
            }

            token = jwt.encode(token_payload, secret_key, algorithm=algo)

            return {
                "status": "success",
                "message": "Admin login successful",
                "token": token,
                "admin_id": admin['admin_id'],
                "username": admin['username'],
                "role": admin['role']
            }, 200
        else:
            return {"status": "error", "message": "Invalid email or password."}, 401

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    finally:
        cursor.close()
        conn.close()