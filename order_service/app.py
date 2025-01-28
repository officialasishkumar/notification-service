import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import pika
import json
from apscheduler.schedulers.background import BackgroundScheduler
import time

from database import Base, engine, SessionLocal
from models import Order
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

Base.metadata.create_all(bind=engine)

QUEUE_NAME = "order_updates_queue"

app = FastAPI(title="Order Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def publish_to_queue(message: dict):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()

@app.post("/order")
def place_order(user_id: int, db: Session = Depends(get_db)):
    order = Order(userId=user_id, status="placed")
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"message": "Order placed", "order_id": order.id}

@app.get("/orders/{user_id}")
def get_orders(user_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.userId == user_id).all()
    return orders

# Periodic job to update order statuses and notify
def scheduled_order_update():
    db = SessionLocal()
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

    db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_order_update, 'interval', seconds=30)  # Run every 30 seconds
scheduler.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
