"""Deterministic persistence baseline for probabilistic state forecasts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from packages.contracts.event import Event
from packages.contracts.world_state import EntityState

@dataclass(frozen=True)
class BinaryForecast:
    prediction: Event
    probability: float
    target: str
    horizon: timedelta
    model_version: str

class PersistenceBaseline:
    """Empirical next-state probability with Laplace smoothing.

    This is a benchmark, not an assertion of causal prediction. It uses only
    historical transitions and preserves the latest state's evidence refs.
    """

    def __init__(self, *, model_version="persistence-v1"): self.model_version=model_version

    def forecast(self, history: tuple[EntityState,...], *, property_name: str,
                 target_value, horizon: timedelta, generated_at: datetime) -> BinaryForecast:
        if not history: raise ValueError("history is required")
        if generated_at.tzinfo is None or horizon <= timedelta(0): raise ValueError("invalid forecast time")
        ordered=sorted(history,key=lambda s:(s.valid_from,s.recorded_at,s.state_id))
        transitions=[s for s in ordered[1:] if property_name in s.properties]
        successes=sum(1 for s in transitions if s.properties.get(property_name)==target_value)
        probability=(successes+1)/(len(transitions)+2)
        latest=ordered[-1]
        refs=latest.evidence_refs
        event_id=sha256(f"{self.model_version}|{latest.state_id}|{property_name}|{target_value}|{generated_at.isoformat()}".encode()).hexdigest()
        event=Event(
            event_id=event_id,event_type="prediction",state="predicted",
            occurred_at=generated_at+horizon,evidence_refs=refs,
            payload={
                "model_version":self.model_version,"entity_id":latest.entity_id,
                "property":property_name,"target":target_value,
                "probability":probability,"horizon_seconds":horizon.total_seconds(),
                "training_transitions":len(transitions),"generated_at":generated_at.isoformat(),
            })
        return BinaryForecast(event,probability,str(target_value),horizon,self.model_version)

@dataclass(frozen=True)
class ForecastScore:
    count: int
    brier: float
    log_loss: float

def score_binary_forecasts(items: tuple[tuple[float,int],...])->ForecastScore:
    import math
    if not items: raise ValueError("forecast observations are required")
    brier=0.0; logloss=0.0
    eps=1e-15
    for probability,outcome in items:
        if not 0<=probability<=1 or outcome not in (0,1): raise ValueError("invalid forecast pair")
        brier+=(probability-outcome)**2
        p=min(max(probability,eps),1-eps)
        logloss-=outcome*math.log(p)+(1-outcome)*math.log(1-p)
    n=len(items)
    return ForecastScore(n,brier/n,logloss/n)
