"""Auth utilities backed by PostgreSQL (via SQLAlchemy).

Provides:
    - password hashing (passlib pbkdf2_sha256)
    - JWT creation & verification (HS256)
    - FastAPI deps for current user
    - Login/Signup handlers using DB persistence

Environment:
    - DATABASE_URL: SQLAlchemy DB URL (e.g., postgresql+psycopg2://user:pass@localhost:5432/db)
    - BL_JWT_SECRET: JWT signing secret
"""
from __future__ import annotations
import os, time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
try:
    from dotenv import load_dotenv  # type: ignore
    from pathlib import Path
    # Load default .env (current working directory or parents)
    load_dotenv()
    # Also attempt to load backend/.env (when running from repo root)
    here = Path(__file__).resolve()
    backend_dir = here.parents[1]  # backend/
    backend_env = backend_dir / ".env"
    if backend_env.exists():
        load_dotenv(dotenv_path=str(backend_env), override=False)
except Exception:
    pass
from sqlalchemy.orm import Session

from .db import get_db
from .models_db import User

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
JWT_SECRET = os.environ.get("BL_JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 12  # 12h

pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ---------------------------------------------------------------------------
# No in-memory users; DB holds records. We'll lazily seed a guest user at init.

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PublicUser(BaseModel):
    username: str
    email: str
    plan: str
    created_at: int

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(pw, hashed)
    except Exception:
        return False

def create_access_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

# ---------------------------------------------------------------------------
# FastAPI deps
# ---------------------------------------------------------------------------

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    cred_exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        username: str | None = payload.get("sub")
        if not username:
            raise cred_exc
    except JWTError:
        raise cred_exc
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise cred_exc
    return user

# ---------------------------------------------------------------------------
# Auth endpoint handlers
# ---------------------------------------------------------------------------

def handle_login(db: Session = Depends(get_db), form: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token(user.username)
    return Token(access_token=token)

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class SignupResponse(BaseModel):
    user: PublicUser
    token: str


def handle_signup(req: SignupRequest, db: Session):
    # Unique checks
    if db.query(User).filter(User.username == req.username).first() is not None:
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == req.email).first() is not None:
        raise HTTPException(status_code=400, detail="Email already in use")
    # First real user becomes Admin (ignore seeded 'guest')
    try:
        non_guest_count = db.query(User).filter(User.username != "guest").count()
    except Exception:
        non_guest_count = 0
    plan_value = "Admin" if non_guest_count == 0 else "Guest"
    rec = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        plan=plan_value,
        created_at=int(time.time()),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    token = create_access_token(req.username)
    return SignupResponse(user=to_public(rec), token=token)

# Public projection

def to_public(user: User) -> PublicUser:
    return PublicUser(username=user.username, email=user.email, plan=user.plan, created_at=user.created_at)


# Optional initializer to seed a guest user for demo purposes
def ensure_seed_user(db: Session):
    if db.query(User).filter(User.username == "guest").first() is None:
        u = User(
            username="guest",
            email="guest@example.com",
            password_hash=hash_password("guest"),
            plan="Guest",
            created_at=int(time.time()),
        )
        db.add(u)
        db.commit()

# ---------------------------------------------------------------------------
# Debug admin seeding (for development only)
# ---------------------------------------------------------------------------

def _env_truthy(name: str, default: str = "1") -> bool:
    v = os.environ.get(name, default)
    return str(v).strip().lower() in {"1", "true", "yes", "on"}

def debug_admin_username() -> str:
    return os.environ.get("BL_DEBUG_ADMIN_USER", "admin")

def is_debug_admin_username(username: str | None) -> bool:
    if not username:
        return False
    try:
        return str(username).strip().lower() == debug_admin_username().strip().lower()
    except Exception:
        return False

def ensure_debug_admin(db: Session):
    """Create or update a persistent Admin user for debugging.

    Controlled by env:
      - BL_ENABLE_DEBUG_ADMIN: default '1' (enabled). Set to '0' to disable.
      - BL_DEBUG_ADMIN_USER: default 'admin'
      - BL_DEBUG_ADMIN_EMAIL: default 'admin@local'
      - BL_DEBUG_ADMIN_PASSWORD: default 'admin'
    """
    if not _env_truthy("BL_ENABLE_DEBUG_ADMIN", "1"):
        return
    uname = os.environ.get("BL_DEBUG_ADMIN_USER", "admin")
    email = os.environ.get("BL_DEBUG_ADMIN_EMAIL", "admin@local")
    pw = os.environ.get("BL_DEBUG_ADMIN_PASSWORD", "admin")
    rec = db.query(User).filter(User.username == uname).first()
    now = int(time.time())
    if rec is None:
        rec = User(
            username=uname,
            email=email,
            password_hash=hash_password(pw),
            plan="Admin",
            created_at=now,
        )
        db.add(rec)
        db.commit()
    else:
        # Ensure it stays Admin and sync email if changed; update password if env changed
        changed = False
        if rec.plan != "Admin":
            rec.plan = "Admin"; changed = True
        if email and rec.email != email:
            rec.email = email; changed = True
        try:
            # Update password only if a non-empty env was provided
            if pw:
                rec.password_hash = hash_password(pw); changed = True
        except Exception:
            pass
        if changed:
            db.add(rec)
            db.commit()
