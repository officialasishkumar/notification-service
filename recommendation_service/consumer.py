import pika
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Recommendation
import os
import time
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "appuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")

QUEUE_NAME = os.getenv("QUEUE_NAME", "recommendations_queue")

def callback(ch, method, properties, body):
    try:
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
                logger.error("Invalid content format")
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
            logger.info(f"Stored recommendation {recommendation.id} for user {user_id}")
            db.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consuming():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    
    while True:
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            logger.info(f"Connected to RabbitMQ. Consuming from {QUEUE_NAME}...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
