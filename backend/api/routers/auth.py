"""认证API路由
处理用户认证、注册、登录等操作
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from api.dependencies import get_db, get_current_user, get_current_active_user
from schemas import User, UserCreate, Token
from services.auth_service import (
    create_user, 
    authenticate_user, 
    create_access_token,
    get_user_by_username,
    get_user_by_email
)
from config.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from models.database import User as UserModel

router = APIRouter()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    user = create_user(db, user_data)
    return User.from_orm(user)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录获取访问令牌"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def get_user_info(
    current_user: UserModel = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return User.from_orm(current_user)


@router.post("/refresh-token", response_model=Token)
async def refresh_access_token(
    current_user: UserModel = Depends(get_current_active_user)
):
    """刷新访问令牌"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "user_id": current_user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.put("/me", response_model=User)
async def update_user_info(
    update_data: dict,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    if "email" in update_data:
        existing_user = get_user_by_email(db, update_data["email"])
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        current_user.email = update_data["email"]
    
    if "full_name" in update_data:
        current_user.full_name = update_data["full_name"]
    
    db.commit()
    db.refresh(current_user)
    return User.from_orm(current_user)


@router.post("/logout")
async def logout(
    current_user: UserModel = Depends(get_current_active_user)
):
    """用户登出（客户端需要删除token）"""
    return {"message": "登出成功"}
