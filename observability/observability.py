import time
from contextlib import contextmanager

from opentelemetry import trace
from prometheus_client import Counter, Histogram

tracer = trace.get_tracer(__name__)

LATENCY = Histogram("pipeline_stage_latency_seconds", "Stage latency", ["stage"])
ERRORS = Counter("pipeline_stage_errors_total", "Stage errors", ["stage"])
REQUESTS = Counter("pipeline_stage_requests_total", "Stage requests", ["stage"])


@contextmanager
def traced(name: str):
    start = time.perf_counter()
    with tracer.start_as_current_span(name) as span:
        try:
            yield span
        except Exception:
            ERRORS.labels(stage=name).inc()
            raise
        finally:
            LATENCY.labels(stage=name).observe(time.perf_counter() - start)


def record_red_metrics(stage: str):
    REQUESTS.labels(stage=stage).inc()