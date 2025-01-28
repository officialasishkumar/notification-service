import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import pika
import json
import threading

from database import Base, engine, SessionLocal
from models import Recommendation
from consumer import start_consuming

Base.metadata.create_all(bind=engine)

RABBITMQ_HOST = "localhost"  # or your RabbitMQ container hostname
QUEUE_NAME = "recommendations_queue"

app = FastAPI(title="Recommendation Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility to publish to RabbitMQ
def publish_to_queue(message: dict):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)  # persistent
    )
    connection.close()

@app.post("/recommend/{user_id}")
def generate_recommendation(user_id: int, product_id: int, reason: str, db: Session = Depends(get_db)):
    """
    A mock endpoint that pretends to do some advanced logic to generate a recommendation.
    We'll store it locally and also publish to the queue.
    """
    recommendation = Recommendation(userId=user_id, productId=product_id, reason=reason)
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    # Publish an event to the queue for the Notification Service to pick up
    message = {
        "event": "NEW_RECOMMENDATION",
        "data": {
            "userId": user_id,
            "content": f"Recommended product {product_id} because {reason}"
        }
    }
    publish_to_queue(message)

    return {"message": "Recommendation generated", "recommendation_id": recommendation.id}

@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    recommendations = db.query(Recommendation).filter(Recommendation.userId == user_id).all()
    return recommendations 

@app.on_event("startup")
def startup_event():
    """
    When FastAPI starts, we spin up a thread to run RabbitMQ consumer logic.
    """
    consumer_thread = threading.Thread(target=start_consuming, daemon=True)
    consumer_thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
