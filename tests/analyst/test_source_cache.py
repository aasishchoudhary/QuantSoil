import unittest
from services.analyst.api import _SOURCE_CACHE, _SOURCE_CACHE_LOCK, _cached_public_source


class PublicSourceCacheTests(unittest.TestCase):
    def setUp(self):
        with _SOURCE_CACHE_LOCK:
            _SOURCE_CACHE.clear()

    def test_successful_response_is_cached_for_ttl(self):
        calls = []
        payload = {"type": "FeatureCollection", "features": []}

        def producer():
            calls.append(1)
            return payload

        first = _cached_public_source("test-provider", 60, producer)
        second = _cached_public_source("test-provider", 60, producer)
        self.assertIs(first, payload)
        self.assertIs(second, payload)
        self.assertEqual(len(calls), 1)

    def test_failed_fetch_is_not_cached_as_empty_success(self):
        calls = []

        def producer():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("provider unavailable")
            return {"features": [{"id": "recovered"}]}

        with self.assertRaises(RuntimeError):
            _cached_public_source("test-provider-failure", 60, producer)
        recovered = _cached_public_source("test-provider-failure", 60, producer)
        self.assertEqual(recovered["features"][0]["id"], "recovered")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
