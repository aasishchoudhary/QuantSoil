"""Outcome linkage and calibration evaluation for evidence-backed forecasts."""
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from packages.contracts.world_state import EntityState
from services.prediction.baseline import BinaryForecast, ForecastScore, score_binary_forecasts

@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_probability: float
    observed_frequency: float

@dataclass(frozen=True)
class CalibrationReport:
    bins: tuple[CalibrationBin, ...]
    score: ForecastScore

def resolve_binary_outcome(forecast: BinaryForecast, state: EntityState, *, property_name: str) -> int:
    if state.entity_id != forecast.prediction.payload["entity_id"]:
        raise ValueError("state entity does not match forecast")
    return int(state.properties.get(property_name) == forecast.prediction.payload["target"])

def calibration_report(items: tuple[tuple[float,int],...], *, bins: int = 10) -> CalibrationReport:
    if bins < 1 or bins > 100: raise ValueError("bins must be between 1 and 100")
    groups=defaultdict(list)
    for p,o in items:
        if not 0<=p<=1 or o not in (0,1): raise ValueError("invalid forecast pair")
        idx=min(int(p*bins),bins-1)
        groups[idx].append((p,o))
    output=[]
    for idx in sorted(groups):
        values=groups[idx]
        output.append(CalibrationBin(idx/bins,(idx+1)/bins,len(values),sum(p for p,_ in values)/len(values),sum(o for _,o in values)/len(values)))
    return CalibrationReport(tuple(output),score_binary_forecasts(items))
