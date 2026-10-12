"""Strict, dependency-free validation for normalized geospatial observations.

This module is a reusable contract boundary, not a provider adapter or database.
It deliberately distinguishes source observations from derived/simulated data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse
import hashlib
import json
import math

SCHEMA_VERSION = "1.0"
ALLOWED_KINDS = {"observed", "derived", "predicted", "simulated"}
ALLOWED_FRESHNESS = {"fresh", "delayed", "stale", "unknown", "unavailable", "simulated"}


class ObservationValidationError(ValueError):
    """Raised when an observation violates the normalized contract."""


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ObservationValidationError("timestamp must be a non-empty ISO-8601 string")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ObservationValidationError("timestamp must be ISO-8601") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ObservationValidationError("timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def validate_geometry(geometry: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(geometry, Mapping) or geometry.get("type") != "Point":
        raise ObservationValidationError("geometry must be a GeoJSON Point")
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) not in (2, 3):
        raise ObservationValidationError("Point coordinates must contain [longitude, latitude] and optional altitude")
    try:
        values = [float(item) for item in coordinates]
    except (TypeError, ValueError) as exc:
        raise ObservationValidationError("coordinates must be numeric") from exc
    if not all(math.isfinite(item) for item in values):
        raise ObservationValidationError("coordinates must be finite")
    lon, lat = values[:2]
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ObservationValidationError("coordinates out of WGS84 bounds")
    return {"type": "Point", "coordinates": values}


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ObservationValidationError(f"{key} must be a non-empty string")
    return value.strip()


def validate_observation(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and canonicalize a normalized observation envelope."""
    if not isinstance(raw, Mapping):
        raise ObservationValidationError("observation must be an object")
    result = dict(raw)
    for key in ("observation_id", "provider_id", "entity_type", "source_entity_id", "source_url", "license_id"):
        result[key] = _required_text(result, key)
    parsed_url = urlparse(result["source_url"])
    if parsed_url.scheme not in {"https", "http"} or not parsed_url.netloc:
        raise ObservationValidationError("source_url must be an absolute HTTP(S) URL")
    result["observed_at"] = parse_timestamp(result.get("observed_at")).isoformat().replace("+00:00", "Z")
    result["retrieved_at"] = parse_timestamp(result.get("retrieved_at")).isoformat().replace("+00:00", "Z")
    result["geometry"] = validate_geometry(result.get("geometry"))
    kind = result.get("kind", "observed")
    if kind not in ALLOWED_KINDS:
        raise ObservationValidationError(f"kind must be one of {sorted(ALLOWED_KINDS)}")
    result["kind"] = kind
    if kind == "simulated":
        result["freshness"] = "simulated"
    else:
        freshness = result.get("freshness", "unknown")
        if freshness not in ALLOWED_FRESHNESS - {"simulated"}:
            raise ObservationValidationError("invalid freshness state for non-simulated data")
        result["freshness"] = freshness
    if not isinstance(result.get("properties", {}), Mapping):
        raise ObservationValidationError("properties must be an object")
    result["properties"] = dict(result.get("properties", {}))
    refs = result.get("provenance_refs", [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ObservationValidationError("provenance_refs must be a list of non-empty strings")
    result["provenance_refs"] = refs
    result["schema_version"] = SCHEMA_VERSION
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    result["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return result
