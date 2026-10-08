from datetime import datetime, timedelta, timezone
from services.runtime.worker import ConnectorWorker, WorkerPolicy

def test_retry_delay_is_exponential_capped_and_jittered():
    policy = WorkerPolicy(
        retry_delay=timedelta(seconds=10),
        max_retry_delay=timedelta(seconds=25),
        jitter_ratio=0.2,
    )
    worker = ConnectorWorker.__new__(ConnectorWorker)
    worker.policy = policy
    class Random:
        def uniform(self, low, high): return high
    worker._random = Random()
    assert worker._retry_delay(1) == timedelta(seconds=12)
    assert worker._retry_delay(2) == timedelta(seconds=24)
    assert worker._retry_delay(3) == timedelta(seconds=25 + 5)

def test_retry_after_is_a_minimum():
    policy = WorkerPolicy(retry_delay=timedelta(seconds=10), max_retry_delay=timedelta(seconds=20), jitter_ratio=0)
    worker = ConnectorWorker.__new__(ConnectorWorker)
    worker.policy = policy
    class Random:
        def uniform(self, low, high): return 0
    worker._random = Random()
    assert worker._retry_delay(1, 30) == timedelta(seconds=30)
