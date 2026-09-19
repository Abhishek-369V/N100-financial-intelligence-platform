"""
Sprint 6, Day 38: FastAPI Application Scaffold

Run with: uvicorn src.api.main:app --port 8000 --reload
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies, screener, sectors, peers, valuation, portfolio, documents, health,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("n100_api")

app = FastAPI(
    title="N100 Financial Intelligence API",
    description="REST API for the Nifty 100 Financial Intelligence Platform",
    version="1.0.0",
)

# Internal use only -- spec explicitly says allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} - {duration_ms}ms - {response.status_code}")
    return response


app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(companies.router, prefix="/api/v1", tags=["companies"])
app.include_router(screener.router, prefix="/api/v1", tags=["screener"])
app.include_router(sectors.router, prefix="/api/v1", tags=["sectors"])
app.include_router(peers.router, prefix="/api/v1", tags=["peers"])
app.include_router(valuation.router, prefix="/api/v1", tags=["valuation"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])