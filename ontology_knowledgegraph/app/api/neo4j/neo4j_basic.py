from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.fibo_connector import FiboConnector

neo4jRou = APIRouter()
neo4jconn = FiboConnector()
logger = logging.getLogger("app.http")

class CypherRequest(BaseModel):
    cypher: str
    parameters: dict[str, Any] = Field(default_factory=dict)

@neo4jRou.post("/query")
def run_cypher(request: CypherRequest):
    return neo4jconn.run(request.cypher, request.parameters)
