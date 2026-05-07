"""
D17 Burn Calculator - FastAPI backend.

Indexes XBT burn transactions on Solana via Helius, computes tranche
multipliers per the @xbt2027 official mechanics, exposes a simple JSON API
the frontend uses to render the calculator.

See docs/mechanics.md for the canonical reference.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from state import BurnState, MULTIPLIERS

# Send INFO and above from our own loggers (helius, indexer) to stdout so
# Render's log tail surfaces them. uvicorn already configures its access logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

load_dotenv()

BURN_ADDRESS = os.getenv("BURN_ADDRESS", "4Upb3WBoMSAaMC3eytHvSnL4hYLvDEL8zpQr4Q9U6JsB")
REFUND_ADDRESS = os.getenv("REFUND_ADDRESS", "DWUFCjBxqDuXpUGF8KnVzhAuz2uhRyfrky4aFc2JvvgH")
D17_TOTAL_SUPPLY = int(os.getenv("D17_TOTAL_SUPPLY", "1000000000"))  # 1B
EVENT_ALLOCATION = int(os.getenv("EVENT_ALLOCATION", "30000000"))  # 30M = 3% of 1B
EVENT_SHARE_PCT = (EVENT_ALLOCATION / D17_TOTAL_SUPPLY) * 100  # derived %, stays in sync

# Singleton state holder. The indexer fills it; the API reads from it.
state = BurnState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # On startup: kick off the indexing loop in the background.
    # On shutdown: cancel it cleanly.
    # Implemented in solana_rpc.py — provider-agnostic JSON-RPC indexer.
    from solana_rpc import start_indexer, stop_indexer

    task = await start_indexer(state)
    try:
        yield
    finally:
        await stop_indexer(task)


app = FastAPI(
    title="D17 Burn Calculator API",
    description="Indexes XBT burns and computes D17 allocation multipliers.",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the frontend (any origin during dev) to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class StateResponse(BaseModel):
    total_burns: int
    total_xbt_burned: float
    last_indexed_at: Optional[str]
    burn_address: str
    refund_address: str
    multipliers: list[float]
    event_share_pct: float
    event_allocation_tokens: int  # absolute D17 tokens for this event (30M)
    d17_total_supply: int  # absolute D17 supply (1B)


class SimulateRequest(BaseModel):
    amount: float
    extra_burns_after: int = 0  # how many txs you assume will burn after yours


class AllocationEntry(BaseModel):
    rank: int
    wallet: str
    tx_count: int
    total_burned: float  # XBT
    tranches: list[int]  # 1..10, sorted unique tranches the wallet appears in
    allocation_tokens: float  # absolute D17 tokens (float for fractional precision)
    allocation_pct_of_event: float  # % of the current 3% event share
    allocation_pct_of_supply: float  # % of total D17 supply (1B)


class SimulateResponse(BaseModel):
    your_position: int
    total_after_you: int
    your_tranche: int  # 1..10
    your_multiplier: float
    your_allocation_pct: float  # share of the current 3% event supply (% of 1B)
    your_allocation_tokens: float  # absolute D17 tokens
    note: str


@app.get("/")
def root() -> dict:
    return {
        "name": "D17 Burn Calculator API",
        "docs": "/docs",
        "endpoints": ["/state", "/simulate", "/allocations"],
    }


@app.get("/allocations", response_model=list[AllocationEntry])
def get_allocations() -> list[AllocationEntry]:
    """Per-wallet ranked allocation table for the current event."""
    rows = state.allocations(EVENT_ALLOCATION, D17_TOTAL_SUPPLY)
    return [AllocationEntry(**r) for r in rows]


@app.get("/state", response_model=StateResponse)
def get_state() -> StateResponse:
    s = state.snapshot()
    return StateResponse(
        total_burns=s.total_burns,
        total_xbt_burned=s.total_xbt_burned,
        last_indexed_at=s.last_indexed_at,
        burn_address=BURN_ADDRESS,
        refund_address=REFUND_ADDRESS,
        multipliers=list(MULTIPLIERS),
        event_share_pct=EVENT_SHARE_PCT,
        event_allocation_tokens=EVENT_ALLOCATION,
        d17_total_supply=D17_TOTAL_SUPPLY,
    )


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    if req.extra_burns_after < 0:
        raise HTTPException(status_code=400, detail="extra_burns_after must be >= 0")

    result = state.simulate(req.amount, req.extra_burns_after, EVENT_SHARE_PCT)
    # Derive absolute D17 tokens from the percentage of total supply.
    result["your_allocation_tokens"] = (
        result["your_allocation_pct"] / 100.0 * D17_TOTAL_SUPPLY
    )
    return SimulateResponse(**result)
