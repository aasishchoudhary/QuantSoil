"""Production inference boundary for God's Eye.

LLM output is untrusted data. This package deliberately exposes a small,
provider-neutral contract so the rest of the platform does not depend on a
specific model vendor.
"""

from .client import InferenceClient, InferenceConfig, InferenceError, InferenceResult
from .policy import InferenceTask, select_model

__all__ = [
    "InferenceClient",
    "InferenceConfig",
    "InferenceError",
    "InferenceResult",
    "InferenceTask",
    "select_model",
]
