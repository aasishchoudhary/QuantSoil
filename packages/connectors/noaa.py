"""Governed NOAA/NWS public alert connector.

The NWS API is open data and requires an identifying User-Agent. This
connector keeps the provider boundary explicit and remains fixture-testable.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Iterable, Mapping
from urllib.request import Request, urlopen

from packages.connectors.contracts import ConnectorError, SourceRecord, SourceSpec, utc_now


class NOAAWeatherAlertsConnector:
    """Fetch active National Weather Service alerts as evidence records."""

    spec = SourceSpec(
        source="noaa-nws-alerts-geojson",
        license_class="public/open",
        schema_version="nws-alerts-geojson-v1",
        parser_version="nws-alerts-parser-v1",
        max_age_seconds=900,
    )

    def __init__(
        self,
        url: str = "https://api.weather.gov/alerts/active",
        *,
        user_agent: str = "GodsEyeWorldIntelligence/0.1",
        fetcher=None,
    ) -> None:
        self.url = url
        self.user_agent = user_agent
        self._fetcher = fetcher

    def fetch(self, *, since: datetime | None = None) -> Iterable[SourceRecord]:
        document = (self._fetcher or self._default_fetch)(self.url)
        if not isinstance(document, Mapping) or document.get("type") != "FeatureCollection":
            raise ConnectorError("invalid NWS alerts GeoJSON FeatureCollection")

        for feature in document.get("features", []):
            if not isinstance(feature, Mapping):
                continue
            alert_id = feature.get("id")
            properties = feature.get("properties")
            if not alert_id or not isinstance(properties, Mapping):
                continue
            sent = _parse_timestamp(properties.get("sent"))
            if sent is None:
                continue
            if since is not None and sent < since:
                continue
            yield SourceRecord(
                str(alert_id),
                {"feature": feature},
                sent,
                max(utc_now(), sent),
            )

    def _default_fetch(self, url: str) -> Mapping[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/geo+json, application/json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                if response.status != 200:
                    raise ConnectorError(f"NWS HTTP status {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(f"NWS transport failure: {type(exc).__name__}") from exc


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return None
    return timestamp.astimezone(timezone.utc)
