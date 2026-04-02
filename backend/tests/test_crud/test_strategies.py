import pytest
from unittest.mock import AsyncMock, MagicMock
from app.crud.strategies import get_strategy_by_id, get_strategy_by_type_code, list_strategies

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.mark.asyncio
async def test_get_strategy_by_id(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(id="strat-123")
    mock_session.execute.return_value = mock_result
    
    res = await get_strategy_by_id(mock_session, "strat-123")
    mock_session.execute.assert_called_once()
    assert res.id == "strat-123"

@pytest.mark.asyncio
async def test_get_strategy_by_type_code(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(type_code="EMA_CROSSOVER")
    mock_session.execute.return_value = mock_result
    
    res = await get_strategy_by_type_code(mock_session, "ema_crossover")
    mock_session.execute.assert_called_once()
    assert res.type_code == "EMA_CROSSOVER"

@pytest.mark.asyncio
async def test_list_strategies(mock_session):
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [MagicMock(id="strat-123")]
    mock_session.execute.return_value = mock_result
    
    res = await list_strategies(mock_session)
    mock_session.execute.assert_called_once()
    assert len(res) == 1
