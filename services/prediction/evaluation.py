"""Horizon-aware prediction scoring, calibration, and outcome linkage."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from packages.contracts.world_state import EntityState
from services.prediction.baseline import (
    BinaryForecast,
    ForecastScore,
    score_binary_forecasts,
)


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_probability: float
    empirical_rate: float


@dataclass(frozen=True)
class EvaluationReport:
    horizon_seconds: float
    count: int
    brier: float
    log_loss: float
    calibration: tuple[CalibrationBin, ...]


@dataclass(frozen=True)
class CalibrationReport:
    bins: tuple[CalibrationBin, ...]
    score: ForecastScore


def resolve_binary_outcome(
    forecast: BinaryForecast,
    state: EntityState,
    *,
    property_name: str,
) -> int:
    """Resolve a binary outcome only against the matching entity state."""
    entity_id = forecast.prediction.payload["entity_id"]
    if state.entity_id != entity_id:
        raise ValueError("state entity does not match forecast")
    return int(state.properties.get(property_name) == forecast.prediction.payload["target"])


def calibration_report(
    items: tuple[tuple[float, int], ...],
    *,
    bins: int = 10,
) -> CalibrationReport:
    """Return calibration bins and proper scores for probability/outcome pairs."""
    if bins < 2 or bins > 100:
        raise ValueError("bins must be between 2 and 100")
    if not items:
        raise ValueError("forecast observations are required")
    groups: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for probability, outcome in items:
        if not 0 <= probability <= 1 or outcome not in (0, 1):
            raise ValueError("invalid forecast pair")
        index = min(int(probability * bins), bins - 1)
        groups[index].append((probability, outcome))
    output = []
    for index in sorted(groups):
        values = groups[index]
        output.append(
            CalibrationBin(
                index / bins,
                (index + 1) / bins,
                len(values),
                sum(p for p, _ in values) / len(values),
                sum(y for _, y in values) / len(values),
            )
        )
    return CalibrationReport(tuple(output), score_binary_forecasts(items))


def evaluate(
    forecasts: Iterable[tuple[float, int, float]],
    *,
    horizon_seconds: float,
    bins: int = 10,
) -> EvaluationReport:
    """Evaluate only outcomes belonging to one forecast horizon."""
    import math

    rows = [row for row in forecasts if row[2] == horizon_seconds]
    if not rows:
        raise ValueError("no forecasts for requested horizon")
    if bins < 2 or bins > 100:
        raise ValueError("bins must be 2..100")

    brier = 0.0
    logloss = 0.0
    grouped: dict[int, list[tuple[float, int]]] = defaultdict(list)
    epsilon = 1e-15
    for probability, outcome, _ in rows:
        if not 0 <= probability <= 1 or outcome not in (0, 1):
            raise ValueError("invalid forecast outcome")
        brier += (probability - outcome) ** 2
        bounded = min(max(probability, epsilon), 1 - epsilon)
        logloss -= outcome * math.log(bounded) + (1 - outcome) * math.log(1 - bounded)
        index = min(int(probability * bins), bins - 1)
        grouped[index].append((probability, outcome))

    calibration = []
    for index in sorted(grouped):
        group = grouped[index]
        calibration.append(
            CalibrationBin(
                index / bins,
                (index + 1) / bins,
                len(group),
                sum(p for p, _ in group) / len(group),
                sum(y for _, y in group) / len(group),
            )
        )
    count = len(rows)
    return EvaluationReport(
        horizon_seconds,
        count,
        brier / count,
        logloss / count,
        tuple(calibration),
    )
