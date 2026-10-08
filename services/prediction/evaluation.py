"""Horizon-aware prediction evaluation and calibration."""
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable

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

def evaluate(
    forecasts: Iterable[tuple[float,int,float]],
    *,
    horizon_seconds: float,
    bins: int = 10,
) -> EvaluationReport:
    """Evaluate only outcomes belonging to one forecast horizon."""
    import math
    rows=[x for x in forecasts if x[2] == horizon_seconds]
    if not rows: raise ValueError("no forecasts for requested horizon")
    if bins < 2 or bins > 100: raise ValueError("bins must be 2..100")
    brier=0.0; logloss=0.0; grouped=defaultdict(list); eps=1e-15
    for probability,outcome,_ in rows:
        if not 0 <= probability <= 1 or outcome not in (0,1):
            raise ValueError("invalid forecast outcome")
        brier+=(probability-outcome)**2
        p=min(max(probability,eps),1-eps)
        logloss-=outcome*math.log(p)+(1-outcome)*math.log(1-p)
        index=min(int(probability*bins),bins-1)
        grouped[index].append((probability,outcome))
    calibration=[]
    for index in sorted(grouped):
        group=grouped[index]; lower=index/bins; upper=(index+1)/bins
        calibration.append(CalibrationBin(lower,upper,len(group),
            sum(p for p,_ in group)/len(group),
            sum(y for _,y in group)/len(group)))
    n=len(rows)
    return EvaluationReport(horizon_seconds,n,brier/n,logloss/n,tuple(calibration))
