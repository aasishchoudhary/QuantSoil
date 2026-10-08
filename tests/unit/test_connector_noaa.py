from datetime import datetime, timezone
from packages.connectors.noaa import NOAAWeatherAlertsConnector

T = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def alert_document(sent="2026-01-01T11:59:00Z"):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.demo",
                "type": "Feature",
                "geometry": None,
                "properties": {
                    "id": "urn:oid:2.49.0.1.840.0.demo",
                    "sent": sent,
                    "event": "Test Alert",
                    "status": "Actual",
                },
            }
        ],
    }


def test_noaa_alert_connector_is_fixture_testable_and_provenance_ready():
    connector = NOAAWeatherAlertsConnector(fetcher=lambda _: alert_document())
    records = list(connector.fetch())
    assert len(records) == 1
    record = records[0]
    assert record.source_record_id.startswith("https://api.weather.gov/alerts/")
    assert record.observed_at == datetime(2026, 1, 1, 11, 59, tzinfo=timezone.utc)
    assert record.acquired_at >= record.observed_at
    assert record.payload["feature"]["properties"]["event"] == "Test Alert"


def test_noaa_alert_connector_respects_since():
    connector = NOAAWeatherAlertsConnector(
        fetcher=lambda _: alert_document("2026-01-01T11:59:00Z")
    )
    assert list(connector.fetch(since=T)) == []
