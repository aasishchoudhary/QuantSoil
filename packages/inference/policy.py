"""Deterministic task-to-model policy.

This is intentionally conservative. Policy chooses a model; it does not let
an LLM choose its own authority, permissions, or data-access scope.
"""

from __future__ import annotations

from enum import StrEnum


class InferenceTask(StrEnum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"
    INVESTIGATION = "investigation"
    SYNTHESIS = "synthesis"


_DEFAULT_MODEL = "gemini-3.6-flash"
_TASK_MODELS = {
    InferenceTask.CLASSIFICATION: "gemini-3.6-flash-lite",
    InferenceTask.EXTRACTION: "gemini-3.6-flash-lite",
    InferenceTask.SUMMARIZATION: "gemini-3.6-flash",
    InferenceTask.ANALYSIS: "gemini-3.6-flash",
    InferenceTask.INVESTIGATION: "gemini-3.6-flash",
    InferenceTask.SYNTHESIS: "gemini-3.7-flash",
}


def select_model(task: InferenceTask, *, override: str | None = None) -> str:
    """Select a deterministic default; explicit override remains caller-owned."""
    if override is not None:
        value = override.strip()
        if not value:
            raise ValueError("model override must not be empty")
        return value
    return _TASK_MODELS.get(task, _DEFAULT_MODEL)
