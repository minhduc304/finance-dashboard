from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# Import shared Base from backend
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
from app.core.database import Base

class User(Base):
    # __table_args__ = {'schema': 'app'}
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    active = Column(Boolean, default=True)

    # Relationship to auth tokens - commented out to avoid circular dependency
    # wealthsimple_auth = relationship("WealthsimpleAuth", back_populates="user", uselist=False)


