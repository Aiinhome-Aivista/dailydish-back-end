import jwt
import datetime
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db_connection  

def register_controller(data):
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
    generated_user_id = f"{clean_name}_{timestamp}"
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return {"status": "error", "message": "Email already existed"}, 400
        sql = "INSERT INTO users (user_id, username, email, password) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (generated_user_id, username, email, hashed_password))
        conn.commit()

        return {
            "status": "success",
            "message": "Registration successful!",
            "user_id": generated_user_id
        }, 201

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    finally:
        cursor.close()
        conn.close()

def login_controller(data):
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return {"status": "error", "message": "Email and password required."}, 400

    conn = get_db_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            secret_key = os.getenv("JWT_SECRET")
            expire_hours = int(os.getenv("JWT_EXPIRATION_HOURS"))
            algo = os.getenv("JWT_ALGO", "HS256").strip().replace('"', '').replace("'", "")

            token_payload = {
                'user_id': user['user_id'],
                'email': user['email'],
                'username': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expire_hours)
            }

            token = jwt.encode(token_payload, secret_key, algorithm=algo)

            return {
                "status": "success",
                "message": "Login successful",
                "token": token,
                "user_id": user['user_id'],
                "username": user['username']
            }, 200
        else:
            return {"status": "error", "message": "Invalid email or password."}, 401

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    finally:
        cursor.close()
        conn.close()