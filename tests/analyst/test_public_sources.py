import unittest
from datetime import datetime, timezone
from services.analyst.public_sources import (
    PublicSourceError, aircraft_for_bbox, earthquakes,
)


class PublicSourceAdapterTests(unittest.TestCase):
    def test_usgs_feed_normalizes_observation_and_provenance(self):
        event_ms = int(datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc).timestamp() * 1000)
        def fake_fetch(url):
            self.assertIn("earthquake.usgs.gov", url)
            return {"features": [{
                "id": "test-event",
                "geometry": {"type": "Point", "coordinates": [87.1, 25.2, 12000]},
                "properties": {"time": event_ms, "updated": event_ms, "mag": 3.2,
                               "place": "test place", "url": "https://example.org/event"}
            }]}
        result = earthquakes(fetch_json=fake_fetch)
        self.assertEqual(result["count"], 1)
        feature = result["features"][0]
        self.assertEqual(feature["properties"]["provider_id"], "usgs-earthquakes")
        self.assertEqual(feature["properties"]["magnitude"], 3.2)
        self.assertTrue(feature["properties"]["observed_at"].endswith("Z"))
        self.assertEqual(feature["geometry"]["coordinates"], [87.1, 25.2, 12000])

    def test_aircraft_feed_normalizes_positions_and_freshness(self):
        called = []
        def fake_fetch(url):
            called.append(url)
            return {"aircraft": [{
                "hex": "abc123", "lat": 25.2, "lon": 87.1, "flight": "TEST123 ",
                "seen_pos": 10, "alt_baro": 9000, "gs": 240, "track": 180
            }]}
        result = aircraft_for_bbox((86.8, 24.9, 87.4, 25.5), fetch_json=fake_fetch)
        self.assertEqual(result["count"], 1)
        self.assertIn("/lat/25.20000/lon/87.10000/dist/", called[0])
        feature = result["features"][0]
        self.assertEqual(feature["id"], "adsb:abc123")
        self.assertEqual(feature["geometry"]["coordinates"], [87.1, 25.2])
        self.assertEqual(feature["properties"]["callsign"], "TEST123")
        self.assertEqual(feature["properties"]["freshness"], "fresh")
        self.assertEqual(feature["properties"]["ground_speed_kt"], 240)

    def test_antimeridian_bbox_queries_both_sides_and_deduplicates(self):
        called = []
        def fake_fetch(url):
            called.append(url)
            return {"aircraft": [{
                "hex": "dateline1", "lat": 10.0, "lon": 179.8,
                "seen_pos": 5, "on_ground": False
            }]}
        result = aircraft_for_bbox((179.0, 9.0, -179.0, 11.0), fetch_json=fake_fetch)
        self.assertEqual(len(called), 2)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["features"][0]["id"], "adsb:dateline1")
        self.assertIn("Antimeridian", result["coverage_note"])
        self.assertIn("/lon/179.50000/", called[0])
        self.assertIn("/lon/-179.50000/", called[1])

    def test_explicit_on_ground_flag_is_preserved(self):
        result = aircraft_for_bbox(
            (86.8, 24.9, 87.4, 25.5),
            fetch_json=lambda _: {"aircraft": [{
                "hex": "ground1", "lat": 25.2, "lon": 87.1,
                "alt_baro": 0, "on_ground": True
            }]},
        )
        self.assertTrue(result["features"][0]["properties"]["on_ground"])

    def test_aircraft_rejects_invalid_bbox(self):
        with self.assertRaises(ValueError):
            aircraft_for_bbox((181, 0, 182, 1), fetch_json=lambda _: {})

    def test_provider_errors_are_not_hidden_as_empty_data(self):
        def failed(_):
            raise PublicSourceError("provider down")
        with self.assertRaises(PublicSourceError):
            earthquakes(fetch_json=failed)


if __name__ == "__main__":
    unittest.main()
