"""
app/api/v1/__init__.py
Aggregates all v1 route modules.
"""
from fastapi import APIRouter

from app.api.v1.routes import backtest
from app.api.v1.routes import backtest_db
from app.api.v1.routes import strategies_db
from app.api.v1.routes import bots
from app.api.v1.routes import paper
from app.api.v1.routes import live_trading
from app.api.v1.routes import users

api_router = APIRouter()
api_router.include_router(backtest.router)
api_router.include_router(backtest_db.router)
api_router.include_router(strategies_db.router)
api_router.include_router(bots.router)
api_router.include_router(paper.router)
api_router.include_router(live_trading.router)
api_router.include_router(users.router)