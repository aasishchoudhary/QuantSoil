"""Deterministic monitoring signals for forecast performance drift."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DriftSignal:
    metric: str
    baseline: float
    current: float
    delta: float
    threshold: float
    breached: bool

def compare_metric(metric:str, baseline:float, current:float, threshold:float)->DriftSignal:
    if threshold < 0: raise ValueError("threshold must be non-negative")
    delta=current-baseline
    return DriftSignal(metric,baseline,current,delta,threshold,abs(delta)>threshold)
