from services.prediction.evaluation import evaluate
from services.prediction.promotion import (
    PromotionThresholds,
    evaluate_promotion,
    expected_calibration_error,
)


def test_promotion_requires_sample_size_and_quality():
    report = evaluate(
        ((0.8, 1, 3600), (0.2, 0, 3600), (0.9, 1, 3600)),
        horizon_seconds=3600,
    )
    decision = evaluate_promotion(
        report,
        PromotionThresholds(
            max_brier=0.10,
            max_log_loss=0.30,
            max_expected_calibration_error=0.20,
            min_samples=10,
        ),
    )
    assert not decision.approved
    assert any("sample_count" in reason for reason in decision.reasons)


def test_promotion_passes_when_all_thresholds_pass():
    report = evaluate(
        ((0.8, 1, 3600), (0.2, 0, 3600), (0.9, 1, 3600), (0.1, 0, 3600)),
        horizon_seconds=3600,
    )
    ece = expected_calibration_error(report)
    decision = evaluate_promotion(
        report,
        PromotionThresholds(
            max_brier=0.05,
            max_log_loss=0.23,
            max_expected_calibration_error=ece,
            min_samples=4,
        ),
    )
    assert decision.approved
    assert decision.reasons == ()
