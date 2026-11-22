from fastapi import APIRouter

from .neo4j_basic import neo4jRou

rouAI = APIRouter()

rouAI.include_router(neo4jRou, prefix="/neo4j", tags=["Neo4j"])
