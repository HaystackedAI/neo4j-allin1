from __future__ import annotations

import json
import os
import re
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
LOAN_MODEL_PATH = PROJECT_ROOT / "fibo" / "loan" / "neo4j_importer_model.json"


def _fibo_vocabulary() -> dict[str, list[dict[str, str]]]:
    model = json.loads(LOAN_MODEL_PATH.read_text(encoding="utf-8"))
    schema = model["dataModel"]["graphSchemaRepresentation"]["graphSchema"]
    return {
        "classes": [
            {"name": item["token"], "description": item.get("description", "")}
            for item in schema.get("nodeLabels", [])
        ],
        "properties": [
            {
                "name": f"{item['token']}.{prop['token']}",
                "domain": item["token"],
                "description": prop.get("description", ""),
            }
            for item in schema.get("nodeLabels", [])
            for prop in item.get("properties", [])
        ],
        "relationships": [
            {"name": item["token"], "description": item.get("description", "")}
            for item in schema.get("relationshipTypes", [])
        ],
    }


@legacyFiboRouter.get("/targets")
def list_fibo_targets():
    return _fibo_vocabulary()


@legacyFiboRouter.get("/sources")
def list_legacy_sources():
    legacy_dir = PROJECT_ROOT / "fibo" / "legacy"
    sql = (legacy_dir / "legacy_loan_demo.sql").read_text(encoding="utf-8")
    dictionary = json.loads((legacy_dir / "data_dictionary.json").read_text(encoding="utf-8"))
    table_descriptions: dict[str, str] = dictionary["tables"]
    semantic_examples = {
        (table, field): meaning
        for table, field, meaning in dictionary.get("mapping_examples", [])
    }

    elements = []
    table_blocks = re.finditer(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);", sql, flags=re.IGNORECASE | re.DOTALL
    )
    for table_match in table_blocks:
        table_name, body = table_match.groups()
        table_name = table_name.upper()
        table_description = table_descriptions.get(table_name, "Legacy source table.")
        elements.append({
            "sourceRef": f"entity|{table_name}",
            "sourceKind": "entity",
            "sourceTable": table_name,
            "sourceField": None,
            "graphElement": table_name,
            "description": table_description,
            "fiboTargetKind": "class",
        })

        for line in body.splitlines():
            column_definition, _, inline_comment = line.partition("--")
            column_definition = column_definition.strip().rstrip(",").strip()
            column = re.match(r"([A-Za-z_]\w*)\s+(.+)$", column_definition)
            if not column:
                continue
            field_name, definition = column.groups()
            if field_name.upper() in {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}:
                continue
            field_name = field_name.upper()
            data_type = definition.split()[0].upper()
            meaning = semantic_examples.get((table_name, field_name))
            details = [f"{table_name}.{field_name} ({data_type})"]
            if inline_comment:
                details.append(inline_comment.strip())
            if meaning:
                details.append(f"Starter semantic example: {meaning}")
            elements.append({
                "sourceRef": f"field|{table_name}|{field_name}",
                "sourceKind": "field",
                "sourceTable": table_name,
                "sourceField": field_name,
                "graphElement": field_name,
                "description": " · ".join(details),
                "fiboTargetKind": "property",
                "semanticExample": meaning,
            })

            reference = re.search(r"\bREFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)", definition, re.IGNORECASE)
            if reference:
                target_table, target_field = reference.groups()
                target_table, target_field = target_table.upper(), target_field.upper()
                elements.append({
                    "sourceRef": f"relationship|{table_name}|{field_name}|{target_table}|{target_field}",
                    "sourceKind": "relationship",
                    "sourceTable": table_name,
                    "sourceField": field_name,
                    "graphElement": f"{table_name}.{field_name} → {target_table}.{target_field}",
                    "description": f"Foreign-key relationship from {table_name}.{field_name} to {target_table}.{target_field}.",
                    "fiboTargetKind": "relationship",
                })

    return {
        "sourceSystem": "Synthetic legacy commercial-loan SQL schema",
        "sourceFile": "fibo/legacy/legacy_loan_demo.sql",
        "elements": elements,
    }


class MappingInput(BaseModel):
    source_ref: str
    source_kind: Literal["entity", "field", "relationship"]
    source_table: str
    source_field: str | None = None
    graph_element: str
    fibo_target_kind: Literal["class", "property", "relationship"]
    fibo_iri: str | None = None
    fibo_label: str
    rationale: str = ""
    is_cde: bool = False
    cde_definition: str | None = None
    review_status: Literal["draft", "reviewed"] = "draft"

    @field_validator("fibo_iri")
    @classmethod
    def require_absolute_iri_when_provided(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.startswith(("https://", "http://")):
            raise ValueError("FIBO IRI must be an absolute HTTP or HTTPS URI")
        return value

    @model_validator(mode="after")
    def validate_source_target_and_cde(self) -> MappingInput:
        expected_target = {
            "entity": "class",
            "field": "property",
            "relationship": "relationship",
        }[self.source_kind]
        if self.fibo_target_kind != expected_target:
            raise ValueError(f"{self.source_kind} sources must map to a FIBO {expected_target}")
        vocabulary_key = {
            "class": "classes",
            "property": "properties",
            "relationship": "relationships",
        }[self.fibo_target_kind]
        valid_names = {item["name"] for item in _fibo_vocabulary()[vocabulary_key]}
        if self.fibo_label not in valid_names:
            raise ValueError(f"Choose a {self.fibo_target_kind} label from the current loan graph vocabulary")
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
