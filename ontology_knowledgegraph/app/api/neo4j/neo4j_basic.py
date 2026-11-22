from __future__ import annotations

import logging

from fastapi import APIRouter

neo4jRou = APIRouter()
logger = logging.getLogger("app.http")

@neo4jRou.post("/init")
async def route_answer(
):
    return "aa"
 