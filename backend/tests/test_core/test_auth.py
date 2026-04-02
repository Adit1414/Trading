import pytest
import jwt
from fastapi import HTTPException

from app.core.auth import decode_token, get_current_user, _jwt_secret

def test_jwt_secret_valid(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.SUPABASE_JWT_SECRET", "valid_secret_length_32_chars_12345!")
    assert _jwt_secret() == "valid_secret_length_32_chars_12345!"

def test_jwt_secret_unconfigured(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.SUPABASE_JWT_SECRET", "")
    with pytest.raises(HTTPException) as exc:
        _jwt_secret()
    assert exc.value.status_code == 503

def test_decode_token_success(monkeypatch, mocker):
    monkeypatch.setattr("app.core.config.settings.SUPABASE_JWT_SECRET", "secret")
    mocker.patch("jwt.decode", return_value={"sub": "user-uuid-1234"})
    assert decode_token("valid_token") == "user-uuid-1234"

def test_decode_token_expired(monkeypatch, mocker):
    monkeypatch.setattr("app.core.config.settings.SUPABASE_JWT_SECRET", "secret")
    mocker.patch("jwt.decode", side_effect=jwt.ExpiredSignatureError)
    with pytest.raises(HTTPException) as exc:
        decode_token("token")
    assert exc.value.status_code == 401

def test_decode_token_missing_sub(monkeypatch, mocker):
    monkeypatch.setattr("app.core.config.settings.SUPABASE_JWT_SECRET", "secret")
    mocker.patch("jwt.decode", return_value={"other": "data"})
    with pytest.raises(HTTPException) as exc:
        decode_token("token")
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_no_credentials():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None)
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_valid(mocker):
    class FakeCreds:
        credentials = "my_token"
    mocker.patch("app.core.auth.decode_token", return_value="user-id")
    res = await get_current_user(FakeCreds())
    assert res == "user-id"
