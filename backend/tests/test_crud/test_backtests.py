import pytest
from unittest.mock import AsyncMock, MagicMock
from app.crud.backtests import (
    create_backtest, get_backtest, list_backtests_for_user,
    list_all_backtests, delete_backtest
)

@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Mock for single scalar result
    mock_result_single = MagicMock()
    mock_result_single.scalar_one_or_none.return_value = MagicMock(id="bt-123", user_id="user-123")
    
    # Mock for list result
    mock_result_list = MagicMock()
    mock_result_list.scalars().all.return_value = [MagicMock(id="bt-123")]
    
    # Assign default response, which will be overridden as needed
    session.execute.return_value = mock_result_single
    return session

@pytest.mark.asyncio
async def test_create_backtest(mock_session):
    res = await create_backtest(
        session=mock_session,
        user_id="user-123",
        strategy_id="strat-123",
        symbol="BTCUSDT",
        timeframe="1d",
        parameters={},
        metrics={}
    )
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()
    assert res.symbol == "BTCUSDT"

@pytest.mark.asyncio
async def test_get_backtest(mock_session):
    res = await get_backtest(mock_session, "bt-123")
    mock_session.execute.assert_called_once()
    assert res is not None

@pytest.mark.asyncio
async def test_list_backtests_for_user(mock_session):
    mock_result_list = MagicMock()
    mock_result_list.scalars().all.return_value = [MagicMock(id="bt-123")]
    mock_session.execute.return_value = mock_result_list
    
    res = await list_backtests_for_user(mock_session, "user-123")
    mock_session.execute.assert_called_once()
    assert len(res) == 1

@pytest.mark.asyncio
async def test_list_all_backtests(mock_session):
    mock_result_list = MagicMock()
    mock_result_list.scalars().all.return_value = [MagicMock(id="bt-123")]
    mock_session.execute.return_value = mock_result_list
    
    res = await list_all_backtests(mock_session)
    mock_session.execute.assert_called_once()
    assert len(res) == 1

@pytest.mark.asyncio
async def test_delete_backtest_success(mock_session):
    res = await delete_backtest(mock_session, "bt-123", user_id="user-123")
    mock_session.delete.assert_called_once()
    assert res is True

@pytest.mark.asyncio
async def test_delete_backtest_wrong_user(mock_session):
    res = await delete_backtest(mock_session, "bt-123", user_id="wrong-user")
    mock_session.delete.assert_not_called()
    assert res is False

@pytest.mark.asyncio
async def test_delete_backtest_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    res = await delete_backtest(mock_session, "bt-invalid", user_id="user-123")
    mock_session.delete.assert_not_called()
    assert res is False
