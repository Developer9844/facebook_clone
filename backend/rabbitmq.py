import json
import pika

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
