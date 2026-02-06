from fastapi import Depends, HTTPException, status, APIRouter
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.schemas import User  # SQLAlchemy model
from backend.models import Register, Token, Login  # Pydantic schemas
import os
from passlib.context import CryptContext
from dotenv import load_dotenv
load_dotenv()



router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    """Verify a plain-text password against its bcrypt hash.

    Args:
        plain_password: The raw password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hash a plain-text password using bcrypt.

    Args:
        password: The raw password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict):
    """Create a JWT access token with an expiration claim.

    Args:
        data: Payload dict (must include 'sub' for the username).

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Decode JWT token and return the authenticated User ORM object.

    Args:
        token: Bearer token extracted from the Authorization header.
        db: Database session (injected).

    Returns:
        The SQLAlchemy User instance for the authenticated user.

    Raises:
        HTTPException 401: If the token is invalid or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register")
async def register(user: Register, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    Creates a new user with hashed password and stores in database.
    
    Args:
        user: Registration data (username and password)
        db: Database session
        
    Returns:
        Success message upon registration
        
    Raises:
        HTTPException: 400 if username already exists
    """
    user_db = db.query(User).filter(User.username == user.username).first()
    if user_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    new_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "message": "User registered successfully"
    }


@router.post("/token", response_model=Token)
async def login(user_data: Login, db: Session = Depends(get_db)):
    """
    Authenticate user and generate JWT access token.
    
    Validates credentials and returns a bearer token for API access.
    
    Args:
        user_data: Login credentials (username and password)
        db: Database session
        
    Returns:
        JWT access token and token type
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }