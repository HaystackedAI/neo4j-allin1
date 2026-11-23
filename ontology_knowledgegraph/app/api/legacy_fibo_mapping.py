from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

database_url = os.getenv("PG_URL") or os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("Set PG_URL or DATABASE_URL for legacy-to-FIBO mappings")
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

engine = create_engine(database_url, pool_pre_ping=True)
legacyFiboRouter = APIRouter(prefix="/legacy-fibo-mapping", tags=["Legacy to FIBO Mapping"])


class MappingInput(BaseModel):
    source_ref: str
    source_kind: Literal["entity", "field", "relationship"]
    source_table: str
    source_field: str | None = None
    graph_element: str
    fibo_target_kind: Literal["class", "property"]
    fibo_iri: str
    fibo_label: str
    rationale: str = ""
    is_cde: bool = False
    cde_definition: str | None = None
    review_status: Literal["draft", "reviewed"] = "draft"

    @field_validator("fibo_iri")
    @classmethod
    def require_absolute_iri(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("https://", "http://")):
            raise ValueError("FIBO IRI must be an absolute HTTP or HTTPS URI")
        return value

    @model_validator(mode="after")
    def validate_source_target_and_cde(self) -> MappingInput:
        expected_target = "class" if self.source_kind == "entity" else "property"
        if self.fibo_target_kind != expected_target:
            raise ValueError(f"{self.source_kind} sources must map to a FIBO {expected_target}")
        if self.is_cde and self.source_kind != "field":
            raise ValueError("CDE designation applies to legacy fields")
        if self.is_cde and not (self.cde_definition or "").strip():
            raise ValueError("Enter a CDE definition when marking a field as a CDE")
        if not self.is_cde:
            self.cde_definition = None
        return self


def _mapping_values(mapping: MappingInput) -> dict[str, object]:
    return mapping.model_dump()


@legacyFiboRouter.get("/mappings")
def list_mappings():
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, source_ref, source_kind, source_table, source_field, graph_element, "
            "fibo_target_kind, fibo_iri, fibo_label, rationale, is_cde, cde_definition, "
            "review_status, created_at, updated_at "
            "FROM legacy_fibo_mappings ORDER BY source_table, source_field NULLS FIRST, id"
        )).mappings().all()
        return [dict(row) for row in rows]


@legacyFiboRouter.post("/mappings")
def create_mapping(mapping: MappingInput):
    values = _mapping_values(mapping)
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "INSERT INTO legacy_fibo_mappings "
                "(source_ref, source_kind, source_table, source_field, graph_element, "
                "fibo_target_kind, fibo_iri, fibo_label, rationale, is_cde, cde_definition, review_status) "
                "VALUES (:source_ref, :source_kind, :source_table, :source_field, :graph_element, "
                ":fibo_target_kind, :fibo_iri, :fibo_label, :rationale, :is_cde, :cde_definition, :review_status) "
                "RETURNING *"
            ),
            values,
        ).mappings().one()
        return dict(row)


@legacyFiboRouter.put("/mappings/{mapping_id}")
def update_mapping(mapping_id: int, mapping: MappingInput):
    values = _mapping_values(mapping)
    values["mapping_id"] = mapping_id
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "UPDATE legacy_fibo_mappings SET source_ref=:source_ref, source_kind=:source_kind, "
                "source_table=:source_table, source_field=:source_field, graph_element=:graph_element, "
                "fibo_target_kind=:fibo_target_kind, fibo_iri=:fibo_iri, fibo_label=:fibo_label, "
                "rationale=:rationale, is_cde=:is_cde, cde_definition=:cde_definition, "
                "review_status=:review_status, updated_at=now() WHERE id=:mapping_id RETURNING *"
            ),
            values,
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return dict(row)


@legacyFiboRouter.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: int):
    with engine.begin() as connection:
        result = connection.execute(
            text("DELETE FROM legacy_fibo_mappings WHERE id=:mapping_id"),
            {"mapping_id": mapping_id},
        )
        if result.rowcount != 1:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return {"deleted": True}
