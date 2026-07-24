"""
FastAPI Authentication Router integrating Supabase Auth.
"""
from __future__ import annotations

import logging
import uuid
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config.settings import get_settings
from database.connection import get_db_session
from database.models.user_model import UserModel
from database.models.refresh_token import RefreshTokenModel
from auth.services.password_service import PasswordService

from backend.auth.supabase_auth import SupabaseAuthHelper
from backend.auth.jwt_manager import create_access_token, hash_refresh_token
from backend.auth.session_manager import SessionManagerBackend
from backend.models.user import (
    RegisterRequest, LoginRequest, ForgotPasswordRequest,
    OnboardingRequest, TokenRefreshRequest, SSOExchangeRequest
)
from backend.services.auth_service import AuthBackendService

logger = logging.getLogger("mediverse.backend.router.auth")
router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer(auto_error=False)
supabase_helper = SupabaseAuthHelper()

def get_fresh_settings():
    get_settings.cache_clear()
    return get_settings()

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30



def get_db():
    """FastAPI database session dependency."""
    with get_db_session() as session:
        yield session


def _make_auth_response(user_db: UserModel, access_token: str, refresh_token: str) -> dict:
    return {
        "success": True,
        "token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "user": {
            "uid": str(user_db.id),
            "id": str(user_db.id),
            "email": user_db.email,
            "username": user_db.username,
            "full_name": user_db.full_name or "",
            "name": user_db.full_name or "",
            "role": user_db.role,
            "is_active": user_db.is_active,
            "is_verified": user_db.is_verified,
            "is_onboarded": user_db.is_onboarded,
            "photo_url": user_db.avatar_url or "",
            "avatar_url": user_db.avatar_url or "",
            "provider": user_db.auth_provider or "local"
        }
    }


def get_current_user_from_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)) -> UserModel:
    """Bypassed Authentication: Returns default developer user directly."""
    import uuid
    dev_user = db.query(UserModel).filter_by(email="developer@mediverse.ai").first()
    if not dev_user:
        dev_user = UserModel(
            id=uuid.UUID("d3b07384-d113-4e4e-9c29-0d1b918fcf10"),
            email="developer@mediverse.ai",
            username="developer",
            password_hash="BypassedAuth",
            full_name="Developer Operator",
            role="doctor",
            is_active=True,
            is_verified=True,
            is_onboarded=True
        )
        db.add(dev_user)
        db.commit()
    return dev_user



@router.post("/register")
@router.post("/signup")
def signup(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    username = req.username.strip()

    is_valid, strength_error = PasswordService.validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=strength_error)

    email_exists = db.query(UserModel).filter_by(email=email).first() is not None
    username_exists = db.query(UserModel).filter_by(username=username).first() is not None

    if email_exists:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")
    if username_exists:
        raise HTTPException(status_code=400, detail="Username is already taken.")

    # Supabase registration
    try:
        supabase_res = supabase_helper.signup_user(email, req.password)
        # Handle auto-assigning ID if returned from Supabase
        supabase_uid = None
        if "user" in supabase_res and "id" in supabase_res["user"]:
            supabase_uid = supabase_res["user"]["id"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    password_hash = PasswordService.hash_password(req.password)

    new_user = UserModel(
        id=uuid.uuid4(),
        email=email,
        username=username,
        password_hash=password_hash,
        supabase_uid=supabase_uid,
        full_name=req.full_name,
        role=req.role,
        is_active=True,
        is_verified=True,
        auth_provider="local"
    )
    db.add(new_user)
    db.flush()

    access_token = create_access_token(new_user.id, new_user.email, new_user.role)
    refresh_raw = uuid.uuid4().hex
    refresh_hash = hash_refresh_token(refresh_raw)

    db_refresh = RefreshTokenModel(
        id=uuid.uuid4(),
        user_id=new_user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh)
    db.commit()

    return _make_auth_response(new_user, access_token, refresh_raw)


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    user = db.query(UserModel).filter_by(email=email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This user account has been deactivated.")

    # Supabase Auth Sign In validation
    try:
        supabase_helper.login_user(email, req.password)
    except Exception as e:
        # Fallback to local password check if offline/mock
        if not user.password_hash or not PasswordService.verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

    access_token = create_access_token(user.id, user.email, user.role)
    refresh_raw = uuid.uuid4().hex
    refresh_hash = hash_refresh_token(refresh_raw)

    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1

    db_refresh = RefreshTokenModel(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh)
    db.commit()

    return _make_auth_response(user, access_token, refresh_raw)


@router.post("/token")
def auth_token(req: LoginRequest, db: Session = Depends(get_db)):
    return login(req, db)


@router.get("/google/signin")
@router.get("/google")
def google_signin(port: int = 52210):
    """Generates the Supabase OAuth redirect URL for Google Sign-In."""
    logger.info("Redirecting user to Supabase Google Auth...")
    settings = get_fresh_settings()
    if not settings.supabase_url:
        raise HTTPException(status_code=500, detail="Supabase URL is not configured.")

    redirect_target = f"{settings.google_redirect_uri}?port={port}"
    params = {
        "provider": "google",
        "redirect_to": redirect_target
    }
    supabase_auth_url = f"{settings.supabase_url}/auth/v1/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(supabase_auth_url)


@router.get("/google/callback")
def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handles callback after successful Supabase/Google authentication."""
    query_params = dict(request.query_params)
    port = int(query_params.get("port", "52210"))
    
    access_token = query_params.get("access_token")
    refresh_token = query_params.get("refresh_token")
    email = query_params.get("email") or "google.user@mediverse.ai"
    full_name = query_params.get("full_name") or "Google User"
    supabase_uid = query_params.get("supabase_uid") or f"sb-{uuid.uuid4().hex[:12]}"

    user = db.query(UserModel).filter(
        (UserModel.email == email.lower().strip()) | 
        (UserModel.supabase_uid == supabase_uid)
    ).first()

    if not user:
        # Register automatically
        base_username = email.split("@")[0]
        username = base_username
        count = 1
        while db.query(UserModel).filter_by(username=username).first():
            username = f"{base_username}{count}"
            count += 1

        user = UserModel(
            id=uuid.uuid4(),
            email=email,
            username=username,
            password_hash="SSO_GOOGLE_AUTHENTICATED",
            supabase_uid=supabase_uid,
            full_name=full_name,
            role="medical_student",
            is_active=True,
            is_verified=True,
            is_onboarded=False,
            auth_provider="google"
        )
        db.add(user)
        db.flush()

    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1

    local_access_token = create_access_token(user.id, user.email, user.role)
    local_refresh_token = uuid.uuid4().hex
    refresh_hash = hash_refresh_token(local_refresh_token)

    db_refresh = RefreshTokenModel(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh)
    db.commit()

    response_url = (
        f"http://127.0.0.1:{port}/auth/callback?"
        f"token={local_access_token}&"
        f"refresh_token={local_refresh_token}&"
        f"user_id={user.id}&"
        f"email={user.email}&"
        f"username={user.username}&"
        f"full_name={urllib.parse.quote(user.full_name or '')}&"
        f"role={user.role}&"
        f"is_onboarded={'true' if user.is_onboarded else 'false'}"
    )
    return RedirectResponse(response_url)


@router.get("/apple/signin")
@router.get("/apple/login")
def apple_signin(port: int = 52210):
    settings = get_fresh_settings()
    if not settings.supabase_url:
        raise HTTPException(status_code=500, detail="Supabase URL is not configured.")
    redirect_target = f"{settings.google_redirect_uri}?port={port}"
    params = {
        "provider": "apple",
        "redirect_to": redirect_target
    }
    supabase_auth_url = f"{settings.supabase_url}/auth/v1/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(supabase_auth_url)


@router.post("/sso")
def exchange_sso_credentials(req: SSOExchangeRequest, db: Session = Depends(get_db)):
    """Exchange OAuth credentials directly (used when client does direct OAuth flows)."""
    email = req.email.lower().strip()
    supabase_uid = req.uid

    user = db.query(UserModel).filter(
        (UserModel.email == email) | (UserModel.supabase_uid == supabase_uid)
    ).first()

    if not user:
        base_username = email.split("@")[0]
        username = base_username
        count = 1
        while db.query(UserModel).filter_by(username=username).first():
            username = f"{base_username}{count}"
            count += 1

        user = UserModel(
            id=uuid.uuid4(),
            email=email,
            username=username,
            password_hash=f"SSO_{req.provider.upper()}_AUTHENTICATED",
            supabase_uid=supabase_uid,
            full_name=req.full_name,
            avatar_url=req.avatar_url,
            auth_provider=req.provider.lower(),
            role="medical_student",
            is_active=True,
            is_verified=True,
            is_onboarded=False
        )
        db.add(user)
        db.flush()

    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1

    access_token = create_access_token(user.id, user.email, user.role)
    refresh_raw = uuid.uuid4().hex
    refresh_hash = hash_refresh_token(refresh_raw)

    db_refresh = RefreshTokenModel(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh)
    db.commit()

    return _make_auth_response(user, access_token, refresh_raw)


@router.post("/forgot-password")
@router.post("/reset-password")
def forgot_password(req: ForgotPasswordRequest):
    try:
        supabase_helper.trigger_password_reset(req.email)
        return {"status": "success", "message": "Password reset link has been dispatched via Supabase."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
def refresh_token(req: TokenRefreshRequest, db: Session = Depends(get_db)):
    refresh_hash = hash_refresh_token(req.refresh_token)
    db_token = db.query(RefreshTokenModel).filter_by(token_hash=refresh_hash, is_revoked=False).first()

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db_token.is_revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token has expired.")

    user = db.query(UserModel).filter_by(id=db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is deactivated or invalid.")

    # Rotate token
    new_refresh = uuid.uuid4().hex
    new_hash = hash_refresh_token(new_refresh)

    db_token.is_revoked = True

    new_db_refresh = RefreshTokenModel(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=new_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_db_refresh)
    db.commit()

    access_token = create_access_token(user.id, user.email, user.role)
    return _make_auth_response(user, access_token, new_refresh)


@router.post("/onboarding")
def complete_onboarding(req: OnboardingRequest, current_user: UserModel = Depends(get_current_user_from_jwt), db: Session = Depends(get_db)):
    valid_roles = ["doctor", "medical_student", "researcher", "student", "patient", "admin"]
    role = req.role.lower().strip()
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid system role selection.")

    user = db.query(UserModel).filter_by(id=current_user.id).first()
    user.role = role
    user.is_onboarded = True
    db.commit()

    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_onboarded": user.is_onboarded
    }


@router.post("/logout")
def logout(req: TokenRefreshRequest, current_user: UserModel = Depends(get_current_user_from_jwt), db: Session = Depends(get_db)):
    refresh_hash = hash_refresh_token(req.refresh_token)
    db_token = db.query(RefreshTokenModel).filter_by(token_hash=refresh_hash, user_id=current_user.id).first()
    if db_token:
        db_token.is_revoked = True
        db.commit()
    return {"status": "success", "message": "Tokens revoked and logged out."}


@router.get("/me")
def get_me(current_user: UserModel = Depends(get_current_user_from_jwt)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "is_onboarded": current_user.is_onboarded
    }


@router.get("/verify")
def verify_configuration():
    """Verify backend Supabase & Google configuration."""
    return supabase_helper.verify_config()

