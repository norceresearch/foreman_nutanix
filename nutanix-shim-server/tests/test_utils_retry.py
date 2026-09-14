"""Tests for utils.retry_on_timeout.

The decorator retries exactly once, and finds the cache-clearing hook by
``hasattr(self, "_clear_clients")`` rather than by any declared interface -
so an object without that method must still work.
"""

from __future__ import annotations

import pytest
from nutanix_shim_server.utils import retry_on_timeout
from urllib3.exceptions import MaxRetryError, ReadTimeoutError


def _read_timeout() -> ReadTimeoutError:
    return ReadTimeoutError(None, "/api/v4/vms", "read timed out")


def _max_retry() -> MaxRetryError:
    return MaxRetryError(None, "/api/v4/vms", "too many retries")


class Service:
    """Object exposing the ``_clear_clients`` hook the decorator looks for."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0
        self.cleared = 0

    def _clear_clients(self) -> None:
        self.cleared += 1

    @retry_on_timeout
    def work(self, *args, **kwargs):
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class ServiceWithoutClear:
    """No ``_clear_clients`` - the hasattr probe must simply skip it."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0

    @retry_on_timeout
    def work(self):
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_success_on_first_try_does_not_clear_clients():
    svc = Service(["ok"])

    assert svc.work() == "ok"
    assert svc.calls == 1
    assert svc.cleared == 0


def test_args_and_kwargs_are_forwarded():
    class Echo:
        @retry_on_timeout
        def work(self, a, b, c=None):
            return (a, b, c)

    assert Echo().work(1, 2, c=3) == (1, 2, 3)


@pytest.mark.parametrize(
    "exc_factory", [_read_timeout, _max_retry], ids=["read", "max"]
)
def test_retries_once_after_timeout_and_clears_clients(exc_factory):
    svc = Service([exc_factory(), "ok"])

    assert svc.work() == "ok"
    assert svc.calls == 2
    assert svc.cleared == 1


@pytest.mark.parametrize(
    "exc_factory", [_read_timeout, _max_retry], ids=["read", "max"]
)
def test_failure_on_both_attempts_propagates(exc_factory):
    first, second = exc_factory(), exc_factory()
    svc = Service([first, second])

    with pytest.raises(type(second)) as excinfo:
        svc.work()

    # The second failure escapes, not the first: there is no third attempt.
    assert excinfo.value is second
    assert svc.calls == 2
    assert svc.cleared == 1


def test_object_without_clear_clients_still_retries():
    svc = ServiceWithoutClear([_read_timeout(), "ok"])

    assert svc.work() == "ok"
    assert svc.calls == 2


def test_non_timeout_exception_is_not_retried():
    svc = Service([ValueError("boom"), "ok"])

    with pytest.raises(ValueError, match="boom"):
        svc.work()
    assert svc.calls == 1
    assert svc.cleared == 0


def test_wraps_preserves_function_metadata():
    class Documented:
        @retry_on_timeout
        def list_things(self):
            """Docstring kept by functools.wraps."""

    assert Documented.list_things.__name__ == "list_things"
    assert Documented.list_things.__doc__ == "Docstring kept by functools.wraps."
