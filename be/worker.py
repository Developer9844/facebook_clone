from celery import Celery
import mysql.connector
import json

# Configure Celery with RabbitMQ as a broker
celery = Celery("worker", broker="pyamqp://guest:guest@localhost//")

# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="ankush-katkurwar",
        password="Anku$h9844.",
        database="facebook_clone"
    )

@celery.task
def save_message_to_db(message):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        data = json.loads(message)
        cursor.execute("INSERT INTO posts (user_id, content) VALUES (%s, %s)", (data["user_id"], data["content"]))
        db.commit()

    except mysql.connector.Error as e:
        print(f"Error inserting into DB: {e}")

    finally:
        cursor.close()
        db.close()
