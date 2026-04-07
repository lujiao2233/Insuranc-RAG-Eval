"""认证服务
处理用户认证、密码哈希、JWT token生成等业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional
import uuid
from sqlalchemy.orm import Session

# Fix for passlib compatibility with bcrypt 4.0.0+
import bcrypt
if not hasattr(bcrypt, "__about__"):
    class BcryptAbout:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = BcryptAbout()

from passlib.context import CryptContext
from jose import JWTError, jwt

from config.settings import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from models.database import User as UserModel
from schemas import UserCreate


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_user(db: Session, user_data: UserCreate) -> UserModel:
    """创建新用户"""
    hashed_password = get_password_hash(user_data.password)
    user = UserModel(
        id=str(uuid.uuid4()),
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    """根据用户名获取用户"""
    return db.query(UserModel).filter(UserModel.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """根据邮箱获取用户"""
    return db.query(UserModel).filter(UserModel.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[UserModel]:
    """认证用户"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """验证JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
