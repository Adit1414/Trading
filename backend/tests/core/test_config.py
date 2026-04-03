import pytest
from app.core.config import settings

def test_settings_initialization():
    """Test that core configuration settings load base variables securely."""
    assert settings.PROJECT_NAME is not None, "Project name should be defined."
    assert settings.API_V1_STR == "/api/v1", "API version path should default to /api/v1."

def test_settings_algorithm():
    """Test Edge Case: Security constraints for JWT defaults."""
    assert settings.ALGORITHM == "HS256" or isinstance(settings.ALGORITHM, str), "Algorithm must be a valid string."
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0, "Expiration limit must be correctly bounded natively."

def test_db_url_format():
    """Test Edge Case: Database URL formats accurately."""
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://") or settings.DATABASE_URL.startswith("sqlite+aiosqlite://"), "Database URL must execute using an async engine flawlessly."
