# recommendation_service/app.py

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import pika
import json
import os
import threading
import time

from database import Base, engine, SessionLocal
from models import Recommendation
from consumer import start_consuming

app = FastAPI(title="Recommendation Service")

# Environment Variables
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "appuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")
QUEUE_NAME = os.getenv("QUEUE_NAME", "recommendations_queue")

class RecommendRequest(BaseModel):
    product_id: int
    reason: str

class RecommendResponse(BaseModel):
    message: str
    recommendation_id: int

class RecommendationType(BaseModel):
    id: int
    userId: int
    productId: int
    reason: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def publish_to_queue(message: dict):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)  # make message persistent
    )
    connection.close()

@app.post("/recommend/{user_id}", response_model=RecommendResponse)
def create_recommendation(user_id: int, recommend_request: RecommendRequest, db: Session = Depends(get_db)):
    recommendation = Recommendation(
        userId=user_id,
        productId=recommend_request.product_id,
        reason=recommend_request.reason
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    
    # Publish event to RabbitMQ
    message = {
        "event": "NEW_RECOMMENDATION",
        "data": {
            "userId": user_id,
            "content": f"Recommended product {recommend_request.product_id} because {recommend_request.reason}"
        }
    }
    publish_to_queue(message)
    
    return RecommendResponse(
        message="Recommendation generated",
        recommendation_id=recommendation.id
    )

@app.get("/recommendations/{user_id}", response_model=list[RecommendationType])
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    recommendations = db.query(Recommendation).filter(Recommendation.userId == user_id).all()
    return recommendations

@app.on_event("startup")
def startup_event():
    # Start the RabbitMQ consumer in a separate thread
    consumer_thread = threading.Thread(target=start_consuming, daemon=True)
    consumer_thread.start()
    print("Recommendation Service started and consumer initialized.")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host="0.0.0.0", port=8003)
