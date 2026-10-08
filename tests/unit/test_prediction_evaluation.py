from datetime import datetime, timezone, timedelta

import pytest

from packages.contracts.world_state import EntityState
from services.prediction.baseline import PersistenceBaseline
from services.prediction.evaluation import (
    calibration_report,
    evaluate,
    resolve_binary_outcome,
)

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_evaluation_is_horizon_specific_and_calibrated():
    report = evaluate(((0.8, 1, 3600), (0.2, 0, 3600), (0.9, 0, 7200)), horizon_seconds=3600)
    assert report.count == 2
    assert round(report.brier, 10) == 0.04
    assert len(report.calibration) == 2


def test_empty_horizon_is_rejected():
    with pytest.raises(ValueError, match="no forecasts"):
        evaluate(((0.8, 1, 3600),), horizon_seconds=7200)


def test_forecast_outcome_links_to_matching_authoritative_state():
    state = EntityState("s1", "e1", "facility", T, None, T, T, {"status": "closed"}, None, 0.9, ("e1",))
    forecast = PersistenceBaseline().forecast(
        (state,),
        property_name="status",
        target_value="closed",
        horizon=timedelta(hours=1),
        generated_at=T,
    )
    assert resolve_binary_outcome(forecast, state, property_name="status") == 1
    other = EntityState("s2", "e2", "facility", T, None, T, T, {"status": "closed"}, None, 0.9, ("e2",))
    with pytest.raises(ValueError, match="does not match"):
        resolve_binary_outcome(forecast, other, property_name="status")


def test_calibration_report_is_deterministic():
    report = calibration_report(((0.1, 0), (0.2, 0), (0.9, 1), (0.8, 1)), bins=2)
    assert report.score.count == 4
    assert len(report.bins) == 2
    assert report.bins[0].empirical_rate == 0
    assert report.bins[1].empirical_rate == 1
