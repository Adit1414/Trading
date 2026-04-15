import os
from cryptography.fernet import Fernet
from app.core.config import settings

_fernet = None

def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key:
            raise ValueError("ENCRYPTION_KEY is not set in environment.")
        _fernet = Fernet(key.encode('utf-8'))
    return _fernet

def encrypt_api_key(plain_text: str) -> str:
    return _get_fernet().encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_api_key(cipher_text: str) -> str:
    return _get_fernet().decrypt(cipher_text.encode('utf-8')).decode('utf-8')
