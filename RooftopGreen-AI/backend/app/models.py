from app.database import Base
from sqlalchemy import Column, String, Float, JSON, DateTime, Text
import datetime
import uuid


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, unique=True, index=True)
    preferences = Column(JSON, default={})
    roof_data = Column(JSON, default={})
    cells = Column(JSON, default={})
    placements = Column(JSON, default={})
    bom = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True)
    items = Column(JSON, default=[])
    total_bdt = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending, confirmed, pending_payment, paid
    payment_method = Column(String, default="cod")
    sandbox_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
