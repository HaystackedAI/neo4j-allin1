from fastapi import APIRouter

from .neo4j import rouAI

rou = APIRouter()

rou.include_router(rouAI)
