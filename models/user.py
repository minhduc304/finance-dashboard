from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    # __table_args__ = {'schema': 'app'}
    __table_name__ = 'users'
    id = Column(Integer, unique_key=True)
    email = Column(String, unique_key=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

    # Relationship to auth tokens
    wealthsimple_auth = relationship("WealthsimpleAuth", back_populates="user", uselist=False)


