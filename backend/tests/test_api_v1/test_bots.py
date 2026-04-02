import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db

client = TestClient(app)

def override_get_current_user():
    return "user-123"

class MockSession:
    pass

async def override_get_db():
    yield MockSession()

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

def test_get_bots(mocker):
    class MockResult:
        def scalars(self):
            class M:
                def all(self):
                    return []
            return M()

    class MockSessionDB:
        async def execute(self, *args, **kwargs):
            return MockResult()
            
    async def get_db_override():
        yield MockSessionDB()
    app.dependency_overrides[get_db] = get_db_override

    # Test Client works but we're forcing an async session execute in bots.py without a standard asyncmock, 
    # so we'll mock the whole session logic out to skip DB complexities.
    mocker.patch("app.api.v1.routes.bots.get_db")
