import pika
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Recommendation
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "recommendations_queue"

def callback(ch, method, properties, body):
    message = json.loads(body)
    if message.get("event") == "NEW_RECOMMENDATION":
        data = message.get("data", {})
        user_id = data.get("userId")
        content = data.get("content")
        # Parse content to extract product_id and reason
        # Assuming content format: "Recommended product {product_id} because {reason}"
        try:
            parts = content.split("Recommended product ")[1].split(" because ")
            product_id = int(parts[0])
            reason = parts[1]
        except (IndexError, ValueError):
            print("Invalid content format")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        db: Session = SessionLocal()
        recommendation = Recommendation(
            userId=user_id,
            productId=product_id,
            reason=reason
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        print(f"Stored recommendation {recommendation.id} for user {user_id}")
        db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    print("Recommendation Service is consuming from recommendations_queue...")
    channel.start_consuming()
