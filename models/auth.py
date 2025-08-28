from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class WealthsimpleAuth(Base):
    __table_name__ = "wealthsimple_auth"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # Wealthsimple tokens
    client_id = Column(String)
    access_token = Column(Text)
    refresh_token = Column(String)
    session_id = Column(String)
    wssdi = Column(String)

    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




    