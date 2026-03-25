from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    conversations = relationship("Conversation", back_populates="user")
    plans = relationship("Plan", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User")
    conversations = relationship("Conversation", back_populates="project")
    plans = relationship("Plan", back_populates="project")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    sender = Column(String) # "user" or "system"
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")
    project = relationship("Project", back_populates="conversations")

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="plans")
    project = relationship("Project", back_populates="plans")
    steps = relationship("PlanStep", back_populates="plan")

class PlanStep(Base):
    __tablename__ = "plan_steps"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    order_index = Column(Integer)
    title = Column(String)
    description = Column(String)
    details = Column(String, nullable=True)
    is_completed = Column(Boolean, default=False)
    
    plan = relationship("Plan", back_populates="steps")
    executions = relationship("ExecutionLog", back_populates="step")

class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    step_id = Column(Integer, ForeignKey("plan_steps.id"), nullable=True)
    level = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    step = relationship("PlanStep", back_populates="executions")
    project = relationship("Project")

class TokenUsage(Base):
    __tablename__ = "token_usage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tokens_used = Column(Integer, default=0)
    cost = Column(String, default="0.00")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User")
