"""Simple JWT auth for the React frontend. Works alongside the existing app/ engine."""
import hashlib
import time
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.db.database import get_connection

SECRET_KEY = "mnemosyne-ai-secret-key-change-in-production"
ALGORITHM = "HS256"

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + 86400 * 30}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    username = verify_token(credentials.credentials)
    if not username:
        raise HTTPException(401, "Invalid token")
    return username


def _ensure_users_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


@router.post("/register")
def register(req: RegisterRequest):
    _ensure_users_table()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(400, "Username already exists")

    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (req.username, hash_password(req.password))
    )
    conn.commit()
    conn.close()

    return {"access_token": create_token(req.username), "token_type": "bearer"}


@router.post("/login")
def login(req: LoginRequest):
    _ensure_users_table()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (req.username,)
    )
    row = cur.fetchone()
    conn.close()

    if not row or row["password_hash"] != hash_password(req.password):
        raise HTTPException(401, "Invalid credentials")

    return {"access_token": create_token(req.username), "token_type": "bearer"}
