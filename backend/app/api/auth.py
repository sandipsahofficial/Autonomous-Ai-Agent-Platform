from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, ApiKey, UserRole
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_raw_api_key,
    hash_api_key,
)
from app.auth.dependencies import get_current_user
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account with secure password hashing.
    """
    # Check duplicate username
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered.",
        )
    # Check duplicate email
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered.",
        )

    # Validate role assignment (only allow recognized roles; default operator)
    role_val = payload.role if payload.role in (UserRole.ADMIN.value, UserRole.OPERATOR.value, UserRole.VIEWER.value) else UserRole.OPERATOR.value

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role_val,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate username/password and issue an HS256-signed JWT access token.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    token = create_access_token({
        "sub": user.id,
        "username": user.username,
        "role": user.role,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieve profile and permissions for the currently authenticated identity.
    """
    return current_user


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new API key for programmatic access.
    The raw secret key is returned exactly once upon creation.
    """
    raw_key = generate_raw_api_key()
    key_digest = hash_api_key(raw_key)

    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    api_key_rec = ApiKey(
        user_id=current_user.id,
        key_hash=key_digest,
        name=payload.name,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(api_key_rec)
    db.commit()
    db.refresh(api_key_rec)

    return ApiKeyCreatedResponse(
        id=api_key_rec.id,
        name=api_key_rec.name,
        raw_api_key=raw_key,
        expires_at=api_key_rec.expires_at,
        created_at=api_key_rec.created_at,
    )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List active API keys belonging to the authenticated user.
    """
    return db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently revoke and delete an API key.
    Enforces tenant ownership.
    """
    key_rec = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"API key '{key_id}' not found.")
    if key_rec.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: You do not own this API key.")
    db.delete(key_rec)
    db.commit()
    return None


@router.post("/api-keys/{key_id}/revoke", response_model=dict)
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Immediately deactivates an API key without deleting the record.
    Enforces tenant ownership.
    """
    key_rec = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"API key '{key_id}' not found.")
    if key_rec.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: You do not own this API key.")
    key_rec.is_active = False
    db.commit()
    return {"success": True, "id": key_id, "is_active": False}
