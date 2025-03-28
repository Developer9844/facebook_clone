from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import jwt_required, get_jwt_identity
import mysql.connector
from db import get_db_connection

bcrypt = Bcrypt()
profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/profile", methods=["GET", "PUT"])
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    db = get_db_connection()
    cursor = db.cursor()

    try:
        if request.method == "GET":
            cursor.execute("SELECT username, full_name, bio FROM users WHERE username = %s", (current_user,))
            user = cursor.fetchone()
            if user:
                return jsonify({
                    "username": user[0], 
                    "full_name": user[1], 
                    "bio": user[2], 
                })
            return jsonify({"error": "User not found"}), 404

        elif request.method == "PUT":
            data = request.json
            updates = []
            values = []

            # Handle username, full_name, bio updates
            if "username" in data:
                updates.append("username = %s")
                values.append(data["username"])
            
            if "full_name" in data:
                updates.append("full_name = %s")
                values.append(data["full_name"])
            
            if "bio" in data:
                updates.append("bio = %s")
                values.append(data["bio"])
            
            # Handle password update
            if "old_password" in data and "new_password" in data:
                cursor.execute("SELECT password FROM users WHERE username = %s", (current_user,))
                stored_password = cursor.fetchone()

                if stored_password and bcrypt.check_password_hash(stored_password[0], data["old_password"]):
                    new_hashed_password = bcrypt.generate_password_hash(data["new_password"]).decode("utf-8")
                    updates.append("password = %s")
                    values.append(new_hashed_password)
                else:
                    return jsonify({"error": "Old password is incorrect"}), 400

            if updates:
                query = f"UPDATE users SET {', '.join(updates)} WHERE username = %s"
                values.append(current_user)
                cursor.execute(query, tuple(values))
                db.commit()

            return jsonify({"message": "Profile updated successfully"})

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()
