from sqlalchemy import Column, Integer, String, Text
from database import Base

class Recommendation(Base):
    __tablename__ = 'recommendations'
    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, nullable=False)
    productId = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
