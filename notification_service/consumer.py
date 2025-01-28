import pika
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Notification
import os
import time
import logging

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "appuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")
RECOMMEND_QUEUE = "recommendations_queue"
ORDER_UPDATES_QUEUE = "order_updates_queue"

def handle_new_recommendation(data: dict, db: Session):
    user_id = data.get("userId")
    content = data.get("content")
    notification = Notification(
        userId=user_id,
        type="recommendation",
        content=content
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    print(f"Created recommendation notification {notification.id} for user {user_id}")

def handle_order_status_update(data: dict, db: Session):
    user_id = data.get("userId")
    status = data.get("status")
    order_id = data.get("orderId")
    content = f"Your order {order_id} status has been updated to {status}."
    notification = Notification(
        userId=user_id,
        type="order_update",
        content=content
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    print(f"Created order update notification {notification.id} for user {user_id}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        event = message.get("event")
        data = message.get("data", {})
        db: Session = SessionLocal()
        if event == "NEW_RECOMMENDATION":
            handle_new_recommendation(data, db)
        elif event == "ORDER_STATUS_UPDATE":
            handle_order_status_update(data, db)
        else:
            logger.warning(f"Unhandled event: {event}")
        db.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consuming():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)

    print("hello", credentials, parameters)
    
    while True:
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Declare both queues
            channel.queue_declare(queue=RECOMMEND_QUEUE, durable=True)
            channel.queue_declare(queue=ORDER_UPDATES_QUEUE, durable=True)
            
            # Set QoS
            channel.basic_qos(prefetch_count=1)
            
            # Start consuming
            channel.basic_consume(queue=RECOMMEND_QUEUE, on_message_callback=callback)
            channel.basic_consume(queue=ORDER_UPDATES_QUEUE, on_message_callback=callback)
            
            print("Notification Service is consuming from recommendations_queue and order_updates_queue...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Failed to connect to RabbitMQ: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Wait before retrying
