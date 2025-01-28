import pika
import json
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field
import os
import time

from database import Base, engine, SessionLocal
from models import Order

class PlaceOrderRequest(BaseModel):
    userId: int = Field(..., alias="userId")

class OrderResponse(BaseModel):
    id: int
    userId: int
    status: str

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "appuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")

Base.metadata.create_all(bind=engine)

QUEUE_NAME = "order_updates_queue"

app = FastAPI(title="Order Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility to publish to RabbitMQ with authentication
def publish_to_queue(message: dict):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )
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

@app.post("/order", response_model=OrderResponse)
def place_order(order_request: PlaceOrderRequest, db: Session = Depends(get_db)):
    order = Order(userId=order_request.userId, status="placed")
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Publish ORDER_PLACED event
    message = {
        "event": "ORDER_PLACED",
        "data": {
            "orderId": order.id,
            "userId": order.userId,
            "status": order.status
        }
    }
    publish_to_queue(message)
    
    # Return the order details instead of a message
    return OrderResponse(
        id=order.id,
        userId=order.userId,
        status=order.status
    )

@app.get("/orders/{user_id}")
def get_orders(user_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.userId == user_id).all()
    return orders

# Periodic job to update order statuses and notify
def scheduled_order_update():
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.status != "delivered").all()
        for order in orders:
            if order.status == "placed":
                order.status = "shipped"
            elif order.status == "shipped":
                order.status = "delivered"
            db.commit()

            # Publish event
            message = {
                "event": "ORDER_STATUS_UPDATE",
                "data": {
                    "userId": order.userId,
                    "status": order.status,
                    "orderId": order.id
                }
            }
            publish_to_queue(message)

    except Exception as e:
        print(f"Error in scheduled_order_update: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_order_update, 'interval', seconds=5)  # Run every 5 seconds for testing
scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
