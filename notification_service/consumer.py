import pika
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Notification
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
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

def callback(ch, method, properties, body):
    message = json.loads(body)
    event = message.get("event")
    data = message.get("data", {})
    db: Session = SessionLocal()
    if event == "NEW_RECOMMENDATION":
        handle_new_recommendation(data, db)
    elif event == "ORDER_STATUS_UPDATE":
        handle_order_status_update(data, db)
    else:
        print(f"Unhandled event: {event}")
    db.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    # Declare both queues
    channel.queue_declare(queue=RECOMMEND_QUEUE, durable=True)
    channel.queue_declare(queue=ORDER_UPDATES_QUEUE, durable=True)
    
    # Set up consumers for both queues
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RECOMMEND_QUEUE, on_message_callback=callback)
    channel.basic_consume(queue=ORDER_UPDATES_QUEUE, on_message_callback=callback)
    
    print("Notification Service is consuming from recommendations_queue and order_updates_queue...")
    channel.start_consuming()