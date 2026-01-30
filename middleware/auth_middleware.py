import jwt
import os
from flask import request, jsonify
from functools import wraps

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"status": "error", "message": "Bearer token malformed!"}), 401

        if not token:
            return jsonify({"status": "error", "message": "Token is missing! Please login first."}), 401

        try:
            secret = os.getenv("JWT_SECRET")
            algo = os.getenv("JWT_ALGO", "HS256").strip().replace('"', '').replace("'", "")
            
            data = jwt.decode(token, secret, algorithms=[algo])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"status": "error", "message": "Invalid token!"}), 401
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 401

        return f(current_user_id, *args, **kwargs)
    return decorated