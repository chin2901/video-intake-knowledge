"""
JSON Schemas for video_intake_knowledge.

Defines versioned schemas for all core data structures used across the system.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).parent

# All schema definitions as dictionaries (compatible with jsonschema Draft 7)


def get_schema(name: str) -> dict[str, Any]:
    """Load a schema by name from the schemas directory."""
    schema_file = SCHEMAS_DIR / f"{name}.json"
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema not found: {name}")
    with open(schema_file) as f:
        return json.load(f)


def get_all_schemas() -> dict[str, dict[str, Any]]:
    """Load all schemas from the schemas directory."""
    schemas = {}
    for schema_file in sorted(SCHEMAS_DIR.glob("*.json")):
        name = schema_file.stem
        with open(schema_file) as f:
            schemas[name] = json.load(f)
    return schemas


def validate(data: Any, schema_name: str) -> list[str]:
    """Validate data against a named schema.

    Args:
        data: The data to validate.
        schema_name: Name of the schema (without .json extension).

    Returns:
        List of validation error messages (empty if valid).
    """
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed — skipping validation"]

    schema = get_schema(schema_name)
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    return [err.message for err in errors]


__all__ = ["get_schema", "get_all_schemas", "validate", "validate_against_schema"]


def validate_against_schema(data: Any, schema_name: str) -> list[str]:
    """Validate data against a named schema.
    
    Alias for validate(). Validates data against a JSON schema
    and returns a list of error messages.
    """
    return validate(data, schema_name)
