"""Deterministic model-promotion policy for evaluated forecasts."""
from __future__ import annotations

from dataclasses import dataclass

from services.prediction.evaluation import EvaluationReport


@dataclass(frozen=True)
class PromotionThresholds:
    """Explicit release thresholds for one forecast horizon."""

    max_brier: float
    max_log_loss: float
    max_expected_calibration_error: float
    min_samples: int

    def __post_init__(self) -> None:
        if self.max_brier < 0 or self.max_log_loss < 0:
            raise ValueError("loss thresholds must be non-negative")
        if self.max_expected_calibration_error < 0:
            raise ValueError("calibration threshold must be non-negative")
        if self.min_samples < 1:
            raise ValueError("min_samples must be >= 1")


@dataclass(frozen=True)
class PromotionDecision:
    approved: bool
    reasons: tuple[str, ...]


def expected_calibration_error(report: EvaluationReport) -> float:
    """Compute ECE from the report's deterministic calibration bins."""
    if report.count < 1:
        raise ValueError("report must contain at least one forecast")
    return sum(
        (item.count / report.count) * abs(item.mean_probability - item.empirical_rate)
        for item in report.calibration
    )


def evaluate_promotion(
    report: EvaluationReport,
    thresholds: PromotionThresholds,
) -> PromotionDecision:
    """Approve only when sample size, scoring, and calibration all pass."""
    ece = expected_calibration_error(report)
    reasons: list[str] = []

    if report.count < thresholds.min_samples:
        reasons.append(
            f"sample_count {report.count} < minimum {thresholds.min_samples}"
        )
    if report.brier > thresholds.max_brier:
        reasons.append(
            f"brier {report.brier:.8f} > maximum {thresholds.max_brier:.8f}"
        )
    if report.log_loss > thresholds.max_log_loss:
        reasons.append(
            f"log_loss {report.log_loss:.8f} > maximum {thresholds.max_log_loss:.8f}"
        )
    if ece > thresholds.max_expected_calibration_error:
        reasons.append(
            "expected_calibration_error "
            f"{ece:.8f} > maximum {thresholds.max_expected_calibration_error:.8f}"
        )

    return PromotionDecision(approved=not reasons, reasons=tuple(reasons))
