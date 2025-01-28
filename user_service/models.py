from sqlalchemy import Column, Integer, String, Text
from database import Base
import json



class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    preferences = Column(Text, nullable=True)  # Store as JSON string

    def get_preferences(self):
        if self.preferences:
            return json.loads(self.preferences)
        return {}

    def set_preferences(self, prefs: dict):
        self.preferences = json.dumps(prefs)
