import asyncio
import logging
from contextlib import asynccontextmanager
from enum import IntEnum
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar

from prometheus_client import Counter, Gauge
from datetime import UTC, datetime, timedelta

from pybreaker import (
    STATE_OPEN,
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerListener,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(IntEnum):
    CLOSED = 0
    HALF_OPEN = 1
    OPEN = 2


class BulkheadFull(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Bulkhead limit reached for {name}")


CIRCUIT_BREAKER_STATE = Gauge(
    "resilience_circuit_breaker_state",
    "Circuit state (0=closed, 1=half_open, 2=open)",
    ["name"],
)
CIRCUIT_BREAKER_CALLS = Counter(
    "resilience_circuit_breaker_calls_total",
    "Calls through circuit breaker",
    ["name", "result"],
)
FALLBACK_INVOCATIONS = Counter(
    "resilience_fallback_invocations_total",
    "Fallback invocations",
    ["name"],
)
BULKHEAD_REJECTIONS = Counter(
    "resilience_bulkhead_rejections_total",
    "Bulkhead rejections",
    ["name"],
)

_STATE_MAP = {
    "closed": CircuitState.CLOSED.value,
    "open": CircuitState.OPEN.value,
    "half-open": CircuitState.HALF_OPEN.value,
}


class ResilienceClient:
    def __init__(
        self,
        name: str,
        fail_max: int = 5,
        reset_timeout: int = 30,
        max_attempts: int = 3,
        timeout_seconds: float = 10.0,
        bulkhead_limit: Optional[int] = None,
    ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

        self.circuit_breaker = CircuitBreaker(
            name=name,
            fail_max=fail_max,
            reset_timeout=reset_timeout,
            listeners=[_StateListener(self)],
        )
        self.bulkhead = asyncio.Semaphore(bulkhead_limit) if bulkhead_limit else None

        CIRCUIT_BREAKER_STATE.labels(name=name).set(CircuitState.CLOSED.value)

    def protect(self, fallback: Optional[Callable[..., Awaitable[Any]]] = None):
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                return await self._execute_with_retry(func, fallback, *args, **kwargs)

            return wrapper

        return decorator

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        fallback: Optional[Callable[..., Awaitable[Any]]] = None,
        **kwargs: Any,
    ) -> T:
        return await self._execute_with_retry(func, fallback, *args, **kwargs)

    async def _execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        fallback: Optional[Callable[..., Awaitable[Any]]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        @retry(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=0.1, max=2, jitter=0.5),
            retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
            reraise=True,
        )
        async def _attempt() -> T:
            return await self._execute(func, fallback, *args, **kwargs)

        return await _attempt()

    async def _async_breaker_call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Run an async function through pybreaker's state machine without Tornado."""
        cb = self.circuit_breaker

        with cb._lock:
            if cb.current_state == STATE_OPEN:
                timeout = timedelta(seconds=cb.reset_timeout)
                opened_at = cb._state_storage.opened_at
                if opened_at and datetime.now(UTC) < opened_at + timeout:
                    raise CircuitBreakerError(
                        "Timeout not elapsed yet, circuit breaker still open"
                    )
                cb.half_open()

            for listener in cb.listeners:
                listener.before_call(cb, func, *args, **kwargs)

        try:
            result = await func(*args, **kwargs)
        except BaseException as exc:
            with cb._lock:
                cb.state._handle_error(exc)
            raise
        else:
            with cb._lock:
                cb.state._handle_success()
            return result

    async def _execute(
        self,
        func: Callable[..., Awaitable[T]],
        fallback: Optional[Callable[..., Awaitable[Any]]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        async with self._bulkhead_slot():
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    result = await self._async_breaker_call(func, *args, **kwargs)
                    CIRCUIT_BREAKER_CALLS.labels(name=self.name, result="success").inc()
                    return result
            except CircuitBreakerError:
                CIRCUIT_BREAKER_CALLS.labels(name=self.name, result="rejected").inc()
                if fallback:
                    FALLBACK_INVOCATIONS.labels(name=self.name).inc()
                    return await fallback(*args, **kwargs)
                raise
            except Exception:
                CIRCUIT_BREAKER_CALLS.labels(name=self.name, result="failure").inc()
                if fallback:
                    FALLBACK_INVOCATIONS.labels(name=self.name).inc()
                    return await fallback(*args, **kwargs)
                raise

    @asynccontextmanager
    async def _bulkhead_slot(self):
        sem = self.bulkhead
        acquired = False
        if sem is not None:
            if sem.locked():
                BULKHEAD_REJECTIONS.labels(name=self.name).inc()
                raise BulkheadFull(self.name)
            await sem.acquire()
            acquired = True
        try:
            yield
        finally:
            if acquired and sem is not None:
                sem.release()


class _StateListener(CircuitBreakerListener):
    def __init__(self, parent: ResilienceClient):
        self.parent = parent

    def state_change(self, cb, old_state, new_state):
        CIRCUIT_BREAKER_STATE.labels(name=self.parent.name).set(
            _STATE_MAP.get(str(new_state), -1)
        )
        logger.warning(
            "Circuit '%s' changed: %s → %s",
            self.parent.name,
            old_state,
            new_state,
        )