import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from services.analyst import orbital_sources


TLE1 = "1 25544U 98067A   21275.51005787  .00001490  00000-0  33223-4 0  9993"
TLE2 = "2 25544  51.6443 208.9905 0004208  71.8769  39.3891 15.48815329302845"


class FakeSatellite:
    def sgp4(self, jd, fr):
        return 0, (7000.0, 0.0, 0.0), (0.0, 7.5, 0.0)


class FakeSatrec:
    @staticmethod
    def twoline2rv(line1, line2, gravity):
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            raise ValueError("invalid TLE")
        return FakeSatellite()


class OrbitalSourceTests(unittest.TestCase):
    def test_teme_conversion_returns_valid_wgs84_coordinates(self):
        lon, lat, altitude = orbital_sources._teme_to_wgs84((7000.0, 0.0, 0.0), 0.0)
        self.assertAlmostEqual(lon, 0.0, places=5)
        self.assertAlmostEqual(lat, 0.0, places=5)
        self.assertGreater(altitude, 500)
        self.assertLess(altitude, 700)

    def test_orbital_feed_marks_position_as_derived(self):
        payload = "ISS (ZARYA)\n" + TLE1 + "\n" + TLE2 + "\n"
        with patch.object(orbital_sources, "Satrec", FakeSatrec), patch.object(orbital_sources, "gstime", return_value=0.0):
            result = orbital_sources.orbital_objects(
                fetch_text=lambda url: payload,
                now=datetime(2026, 10, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(result["count"], 1)
        feature = result["features"][0]
        self.assertEqual(feature["id"], "tle:25544")
        self.assertEqual(feature["properties"]["entity_type"], "satellite")
        self.assertEqual(feature["properties"]["kind"], "derived")
        self.assertTrue(feature["properties"]["position_is_predicted"])
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(len(feature["geometry"]["coordinates"]), 3)

    def test_orbital_adapter_rejects_naive_time(self):
        with self.assertRaises(ValueError):
            orbital_sources.orbital_objects(fetch_text=lambda _: "", now=datetime(2026, 10, 12))


if __name__ == "__main__":
    unittest.main()
