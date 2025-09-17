from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime
from datetime import datetime

# Import shared Base from backend
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
from app.core.database import Base

class WealthsimpleAuth(Base):
    __tablename__ = "wealthsimple_auth"

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




    