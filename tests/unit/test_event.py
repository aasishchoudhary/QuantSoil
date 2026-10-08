from datetime import datetime, timezone
import pytest
from packages.contracts.event import Event
def make(kind, derivation=None):
    return Event("evt-1", kind, datetime.now(timezone.utc), datetime.now(timezone.utc), {"x":1}, ("ev-1",), derivation)
def test_observed_event_has_no_derivation():
    assert make("observed").kind == "observed"
@pytest.mark.parametrize("kind", ["derived", "predicted"])
def test_non_observed_requires_derivation(kind):
    with pytest.raises(ValueError, match="derivation"): make(kind)
def test_observed_rejects_derivation():
    with pytest.raises(ValueError, match="observed"): make("observed", "rule-v1")
