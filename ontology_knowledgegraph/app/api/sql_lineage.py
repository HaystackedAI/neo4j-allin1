from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from .legacy_fibo_mapping import engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DIR = PROJECT_ROOT / "fibo" / "legacy"
sqlLineageRouter = APIRouter(prefix="/sql-lineage", tags=["SQL Lineage"])


def _parse_legacy_schema() -> list[dict[str, object]]:
    sql = (LEGACY_DIR / "legacy_loan_demo.sql").read_text(encoding="utf-8")
    dictionary = json.loads((LEGACY_DIR / "data_dictionary.json").read_text(encoding="utf-8"))
    descriptions: dict[str, str] = dictionary.get("tables", {})
    examples = {
        (table.upper(), field.upper()): meaning
        for table, field, meaning in dictionary.get("mapping_examples", [])
    }
    tables: list[dict[str, object]] = []

    for table_match in re.finditer(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);", sql, flags=re.IGNORECASE | re.DOTALL
    ):
        table_name, body = table_match.groups()
        table_name = table_name.upper()
        body_start = table_match.start(2)
        primary_keys: set[str] = set()
        for match in re.finditer(r"PRIMARY\s+KEY\s*\(([^)]+)\)", body, flags=re.IGNORECASE):
            primary_keys.update(part.strip().strip('"').upper() for part in match.group(1).split(","))

        fields: list[dict[str, object]] = []
        relationships: list[dict[str, str]] = []
        for line_match in re.finditer(r"[^\r\n]+", body):
            raw_line = line_match.group(0)
            column_definition, _, comment = raw_line.partition("--")
            column_definition = column_definition.strip().rstrip(",").strip()
            column_match = re.match(r"([A-Za-z_]\w*)\s+(.+)$", column_definition)
            if not column_match:
                continue
            field_name, definition = column_match.groups()
            field_name = field_name.upper()
            if field_name in {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}:
                continue

            data_type = definition.split()[0].upper()
            is_primary_key = field_name in primary_keys or bool(re.search(r"\bPRIMARY\s+KEY\b", definition, re.IGNORECASE))
            reference = re.search(
                r"\bREFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)", definition, re.IGNORECASE
            )
            foreign_key = None
            if reference:
                target_table, target_field = (part.upper() for part in reference.groups())
                foreign_key = {"table": target_table, "field": target_field}
                relationships.append({"field": field_name, "table": target_table, "targetField": target_field})

            fields.append({
                "name": field_name,
                "dataType": data_type,
                "nullable": not is_primary_key and not bool(re.search(r"\bNOT\s+NULL\b", definition, re.IGNORECASE)),
                "primaryKey": is_primary_key,
                "foreignKey": foreign_key,
                "sqlComment": comment.strip() or None,
                "semanticExample": examples.get((table_name, field_name)),
                "sourceLine": sql.count("\n", 0, body_start + line_match.start()) + 1,
                "sourceRef": f"field|{table_name}|{field_name}",
            })

        tables.append({
            "name": table_name,
            "description": descriptions.get(table_name, "Legacy source table."),
            "sourceLine": sql.count("\n", 0, table_match.start()) + 1,
            "sourceRef": f"entity|{table_name}",
            "fields": fields,
            "relationships": relationships,
        })

    return tables


@sqlLineageRouter.get("")
def get_sql_lineage():
    tables = _parse_legacy_schema()
    dictionary = json.loads((LEGACY_DIR / "data_dictionary.json").read_text(encoding="utf-8"))
    with engine.connect() as connection:
        mapping_rows = connection.execute(text(
            "SELECT source_ref, fibo_target_kind, fibo_label, rationale, is_cde, "
            "cde_definition, review_status FROM legacy_fibo_mappings"
        )).mappings().all()

    mappings = {row["source_ref"]: dict(row) for row in mapping_rows}
    table_by_name = {table["name"]: table for table in tables}
    incoming_by_table: dict[str, list[dict[str, str | dict[str, object] | None]]] = {
        table["name"]: [] for table in tables
    }
    field_count = 0
    relationship_count = 0
    cde_count = 0
    known_mapping_refs: set[str] = set()

    for table in tables:
        table["mapping"] = mappings.get(table["sourceRef"])
        known_mapping_refs.add(table["sourceRef"])
        for field in table["fields"]:
            field_count += 1
            field["mapping"] = mappings.get(field["sourceRef"])
            known_mapping_refs.add(field["sourceRef"])
            if field["mapping"] and field["mapping"]["is_cde"]:
                cde_count += 1
            foreign_key = field["foreignKey"]
            if foreign_key:
                relationship_count += 1
                target_table = table_by_name.get(foreign_key["table"])
                target_desc = target_table["description"] if target_table else ""
                relationship_ref = (
                    f"relationship|{table['name']}|{field['name']}|"
                    f"{foreign_key['table']}|{foreign_key['field']}"
                )
                known_mapping_refs.add(relationship_ref)
                field["relationshipMapping"] = mappings.get(relationship_ref)
                field["foreignKey"]["sourceRef"] = relationship_ref
                field["foreignKey"]["targetDescription"] = target_desc
                incoming_by_table.setdefault(foreign_key["table"], []).append({
                    "sourceTable": table["name"],
                    "sourceField": field["name"],
                    "targetField": foreign_key["field"],
                    "mapping": field["relationshipMapping"],
                })
    for table in tables:
        table["incomingRelationships"] = incoming_by_table.get(table["name"], [])

    return {
        "sourceFile": "fibo/legacy/legacy_loan_demo.sql",
        "syntheticOnly": bool(dictionary.get("synthetic_only", False)),
        "lineageScope": "Table, column, and declared foreign-key dependencies from the SQL schema. The script has no transformation queries, so value-level SQL lineage is not available.",
        "summary": {
            "tables": len(tables),
            "fields": field_count,
            "foreignKeys": relationship_count,
            "mappedElements": len(known_mapping_refs.intersection(mappings)),
            "cdes": cde_count,
        },
        "tables": tables,
    }
