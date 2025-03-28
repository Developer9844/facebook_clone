from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from rabbitmq import send_message_to_queue
import mysql.connector
from db import get_db_connection
import datetime


post_bp = Blueprint("post", __name__)

@post_bp.route("/posts",  methods=["GET", "POST"])
@jwt_required()
def handle_posts():
    current_user = get_jwt_identity()
    db = get_db_connection()  # ✅ Get a new DB connection
    cursor = db.cursor()

    try:
        # Fetch the user_id, full_name, and username
        cursor.execute("SELECT id, full_name, username FROM users WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id, full_name, username = user  # Extract user details

        if request.method == "POST":
            data = request.json
            content = data.get("content")
            
            if not content:
                return jsonify({"error": "Content cannot be empty"}), 400

            cursor.execute("INSERT INTO posts (user_id, content) VALUES (%s, %s)", (user_id, content))
            db.commit()

            # Send message to RabbitMQ
            post_message = {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "content": content,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            send_message_to_queue(post_message)

            return jsonify(post_message)

        # Fetch all posts with user details
        cursor.execute("""
            SELECT users.username, users.full_name, posts.content 
            FROM posts 
            JOIN users ON posts.user_id = users.id  -- ✅ Corrected JOIN condition
            ORDER BY posts.created_at DESC
        """)

        posts = cursor.fetchall()

        return jsonify([
            {"username": p[0], "full_name": p[1], "content": p[2]} for p in posts
        ])

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()  # ✅ Always close the database connection


@post_bp.route('/posts/full', methods=['GET'])
@jwt_required()
def get_posts_with_fullname():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT users.id, users.full_name, users.username, posts.content 
            FROM posts 
            JOIN users ON posts.user_id = users.id
        """)
        posts = cursor.fetchall()
        return jsonify(posts)
    
    finally:
        cursor.close()
        db.close()

@post_bp.route("/posts/<int:post_id>", methods=["PUT", "DELETE"])
@jwt_required()
def modify_post(post_id):
    current_user = get_jwt_identity()
    db = get_db_connection()  # ✅ Get a fresh DB connection
    cursor = db.cursor()

    try:
        # Fetch user_id from the users table
        cursor.execute("SELECT id FROM users WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user_id = user[0]  # Extract user ID

        # Check if post exists and belongs to the user
        cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        
        if not post or post[0] != user_id:
            return jsonify({"error": "Unauthorized or post not found"}), 403

        if request.method == "PUT":
            data = request.json
            new_content = data.get("content")

            if not isinstance(new_content, str) or not new_content.strip():
                return jsonify({"error": "Content must be a non-empty string"}), 400

            cursor.execute("UPDATE posts SET content = %s WHERE id = %s", (new_content, post_id))
            db.commit()
            return jsonify({"message": "Post updated successfully"}), 200

        elif request.method == "DELETE":
            cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
            db.commit()
            return jsonify({"message": "Post deleted successfully"}), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()  # ✅ Always close the connection