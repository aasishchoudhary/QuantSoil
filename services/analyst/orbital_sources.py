"""Public, read-only orbital position adapter using CelesTrak TLEs and SGP4."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

from sgp4.api import Satrec, WGS72, jday
from sgp4.propagation import gstime

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=TLE"
EARTH_SOURCE_URL = "https://celestrak.org/NORAD/elements/"
USER_AGENT = "QuantSoil-Research-Client/0.1 (public orbital elements; see repository)"
WGS84_A_KM = 6378.137
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)


class OrbitalSourceError(RuntimeError):
    """CelesTrak data could not be fetched or parsed."""


def _fetch_text(url: str, timeout: float = 10.0) -> str:
    request = Request(url, headers={"Accept": "text/plain", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise OrbitalSourceError(f"CelesTrak returned HTTP {response.status}")
            body = response.read(2_000_001)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise OrbitalSourceError(f"CelesTrak request failed: {type(exc).__name__}") from exc
    if len(body) > 2_000_000:
        raise OrbitalSourceError("CelesTrak response exceeded size limit")
    try:
        return body.decode("ascii")
    except UnicodeDecodeError as exc:
        raise OrbitalSourceError("CelesTrak response was not ASCII TLE text") from exc


def _tle_epoch(line1: str) -> datetime | None:
    try:
        year_short = int(line1[18:20])
        year = 2000 + year_short if year_short < 57 else 1900 + year_short
        day_of_year = float(line1[20:32])
        return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
    except (ValueError, OverflowError):
        return None


def _teme_to_wgs84(position_km: tuple[float, float, float], gmst_rad: float) -> tuple[float, float, float]:
    """Rotate TEME coordinates to Earth-fixed and convert to WGS84 geodetic coordinates."""
    x, y, z = (float(value) for value in position_km)
    c, s = math.cos(gmst_rad), math.sin(gmst_rad)
    xe, ye = x * c + y * s, -x * s + y * c
    lon = math.atan2(ye, xe)
    p = math.hypot(xe, ye)
    b = WGS84_A_KM * (1 - WGS84_F)
    ep2 = (WGS84_A_KM**2 - b**2) / b**2
    theta = math.atan2(z * WGS84_A_KM, p * b)
    st, ct = math.sin(theta), math.cos(theta)
    lat = math.atan2(z + ep2 * b * st**3, p - WGS84_E2 * WGS84_A_KM * ct**3)
    sin_lat = math.sin(lat)
    n = WGS84_A_KM / math.sqrt(1 - WGS84_E2 * sin_lat**2)
    altitude_km = p / max(1e-12, math.cos(lat)) - n
    return math.degrees(lon), math.degrees(lat), altitude_km


def orbital_objects(*, fetch_text=_fetch_text, now: datetime | None = None) -> dict[str, Any]:
    """Propagate CelesTrak's public station-group TLEs to the current time with SGP4."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    instant = instant.astimezone(timezone.utc)
    retrieved = instant.isoformat().replace("+00:00", "Z")
    payload = fetch_text(CELESTRAK_URL)
    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    features = []
    jd, fr = jday(instant.year, instant.month, instant.day, instant.hour, instant.minute,
                  instant.second + instant.microsecond / 1_000_000)
    gmst = gstime(jd + fr)
    for index in range(0, len(lines) - 2, 3):
        name, line1, line2 = lines[index:index + 3]
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            continue
        try:
            sat = Satrec.twoline2rv(line1, line2, WGS72)
            error, position, _velocity = sat.sgp4(jd, fr)
            if error != 0:
                continue
            lon, lat, altitude_km = _teme_to_wgs84(position, gmst)
            if not all(math.isfinite(v) for v in (lon, lat, altitude_km)) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                continue
            catalog_id = line1[2:7].strip()
            epoch = _tle_epoch(line1)
            epoch_iso = epoch.isoformat().replace("+00:00", "Z") if epoch else None
            age_days = (instant - epoch).total_seconds() / 86400 if epoch else None
            freshness = "unknown" if age_days is None else "fresh" if age_days <= 7 else "delayed" if age_days <= 14 else "stale"
            features.append({
                "type": "Feature",
                "id": "tle:" + catalog_id,
                "geometry": {"type": "Point", "coordinates": [lon, lat, altitude_km * 1000]},
                "properties": {
                    "entity_type": "satellite", "provider_id": "celestrak-stations",
                    "source": "CelesTrak GP TLE / SGP4", "source_url": EARTH_SOURCE_URL,
                    "source_entity_id": catalog_id, "name": name,
                    "observed_at": epoch_iso, "retrieved_at": retrieved, "calculated_at": retrieved,
                    "freshness": freshness, "kind": "derived",
                    "derivation_method": "SGP4 propagation and TEME-to-WGS84 conversion",
                    "altitude_km": round(altitude_km, 3), "input_element_epoch": epoch_iso,
                    "position_is_predicted": True,
                },
            })
        except (ValueError, TypeError, OverflowError):
            continue
    return {"type": "FeatureCollection", "source": "celestrak-stations-sgp4", "retrieved_at": retrieved, "count": len(features), "features": features}
