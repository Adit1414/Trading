import pytest
import json
from fastapi import HTTPException

from app.core.idempotency import idempotency_dep, IdempotencyContext, _CachedResponse

@pytest.mark.asyncio
async def test_idempotency_dep_no_key(mocker):
    res = await idempotency_dep(request=mocker.MagicMock(), idempotency_key=None)
    assert res.key is None

@pytest.mark.asyncio
async def test_idempotency_dep_invalid_key(mocker):
    with pytest.raises(HTTPException) as exc:
        await idempotency_dep(request=mocker.MagicMock(), idempotency_key="invalid-uuid")
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_idempotency_dep_no_redis(mocker):
    mocker.patch("app.core.idempotency.get_redis", return_value=None)
    res = await idempotency_dep(request=mocker.MagicMock(), idempotency_key="11111111-1111-4111-8111-111111111111")
    assert res.key == "11111111-1111-4111-8111-111111111111"
    
@pytest.mark.asyncio
async def test_idempotency_dep_cache_hit(mocker):
    mock_redis = mocker.AsyncMock()
    mock_redis.get.return_value = json.dumps({"status_code": 201, "body": {"ok": True}})
    mocker.patch("app.core.idempotency.get_redis", return_value=mock_redis)

    with pytest.raises(_CachedResponse) as exc:
        await idempotency_dep(request=mocker.MagicMock(), idempotency_key="11111111-1111-4111-8111-111111111111")
    
    assert exc.value.response.status_code == 200 # Returns 200 on replay
    assert json.loads(exc.value.response.body.decode()) == {"ok": True}

@pytest.mark.asyncio
async def test_idempotency_ctx_store(mocker):
    mock_redis = mocker.AsyncMock()
    mocker.patch("app.core.idempotency.get_redis", return_value=mock_redis)
    ctx = IdempotencyContext(key="11111111-1111-4111-8111-111111111111")
    await ctx.store({"ok": True}, 201)
    
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0] == "idempotency:11111111-1111-4111-8111-111111111111"
    assert json.loads(args[1]) == {"status_code": 201, "body": {"ok": True}}
