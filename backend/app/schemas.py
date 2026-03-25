from pydantic import BaseModel
from typing import List, Optional
import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ProjectCreate(BaseModel):
    title: str

class ProjectBase(BaseModel):
    id: int
    title: str
    updated_at: datetime.datetime
    class Config:
        from_attributes = True

class ChatPrompt(BaseModel):
    text: str
    project_id: int

class ConversationBase(BaseModel):
    id: int
    sender: str
    text: str
    timestamp: datetime.datetime
    class Config:
        from_attributes = True

class ExecutionLogBase(BaseModel):
    id: int
    level: str
    message: str
    timestamp: datetime.datetime
    class Config:
        from_attributes = True

class PlanStepBase(BaseModel):
    id: int
    order_index: int
    title: str
    description: str
    details: Optional[str] = None
    is_completed: bool
    executions: List[ExecutionLogBase] = []
    class Config:
        from_attributes = True

class PlanBase(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime.datetime
    steps: List[PlanStepBase] = []
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    status: str
    message: str

class TokenUsageBase(BaseModel):
    user_id: int
    tokens_used: int
    cost: str
    class Config:
        from_attributes = True
