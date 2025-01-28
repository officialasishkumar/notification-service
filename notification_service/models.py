from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from database import Base

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sentAt = Column(DateTime(timezone=True), server_default=func.now())
    read = Column(Boolean, default=False)
