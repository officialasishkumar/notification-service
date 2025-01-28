import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import Base, engine, SessionLocal
from models import Notification

import threading
from consumer import start_consuming

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Notification Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/notifications/unread/{user_id}")
def fetch_unread_notifications(user_id: int, db: Session = Depends(get_db)):
    notifications = db.query(Notification)\
                      .filter(Notification.userId == user_id, Notification.read == False)\
                      .all()
    return notifications

@app.post("/notifications/mark-read/{notification_id}")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    db.commit()
    return {"message": "Notification marked as read"}

# endpoint to manually create a notification (you’d normally do this via queue/event)
@app.post("/notifications")
def create_notification(user_id: int, notif_type: str, content: str, db: Session = Depends(get_db)):
    notif = Notification(userId=user_id, type=notif_type, content=content)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

@app.on_event("startup")
def startup_event():
    """
    When FastAPI starts, we spin up a thread to run RabbitMQ consumer logic.
    """
    consumer_thread = threading.Thread(target=start_consuming, daemon=True)
    consumer_thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
