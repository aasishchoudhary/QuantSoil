import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from services.analyst.public_sources import (
    PublicSourceError, PublicSourceNotConfigured, configured_geojson_feed,
)


class ConfiguredAuthorizedFeedTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "QUANTSOIL_AIS_GEOJSON_URL": "https://feed.example.test/ais.geojson",
            "QUANTSOIL_AIS_BEARER_TOKEN": "not-a-real-secret",
            "QUANTSOIL_AIS_PROVIDER_ID": "test-ais",
            "QUANTSOIL_AIS_LICENSE_ID": "test-license",
        }

    def test_normalizes_authorized_vessel_points_and_provenance(self):
        observed = datetime.now(timezone.utc).isoformat()
        payload = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "id": "mmsi-123",
                "geometry": {"type": "Point", "coordinates": [87.1, 25.2]},
                "properties": {"mmsi": "123", "observed_at": observed, "speed_knots": 4.5},
            }],
        }
        with patch.dict(os.environ, self.env, clear=False):
            result = configured_geojson_feed(
                "vessel", url_env="QUANTSOIL_AIS_GEOJSON_URL",
                token_env="QUANTSOIL_AIS_BEARER_TOKEN",
                provider_env="QUANTSOIL_AIS_PROVIDER_ID",
                license_env="QUANTSOIL_AIS_LICENSE_ID",
                payload_loader=lambda url: payload,
            )
        feature = result["features"][0]
        self.assertEqual(result["count"], 1)
        self.assertEqual(feature["properties"]["entity_type"], "vessel")
        self.assertEqual(feature["properties"]["provider_id"], "test-ais")
        self.assertEqual(feature["properties"]["license_id"], "test-license")
        self.assertEqual(feature["geometry"]["coordinates"], [87.1, 25.2])

    def test_unconfigured_feed_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PublicSourceNotConfigured):
                configured_geojson_feed(
                    "camera", url_env="MISSING_URL", token_env="MISSING_TOKEN",
                    provider_env="MISSING_PROVIDER", license_env="MISSING_LICENSE",
                    payload_loader=lambda _: {},
                )

    def test_insecure_feed_url_is_rejected(self):
        env = {**self.env, "QUANTSOIL_AIS_GEOJSON_URL": "http://feed.example.test/ais.geojson"}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(PublicSourceError):
                configured_geojson_feed(
                    "vessel", url_env="QUANTSOIL_AIS_GEOJSON_URL",
                    token_env="QUANTSOIL_AIS_BEARER_TOKEN",
                    provider_env="QUANTSOIL_AIS_PROVIDER_ID",
                    license_env="QUANTSOIL_AIS_LICENSE_ID",
                    payload_loader=lambda _: {},
                )

    def test_invalid_geometry_is_not_rendered(self):
        payload = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "id": "bad", "geometry": {"type": "Point", "coordinates": [181, 95]}, "properties": {}},
            {"type": "Feature", "id": "line", "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}, "properties": {}},
        ]}
        with patch.dict(os.environ, self.env, clear=False):
            result = configured_geojson_feed(
                "vessel", url_env="QUANTSOIL_AIS_GEOJSON_URL",
                token_env="QUANTSOIL_AIS_BEARER_TOKEN",
                provider_env="QUANTSOIL_AIS_PROVIDER_ID",
                license_env="QUANTSOIL_AIS_LICENSE_ID",
                payload_loader=lambda _: payload,
            )
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
