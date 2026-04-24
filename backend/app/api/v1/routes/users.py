import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.db.models import UserModel, ApiKeyModel, BotModel, TradeLogModel, BacktestModel
from app.core.security import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    timezone: str | None = None
    bio: str | None = None

class AvatarUpdate(BaseModel):
    avatar_url: str

class BinanceSettingsSubmit(BaseModel):
    binance_api_key: str
    binance_secret: str

@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user:
            return {
                "full_name": None,
                "phone": None,
                "timezone": None,
                "bio": None,
                "avatar_url": None,
            }
        return {
            "full_name": user.full_name,
            "phone": user.phone,
            "timezone": user.timezone,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
        }

@router.put("/profile")
async def update_profile(body: ProfileUpdate, user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user:
            # Create user if it doesn't exist (since auth is stubbed)
            user = UserModel(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
        
        if body.full_name is not None: user.full_name = body.full_name
        if body.phone is not None: user.phone = body.phone
        if body.timezone is not None: user.timezone = body.timezone
        if body.bio is not None: user.bio = body.bio
        
        await session.commit()
        return {"message": "Profile updated"}

@router.post("/profile/avatar")
async def update_avatar(body: AvatarUpdate, user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user:
            user = UserModel(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
        user.avatar_url = body.avatar_url
        await session.commit()
        return {"message": "Avatar updated"}

@router.get("/preferences/notifications")
async def get_notification_prefs(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user or not user.notification_preferences:
            return {}
        return user.notification_preferences

@router.put("/preferences/notifications")
async def update_notification_prefs(body: Dict[str, Any], user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user:
            user = UserModel(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
        user.notification_preferences = body
        await session.commit()
        return {"message": "Notification preferences updated"}

@router.get("/preferences/trading")
async def get_trading_prefs(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user or not user.trading_preferences:
            return {}
        return user.trading_preferences

@router.put("/preferences/trading")
async def update_trading_prefs(body: Dict[str, Any], user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if not user:
            user = UserModel(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
        user.trading_preferences = body
        await session.commit()
        return {"message": "Trading preferences updated"}

@router.get("/settings/binance")
async def get_binance_settings(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        key = result.scalar_one_or_none()
        if not key:
            return {"connected": False, "api_key_masked": None, "has_secret": False}
        
        try:
            decrypted = decrypt_api_key(key.binance_testnet_api_key)
            masked = decrypted[:4] + "..." + decrypted[-4:] if len(decrypted) > 8 else "***"
        except Exception:
            masked = "***"
            
        return {
            "connected": True,
            "api_key_masked": masked,
            "has_secret": True
        }

@router.post("/settings/binance")
async def save_binance_settings(body: BinanceSettingsSubmit, user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        key = result.scalar_one_or_none()
        
        enc_key = encrypt_api_key(body.binance_api_key)
        enc_secret = encrypt_api_key(body.binance_secret)
        
        if key:
            key.binance_testnet_api_key = enc_key
            key.binance_testnet_secret = enc_secret
        else:
            new_key = ApiKeyModel(
                user_id=user_id,
                binance_testnet_api_key=enc_key,
                binance_testnet_secret=enc_secret
            )
            session.add(new_key)
        await session.commit()
        return {"message": "Binance keys saved securely"}

@router.get("/sessions/active")
async def get_active_sessions(user_id: str = Depends(get_current_user)):
    return []

@router.delete("/sessions/revoke_all")
async def revoke_all_sessions(user_id: str = Depends(get_current_user)):
    return {"message": "Sessions revoked"}

@router.post("/security/2fa/setup")
async def setup_2fa(user_id: str = Depends(get_current_user)):
    return {"secret": "MOCK_2FA_SECRET"}

@router.post("/security/2fa/verify")
async def verify_2fa(code: dict, user_id: str = Depends(get_current_user)):
    return {"message": "2FA verified"}

@router.get("/export-data")
async def export_data(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id, "data": "MOCK_EXPORT_DATA"}

@router.delete("/account")
async def delete_account(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        user = await session.get(UserModel, user_id)
        if user:
            await session.delete(user)
            await session.commit()
    return {"message": "Account deleted"}
