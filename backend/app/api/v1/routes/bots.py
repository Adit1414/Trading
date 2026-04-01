import asyncio
import json
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/bots", tags=["bots"])

# In-memory store
bots_db: Dict[str, Dict[str, Any]] = {}

class BotCreateRequest(BaseModel):
    symbol: str
    is_testnet: bool
    strategy_id: str
    parameters: dict
    take_profit: float | None = None
    stop_loss: float | None = None

class BotStateRequest(BaseModel):
    state: str

@router.get("")
async def get_bots():
    return list(bots_db.values())

@router.post("")
async def create_bot(req: BotCreateRequest):
    bot_id = str(uuid.uuid4())
    bot_data = {
        "id": bot_id,
        "symbol": req.symbol,
        "is_testnet": req.is_testnet,
        "strategy_id": req.strategy_id,
        "parameters": req.parameters,
        "take_profit": req.take_profit,
        "stop_loss": req.stop_loss,
        "status": "RUNNING",
        "pnl": 0.0,
    }
    bots_db[bot_id] = bot_data
    return bot_data

@router.put("/{bot_id}/state")
async def update_bot_state(bot_id: str, req: BotStateRequest, request: Request):
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = bots_db[bot_id]
    if req.state not in ["RUNNING", "PAUSED", "STOPPED"]:
        raise HTTPException(status_code=400, detail="Invalid target state")
    
    # Simple state transition validation
    if bot["status"] == "STOPPED":
        raise HTTPException(status_code=400, detail="Cannot restart a stopped bot.")
        
    bot["status"] = req.state
    return bot

@router.get("/events")
async def bot_events(request: Request):
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                # Yield an occasional heartbeat to keep the SSE connection alive
                yield f"data: {json.dumps({'type': 'HEARTBEAT', 'message': 'ping'})}\n\n"
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
