from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from config.fibo_connector import FiboConnector
from app.config import get_settings_singleton

loanRou = APIRouter()
neo4jconn = FiboConnector()
logger = logging.getLogger("app.http")
settings = get_settings_singleton()
pg_url = os.getenv("PG_URL") or os.getenv("DATABASE_URL") or settings.TOO_SB_DB
if pg_url.startswith("postgresql+asyncpg://"):
    pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
pg_engine = create_engine(pg_url, pool_pre_ping=True)

class CypherRequest(BaseModel):
    cypher: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class SavedQueryRequest(BaseModel):
    name: str
    cypher: str


@loanRou.get("/borrowers")
def list_borrowers():
    cypher="""
        MATCH (p:Person) - [:BORROWER_ON]->(:Loan)
        RETURN DISTINCT p.personId AS borrowerId, p.name AS borrowerName
        ORDER BY borrowerName        
    """
    return neo4jconn.run(cypher)    

@loanRou.get("/borrowers/{borrower_id}")
def borrower_360(borrower_id: str):
    cypher = """
        MATCH (person:Person {personId: $borrower_id})
        OPTIONAL MATCH (person)-[borrowerRel:BORROWER_ON]->(loan:Loan)
        WITH person, collect(
            CASE WHEN loan IS NULL THEN null ELSE {
                loanId: loan.loanId,
                borrowerRole: borrowerRel.borrowerRole,
                status: loan.status,
                principalAmount: loan.principalAmount,
                currentBalance: loan.currentBalance,
                interestRate: loan.interestRate,
                originationDate: toString(loan.originationDate),
                maturityDate: toString(loan.maturityDate)
            } END
        ) AS loans
        RETURN {
            borrowerId: person.personId,
            borrowerName: person.name,
            loans: loans
        } AS borrower
    """
    return neo4jconn.run(cypher, {"borrower_id": borrower_id})


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    iso_format = getattr(value, "iso_format", None)
    if callable(iso_format):
        return iso_format()
    return value


@loanRou.get("/nodes/{label}/{id_property}/{node_id}/connections")
def node_connections(label: str, id_property: str, node_id: str):
    cypher = """
        MATCH (source:$( $label))
        WHERE source[$id_property] = $node_id
        MATCH (source)-[relationship]-(neighbor)
        WITH source, relationship, neighbor,
             head([key IN keys(neighbor) WHERE key ENDS WITH 'Id']) AS neighbor_id_property
        RETURN type(relationship) AS relationshipType,
               CASE WHEN startNode(relationship) = source THEN 'outgoing' ELSE 'incoming' END AS direction,
               properties(relationship) AS relationshipProperties,
               {
                   labels: labels(neighbor),
                   idProperty: neighbor_id_property,
                   id: neighbor[neighbor_id_property],
                   properties: properties(neighbor)
               } AS node
        ORDER BY relationshipType, node.id
    """
    rows = neo4jconn.run(cypher, {
        "label": label,
        "id_property": id_property,
        "node_id": node_id,
    })
    return _json_safe(rows)
