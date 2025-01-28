# user_service/app.py

import jwt
import time
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
from typing import Dict, List

from database import Base, engine, SessionLocal
from models import User
from passlib.hash import bcrypt

app = FastAPI(title="User Service")

# Pydantic Schemas
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    preferences: Dict[str, bool] = {}

class UserLogin(BaseModel):
    email: str
    password: str

class UserPreferencesUpdate(BaseModel):
    preferences: Dict[str, bool]

class UserType(BaseModel):
    id: int
    name: str
    email: str
    preferences: str  # JSON string

SECRET_KEY = "MY_SECRET_KEY"  # Use environment variables in production
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register", response_model=UserType)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = bcrypt.hash(user_data.password)
    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        preferences=json.dumps(user_data.preferences)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserType(
        id=user.id,
        name=user.name,
        email=user.email,
        preferences=user.preferences
    )

@app.post("/login")
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not bcrypt.verify(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    payload = {
        "userId": user.id,  # Changed from user_id to userId
        "exp": int(time.time()) + 3600  # 1 hour expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "userId": user.id}  # Changed from user_id to userId

@app.get("/user/{user_id}", response_model=UserType)
def get_user_details(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserType(
        id=user.id,
        name=user.name,
        email=user.email,
        preferences=user.preferences
    )

@app.put("/user/{user_id}/preferences", response_model=UserType)
def update_user_preferences(
    user_id: int, prefs: UserPreferencesUpdate, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.preferences = json.dumps(prefs.preferences)
    db.commit()
    db.refresh(user)
    return UserType(
        id=user.id,
        name=user.name,
        email=user.email,
        preferences=user.preferences
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
