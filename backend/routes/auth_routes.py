from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
import datetime
import mysql.connector
from db import get_db_connection

bcrypt = Bcrypt()
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = bcrypt.generate_password_hash(data.get("password")).decode("utf-8")
    full_name = data.get("full_name", "")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password, full_name) VALUES (%s, %s, %s)", 
            (username, password, full_name)
        )
        db.commit()
        response = jsonify({"message": "User registered successfully"})
    except mysql.connector.Error as e:
        response = jsonify({"error": str(e)})
    finally:
        cursor.close()
        db.close()

    return response

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user[1], password):
            access_token = create_access_token(identity=username, expires_delta=datetime.timedelta(hours=1))
            return jsonify({"access_token": access_token})

        return jsonify({"error": "Invalid credentials"}), 401

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()
