import unittest
from packages.geospatial.observation_contract import ObservationValidationError, validate_observation

BASE = {
    "observation_id": "obs-1", "provider_id": "fixture", "entity_type": "aircraft",
    "source_entity_id": "ABC123", "source_url": "https://example.org/data/ABC123",
    "license_id": "test-fixture", "observed_at": "2026-10-12T08:00:00Z",
    "retrieved_at": "2026-10-12T08:00:02+00:00",
    "geometry": {"type": "Point", "coordinates": [87.0, 25.0]},
    "properties": {"altitude_m": 9000}, "provenance_refs": ["evidence-1"]
}

class ObservationContractTests(unittest.TestCase):
    def test_valid_observation_is_canonicalized_and_hashed(self):
        item = validate_observation(BASE)
        self.assertEqual(item["schema_version"], "1.0")
        self.assertEqual(len(item["content_hash"]), 64)
        self.assertEqual(item["freshness"], "unknown")

    def test_rejects_invalid_longitude(self):
        raw = {**BASE, "geometry": {"type": "Point", "coordinates": [181, 25]}}
        with self.assertRaises(ObservationValidationError):
            validate_observation(raw)

    def test_rejects_timezone_naive_timestamp(self):
        raw = {**BASE, "observed_at": "2026-10-12T08:00:00"}
        with self.assertRaises(ObservationValidationError):
            validate_observation(raw)

    def test_simulated_data_cannot_look_fresh(self):
        item = validate_observation({**BASE, "kind": "simulated", "freshness": "fresh"})
        self.assertEqual(item["freshness"], "simulated")

    def test_rejects_non_http_source_url(self):
        raw = {**BASE, "source_url": "file:///etc/passwd"}
        with self.assertRaises(ObservationValidationError):
            validate_observation(raw)

if __name__ == "__main__":
    unittest.main()
