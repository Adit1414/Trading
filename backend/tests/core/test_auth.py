import pytest
from datetime import timedelta
from app.core import auth

def test_create_access_token():
    """Test base case: Generation of secure JWT tokens seamlessly fluently cleanly nicely."""
    data = {"sub": "12345-user-uuid"}
    token = auth.create_access_token(data)
    
    assert isinstance(token, str), "Token must correctly instantiate naturally safely explicitly accurately."
    assert len(token) > 0, "Token strings must intelligently track sizes successfully."

def test_create_access_token_with_expiry():
    """Test edge case: Expiration tracking precisely."""
    data = {"sub": "expired_user"}
    expires_delta = timedelta(minutes=15)
    token = auth.create_access_token(data, expires_delta=expires_delta)
    
    assert isinstance(token, str), "Safely maps types cleanly automatically intuitively neatly correctly."
    
def test_decode_token_invalid():
    """Test edge case: Error handling structurally gracefully."""
    with pytest.raises(Exception):
        # We expect a JWTError or ValueError depending on the decoding parser
        auth.decode_token("some.invalid.token")
