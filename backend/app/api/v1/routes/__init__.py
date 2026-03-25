"""
app/api/v1/__init__.py
Aggregates all v1 route modules.
"""
from fastapi import APIRouter

from app.api.v1.routes import backtest
from app.api.v1.routes import backtest_db
from app.api.v1.routes import strategies_db

api_router = APIRouter()
api_router.include_router(backtest.router)
api_router.include_router(backtest_db.router)
api_router.include_router(strategies_db.router)