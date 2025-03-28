from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
import datetime
import pika
import json
import os
from celery import Celery

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJPbmxpbmUgSldUIEJ1YiI6IkpvaG5ueSIsIlN1cm5hbWUiOiJSb2NrZXQiLCJFbWFpbCI6Impyb2NrZXRAZXhhbXBsZS5jb20iLCJSb2xlIjpbIk1hbmFnZXIiLCJQcm9qZWN0IEFkbWluaXN0cmF0b3IiXX0.RSq0eQtMWrxk4xxSiF8kD9B1L_8WExdEy-pCzrwSuYY'
jwt = JWTManager(app)


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "ankush-katkurwar")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Anku$h9844.")
DATABASE = os.getenv("DATABASE", "facebook_clone")

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend="rpc://",
        broker="pyamqp://guest@localhost//"
    )
    celery.conf.update(app.config)
    return celery

app.config["CELERY_BROKER_URL"] = "pyamqp://guest@localhost//"
app.config["CELERY_RESULT_BACKEND"] = "rpc://"

celery = make_celery(app)

@celery.task  # ✅ Register the task
def save_post_to_db(post_data):
    # Import here to avoid circular import
    from models import Post, db  # Ensure you have SQLAlchemy configured
    post = Post(**post_data)
    db.session.add(post)
    db.session.commit()
    return "Post saved!"


# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DATABASE
    )

# Database migration
def migrate():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            bio TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    db.commit()
    cursor.close()
    db.close()

migrate()

# RabbitMQ Configuration
RABBITMQ_HOST = "localhost"
QUEUE_NAME = "post_queue"

def send_message_to_queue(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()

    # Declare the queue (it must exist before publishing messages)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # Publish message to RabbitMQ
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Makes message persistent
        )
    )

    connection.close()



@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = bcrypt.generate_password_hash(data.get("password")).decode('utf-8')
    full_name = data.get("full_name", "")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password, full_name) VALUES (%s, %s, %s)", 
                       (username, password, full_name))
        db.commit()
        response = jsonify({"message": "User registered successfully"})
    except mysql.connector.Error as e:
        response = jsonify({"error": str(e)})
    finally:
        cursor.close()
        db.close()

    return response

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    db = get_db_connection()  # ✅ Get a new DB connection
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

@app.route("/api/profile", methods=["GET", "PUT"])
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    db = get_db_connection()  # ✅ Get a new DB connection
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

            # Handle username, full_name, bio, profile_pic updates
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
        db.close()  # ✅ Always close DB connection



@app.route("/api/posts", methods=["GET", "POST"])
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


@app.route('/api/posts/full', methods=['GET'])
@jwt_required()
def get_posts_with_fullname():
    db = get_db_connection()  # ✅ Get a new DB connection
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
        db.close()  # ✅ Close DB connection properly



@app.route("/api/posts/<int:post_id>", methods=["PUT", "DELETE"])
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





@app.route("/api/my-posts", methods=["GET"])
@jwt_required()
def get_my_posts():
    current_user = get_jwt_identity()
    db = get_db_connection()  # ✅ Get a new DB connection
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
        db.close()  # ✅ Close DB connection properly



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
