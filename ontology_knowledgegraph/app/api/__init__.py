from fastapi import APIRouter

from .neo4j import rouAI
from .legacy_fibo_mapping import legacyFiboRouter

rou = APIRouter()

rou.include_router(rouAI)
rou.include_router(legacyFiboRouter)
