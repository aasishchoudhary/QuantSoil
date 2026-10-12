"""Public, read-only geospatial source adapters.

These adapters fetch documented public feeds and normalize them into GeoJSON.
They never write authoritative world state. Provider timestamps are preserved;
retrieval time is not represented as observation time.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USGS_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
ADSB_BASE = "https://api.adsb.lol/v2"
USER_AGENT = "QuantSoil-Research-Client/0.1 (public geospatial data; contact via repository)"


class PublicSourceError(RuntimeError):
    """A public data provider could not return a usable response."""


def _fetch_json(url: str, *, timeout: float = 8.0) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/geo+json, application/json", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise PublicSourceError(f"provider returned HTTP {response.status}")
            body = response.read(8_000_001)
            if len(body) > 8_000_000:
                raise PublicSourceError("provider response exceeds the 8 MB safety limit")
            payload = json.loads(body)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PublicSourceError(f"public provider request failed: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise PublicSourceError("provider response must be a JSON object")
    return payload


def _iso_ms(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def earthquakes(*, fetch_json=_fetch_json) -> dict[str, Any]:
    """Return USGS's public past-hour earthquake feed as provenance-rich GeoJSON."""
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = fetch_json(USGS_FEED)
    features = []
    for item in payload.get("features", []):
        if not isinstance(item, dict) or not isinstance(item.get("geometry"), dict):
            continue
        coords = item["geometry"].get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        props = item.get("properties") if isinstance(item.get("properties"), dict) else {}
        observed = _iso_ms(props.get("time"))
        source_id = str(item.get("id") or props.get("code") or "")
        features.append({
            "type": "Feature",
            "id": "usgs:" + source_id,
            "geometry": {"type": "Point", "coordinates": coords[:3]},
            "properties": {
                "entity_type": "earthquake",
                "name": props.get("title") or props.get("place") or source_id,
                "provider_id": "usgs-earthquakes",
                "source": "USGS Earthquake Hazards Program",
                "source_url": props.get("url") or "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
                "source_entity_id": source_id,
                "observed_at": observed,
                "retrieved_at": retrieved,
                "freshness": "unknown" if not observed else "fresh" if (datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(observed.replace("Z", "+00:00")).timestamp()) <= 3600 else "stale",
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "event_status": props.get("status"),
                "event_updated_at": _iso_ms(props.get("updated")),
                "kind": "observed",
            },
        })
    return {"type": "FeatureCollection", "source": "usgs-earthquakes", "retrieved_at": retrieved, "features": features, "count": len(features)}


def aircraft_for_bbox(bbox: tuple[float, float, float, float], *, fetch_json=_fetch_json) -> dict[str, Any]:
    """Fetch ADS-B aircraft around the viewport center (maximum 250 km radius).

    Coverage is local/regional and depends on volunteer receiver availability.
    The adapter intentionally does not imply global coverage.
    """
    if len(bbox) != 4:
        raise ValueError("bbox must contain minLon,minLat,maxLon,maxLat")
    west, south, east, north = (float(v) for v in bbox)
    if not all(math.isfinite(v) for v in (west, south, east, north)):
        raise ValueError("bbox coordinates must be finite")
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        raise ValueError("bbox outside WGS84 bounds")
    if south > north:
        raise ValueError("bbox has inverted latitude bounds")
    if west > east:
        # Longitude wraps at the antimeridian. Query each side independently so
        # the center calculation never points at Greenwich for a dateline view.
        left = aircraft_for_bbox((west, south, 180.0, north), fetch_json=fetch_json)
        right = aircraft_for_bbox((-180.0, south, east, north), fetch_json=fetch_json)
        by_id = {}
        for feature in left["features"] + right["features"]:
            by_id.setdefault(feature["id"], feature)
        features = list(by_id.values())
        return {
            "type": "FeatureCollection",
            "source": "adsb-lol",
            "retrieved_at": max(left["retrieved_at"], right["retrieved_at"]),
            "coverage_radius_nm": max(left["coverage_radius_nm"], right["coverage_radius_nm"]),
            "count": len(features),
            "features": features,
            "coverage_note": "Antimeridian viewport queried as two regional requests; receiver coverage varies.",
        }
    lat = (south + north) / 2
    lon = (west + east) / 2
    # Approximate bounding-box half-diagonal in km, capped to the documented endpoint limit.
    lat_km = (north - south) * 111.0 / 2
    lon_km = (east - west) * 111.0 * max(0.05, math.cos(math.radians(lat))) / 2
    radius_nm = max(5, min(250, int(math.ceil(math.hypot(lat_km, lon_km) / 1.852))))
    url = f"{ADSB_BASE}/lat/{lat:.5f}/lon/{lon:.5f}/dist/{radius_nm}"
    retrieved_dt = datetime.now(timezone.utc)
    retrieved = retrieved_dt.isoformat().replace("+00:00", "Z")
    payload = fetch_json(url)
    features = []
    for item in payload.get("aircraft", []):
        if not isinstance(item, dict):
            continue
        try:
            aircraft_lat, aircraft_lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (-90 <= aircraft_lat <= 90 and -180 <= aircraft_lon <= 180):
            continue
        seen_seconds = item.get("seen_pos")
        try:
            observed_dt = datetime.fromtimestamp(retrieved_dt.timestamp() - max(0, float(seen_seconds)), tz=timezone.utc) if seen_seconds is not None else None
        except (TypeError, ValueError, OverflowError, OSError):
            observed_dt = None
        observed = observed_dt.isoformat().replace("+00:00", "Z") if observed_dt else None
        age = (retrieved_dt - observed_dt).total_seconds() if observed_dt else None
        freshness = "unknown" if age is None else "fresh" if age <= 120 else "delayed" if age <= 600 else "stale"
        hex_id = str(item.get("hex") or item.get("r") or "unknown")
        callsign = str(item.get("flight") or "").strip() or None
        props = {
            "entity_type": "aircraft", "provider_id": "adsb-lol", "source": "adsb.lol ADS-B network",
            "source_url": "https://adsb.lol/", "source_entity_id": hex_id,
            "name": callsign or hex_id, "callsign": callsign, "registration": item.get("r"),
            "aircraft_type": item.get("t"), "observed_at": observed, "retrieved_at": retrieved,
            "freshness": freshness, "kind": "observed", "coverage_note": "Receiver coverage varies; not global or guaranteed.",
            "altitude_baro_ft": item.get("alt_baro"), "ground_speed_kt": item.get("gs"),
            "track_deg": item.get("track"), "vertical_rate_fpm": item.get("baro_rate"),
            "squawk": item.get("squawk"), "on_ground": item.get("alt_baro") == "ground" or item.get("on_ground") is True,
        }
        features.append({
            "type": "Feature", "id": "adsb:" + hex_id,
            "geometry": {"type": "Point", "coordinates": [aircraft_lon, aircraft_lat]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "source": "adsb-lol", "retrieved_at": retrieved, "coverage_radius_nm": radius_nm, "count": len(features), "features": features}
