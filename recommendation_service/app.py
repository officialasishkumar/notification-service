import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import pika
import json
import os
import threading
import time
import requests
import random
from typing import List, Optional, Dict

from database import Base, engine, SessionLocal
from models import Recommendation
from consumer import start_consuming, generate_random_recommendation, fetch_user_preferences, publish_new_recommendation
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="Recommendation Service")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "appuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")
ORDER_PLACED_QUEUE = os.getenv("ORDER_PLACED_QUEUE", "order_placed_queue")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DUMMY_PRODUCTS = [
    {"product_id": 201, "name": "Gaming Chair"},
    {"product_id": 202, "name": "Mechanical Keyboard"},
    {"product_id": 203, "name": "HD Webcam"},
    {"product_id": 204, "name": "Ergonomic Desk"},
    {"product_id": 205, "name": "Wireless Charger"},
    {"product_id": 206, "name": "Smartwatch"},
    {"product_id": 207, "name": "Fitness Tracker"},
    {"product_id": 208, "name": "Portable Projector"},
    {"product_id": 209, "name": "Action Camera"},
    {"product_id": 210, "name": "Drone with Camera"},
]

def fetch_all_users() -> List[dict]:
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch users: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []

def generate_and_publish_recommendation(user_id: int):
    recommendation = generate_random_recommendation(user_id)
    db: Session = SessionLocal()
    try:

        new_recommendation = Recommendation(
            userId=recommendation["userId"],
            productId=recommendation["productId"],
            reason=recommendation["reason"]
        )
        db.add(new_recommendation)
        db.commit()
        db.refresh(new_recommendation)
        logger.info(f"Stored recommendation {new_recommendation.id} for user {user_id}")

        publish_new_recommendation(recommendation)
    except Exception as e:
        logger.error(f"Error storing/publishing recommendation: {e}")
        db.rollback()
    finally:
        db.close()

def scheduled_recommendation_task():
    logger.info("Running scheduled recommendation task...")
    users = fetch_all_users()
    for user in users:
        preferences = json.loads(user["preferences"])
        if preferences.get("recommendations"):
            generate_and_publish_recommendation(user["id"])
    logger.info("Scheduled recommendation task completed.")

@app.on_event("startup")
def startup_event():

    consumer_thread = threading.Thread(target=start_consuming, daemon=True)
    consumer_thread.start()
    logger.info("Recommendation Service started and consumer initialized.")

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_recommendation_task, 'interval', minutes=10)  
    scheduler.start()
    logger.info("Scheduler for scheduled recommendations started.")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host="0.0.0.0", port=8003)