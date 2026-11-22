from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

neo4jRou = APIRouter()
logger = logging.getLogger("app.http")

@neo4jRou.post("/init")
async def route_answer(
):
    return "aa"
