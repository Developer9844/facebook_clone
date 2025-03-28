from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import mysql.connector
from db import get_db_connection

my_posts_bp = Blueprint("my_posts", __name__)

@my_posts_bp.route("/my-posts", methods=["GET"])
@jwt_required()
def get_my_posts():
    current_user = get_jwt_identity()
    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user_id = user[0]

        # Fetch posts
        cursor.execute("SELECT id, content FROM posts WHERE user_id = %s", (user_id,))
        posts = cursor.fetchall()

        return jsonify([{"id": row[0], "content": row[1]} for row in posts])
    
    finally:
        cursor.close()
        db.close()
