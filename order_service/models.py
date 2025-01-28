from sqlalchemy import Column, Integer, String, Text
from database import Base

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # e.g., 'placed', 'shipped', 'delivered'
