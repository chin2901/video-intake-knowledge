"""
video_intake_schemas — Paquete de JSON Schemas versionados para video-intake-knowledge.

Este paquete agrupa todos los JSON Schemas del sistema en un formato
instalable, permitiendo validación de datos fuera del paquete principal
cuando sea necesario.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Ruta al directorio de schemas (relativo a este archivo)
_SCHEMAS_DIR = Path(__file__).parent.parent / "video_intake_core" / "schemas"


def get_schema(name: str) -> dict[str, Any] | None:
    """
    Obtener un schema por nombre (sin extensión).

    Args:
        name: Nombre del schema (ej. "source", "job", "artifact_manifest").

    Returns:
        El schema como diccionario, o None si no existe.
    """
    schema_path = _SCHEMAS_DIR / f"{name}.json"
    if not schema_path.exists():
        return None
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def get_all_schemas() -> dict[str, dict[str, Any]]:
    """
    Obtener todos los schemas disponibles.

    Returns:
        Diccionario nombre -> schema.
    """
    result = {}
    if not _SCHEMAS_DIR.exists():
        return result
    for schema_file in _SCHEMAS_DIR.glob("*.json"):
        name = schema_file.stem
        with open(schema_file, encoding="utf-8") as f:
            result[name] = json.load(f)
    return result


def list_schemas() -> list[str]:
    """
    Listar todos los nombres de schemas disponibles.

    Returns:
        Lista de nombres de schemas.
    """
    if not _SCHEMAS_DIR.exists():
        return []
    return [f.stem for f in _SCHEMAS_DIR.glob("*.json")]


def validate(data: Any, schema_name: str) -> bool:
    """
    Validar datos contra un schema.

    Esta función usa jsonschema si está disponible, o hace una validación
    básica si no.

    Args:
        data: Datos a validar.
        schema_name: Nombre del schema.

    Returns:
        True si los datos son válidos, False en caso contrario.
    """
    schema = get_schema(schema_name)
    if schema is None:
        return False

    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return True
    except ImportError:
        # Validación básica sin jsonschema
        return _basic_validate(data, schema)


def _basic_validate(data: Any, schema: dict[str, Any]) -> bool:
    """
    Validación básica sin jsonschema (solo verifica tipos y required).
    """
    if not isinstance(data, dict):
        return False

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field in required:
        if field not in data:
            return False

    # Verificar tipos básicos
    for key, value in data.items():
        if key in properties:
            prop = properties[key]
            expected_type = prop.get("type")
            if expected_type:
                type_map = {
                    "string": str,
                    "integer": int,
                    "number": (int, float),
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                expected = type_map.get(expected_type)
                if expected and not isinstance(value, expected):
                    return False

    return True


# Versión del paquete de schemas
__version__ = "1.0.0"

# Lista de schemas disponibles (para documentación)
AVAILABLE_SCHEMAS = [
    "source",
    "job",
    "artifact_manifest",
    "transcript_segment",
    "ocr_block",
    "audio_context",
    "visual_context",
    "knowledge_extraction",
    "build_proposal",
    "memory_entry",
    "memory_bank",
]
