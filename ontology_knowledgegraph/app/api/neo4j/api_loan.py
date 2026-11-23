from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from config.fibo_connector import FiboConnector
from app.config import get_settings_singleton

loanRou = APIRouter()
neo4jconn = FiboConnector()
logger = logging.getLogger("app.http")
NODE_ID_PROPERTIES = {
    "Person": "personId",
    "Loan": "loanId",
    "LoanApplication": "applicationId",
    "LoanProduct": "productId",
    "Property": "propertyId",
    "Appraisal": "appraisalId",
    "Payment": "paymentId",
    "FinancialInstitution": "institutionId",
    "LoanOfficer": "officerId",
}
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

@loanRou.post("/query")
def run_cypher(request: CypherRequest):
    return neo4jconn.run(request.cypher, request.parameters)


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


@loanRou.get("/nodes/{label}/{node_id}/connections")
def node_connections(label: str, node_id: str):
    id_property = NODE_ID_PROPERTIES.get(label)
    if id_property is None:
        raise HTTPException(status_code=400, detail=f"Unsupported node label: {label}")

    cypher = f"""
        MATCH (source:`{label}` {{{id_property}: $node_id}})-[relationship]-(neighbor)
        WITH source, relationship, neighbor,
             CASE
                 WHEN neighbor:Person THEN neighbor.personId
                 WHEN neighbor:Loan THEN neighbor.loanId
                 WHEN neighbor:LoanApplication THEN neighbor.applicationId
                 WHEN neighbor:LoanProduct THEN neighbor.productId
                 WHEN neighbor:Property THEN neighbor.propertyId
                 WHEN neighbor:Appraisal THEN neighbor.appraisalId
                 WHEN neighbor:Payment THEN neighbor.paymentId
                 WHEN neighbor:FinancialInstitution THEN neighbor.institutionId
                 WHEN neighbor:LoanOfficer THEN neighbor.officerId
             END AS neighbor_id,
             CASE
                 WHEN neighbor:Person THEN neighbor.name
                 WHEN neighbor:Loan THEN neighbor.loanId
                 WHEN neighbor:LoanApplication THEN neighbor.applicationId
                 WHEN neighbor:LoanProduct THEN neighbor.name
                 WHEN neighbor:Property THEN neighbor.address
                 WHEN neighbor:Appraisal THEN neighbor.appraisalId
                 WHEN neighbor:Payment THEN neighbor.paymentId
                 WHEN neighbor:FinancialInstitution THEN neighbor.name
                 WHEN neighbor:LoanOfficer THEN neighbor.name
             END AS neighbor_name
        RETURN type(relationship) AS relationshipType,
               CASE WHEN startNode(relationship) = source THEN 'outgoing' ELSE 'incoming' END AS direction,
               properties(relationship) AS relationshipProperties,
               {{label: labels(neighbor)[0], id: neighbor_id, name: neighbor_name}} AS node
        ORDER BY relationshipType, node.name
    """
    return neo4jconn.run(cypher, {"node_id": node_id})
