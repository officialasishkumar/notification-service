from typing import Optional, Dict
import pika
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Recommendation
import os
import time
import logging
import requests
import random

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "appuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")
ORDER_PLACED_QUEUE = os.getenv("ORDER_PLACED_QUEUE", "order_placed_queue")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")

# Dummy products for recommendation
DUMMY_PRODUCTS = [
    {"product_id": 101, "name": "Wireless Mouse"},
    {"product_id": 102, "name": "Bluetooth Keyboard"},
    {"product_id": 103, "name": "USB-C Hub"},
    {"product_id": 104, "name": "Noise Cancelling Headphones"},
    {"product_id": 105, "name": "4K Monitor"},
    {"product_id": 106, "name": "External SSD"},
    {"product_id": 107, "name": "Smartphone Stand"},
    {"product_id": 108, "name": "Webcam"},
    {"product_id": 109, "name": "Portable Charger"},
    {"product_id": 110, "name": "LED Desk Lamp"},
]

def generate_random_recommendation(user_id: int) -> dict:
    product = random.choice(DUMMY_PRODUCTS)
    reason = "Based on your recent order."
    recommendation = {
        "userId": user_id,
        "productId": product["product_id"],
        "reason": reason
    }
    return recommendation

def fetch_user_preferences(user_id: int) -> Optional[Dict]:
    try:
        response = requests.get(f"{USER_SERVICE_URL}/user/{user_id}")
        if response.status_code == 200:
            user_data = response.json()
            preferences = json.loads(user_data["preferences"])
            return preferences
        else:
            logger.error(f"Failed to fetch user {user_id} preferences: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}")
        return None

def publish_new_recommendation(recommendation: dict):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue="recommendations_queue", durable=True)
    message = {
        "event": "NEW_RECOMMENDATION",
        "data": {
            "userId": recommendation["userId"],
            "content": f"Recommended product {recommendation['productName']} (Product ID: {recommendation['productId']}) "
                       f"for Order #{recommendation['orderId']} because {recommendation['reason']}"
        }
    }
    channel.basic_publish(
        exchange='',
        routing_key="recommendations_queue",
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()

def handle_order_placed(data: dict):
    user_id = data.get("userId")
    if not user_id:
        logger.error("userId not found in ORDER_PLACED event")
        return
    
    preferences = fetch_user_preferences(user_id)
    if preferences and preferences.get("recommendations"):
        recommendation = generate_random_recommendation(user_id)
        db: Session = SessionLocal()
        try:
            # Store recommendation in the database
            new_recommendation = Recommendation(
                userId=recommendation["userId"],
                productId=recommendation["productId"],
                reason=recommendation["reason"]
            )
            db.add(new_recommendation)
            db.commit()
            db.refresh(new_recommendation)
            logger.info(f"Stored recommendation {new_recommendation.id} for user {user_id}")
            
            # Publish NEW_RECOMMENDATION event
            publish_new_recommendation(recommendation)
        except Exception as e:
            logger.error(f"Error storing recommendation: {e}")
            db.rollback()
        finally:
            db.close()
    else:
        logger.info(f"User {user_id} has not enabled recommendations.")

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        event = message.get("event")
        data = message.get("data", {})
        
        if event == "ORDER_PLACED":
            handle_order_placed(data)
        else:
            logger.warning(f"Unhandled event: {event}")
        
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
            channel.queue_declare(queue=ORDER_PLACED_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=ORDER_PLACED_QUEUE, on_message_callback=callback)
            logger.info(f"Connected to RabbitMQ. Consuming from {ORDER_PLACED_QUEUE}...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
