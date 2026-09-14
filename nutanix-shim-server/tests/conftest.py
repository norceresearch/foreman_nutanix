"""Shared stubs for the shim server test suite.

The Nutanix SDK response/model objects the package consumes are plain
attribute bags as far as our code is concerned: every translation classmethod
walks attributes (often via ``hasattr``/``getattr``) rather than calling SDK
behaviour. The stubs below reproduce exactly the attribute chains the code
walks. Where the source uses ``isinstance`` against a concrete SDK class the
tests build the real SDK object instead - see ``tests/README.md``.
"""

from __future__ import annotations

import pytest
from nutanix_shim_server.server import Context


class Stub:
    """Attribute bag: every kwarg becomes an attribute, nothing else exists."""

    def __init__(self, **attrs):
        self.__dict__.update(attrs)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"Stub({self.__dict__!r})"


class Link(Stub):
    """Stands in for ``ApiLink`` - ``paginate`` only reads ``.rel``/``.href``."""

    def __init__(self, rel: str, href: str):
        super().__init__(rel=rel, href=href)


class Meta(Stub):
    """Stands in for ``ApiResponseMetadata`` - only ``.links`` is read."""

    def __init__(self, links=None):
        super().__init__(links=links)


class Resp(Stub):
    """A ``list_*`` response: ``paginate`` reads ``.data`` and ``.metadata``."""

    def __init__(self, data, metadata=None):
        super().__init__(data=data, metadata=metadata)


class FakeConfig:
    """Stands in for any ``<sdk>.Configuration`` - see utils.configure_sdk."""

    def __init__(self):
        self.api_key = None

    def set_api_key(self, key):
        self.api_key = key


class FakeApiClient:
    """Stands in for any ``<sdk>.ApiClient`` - see utils.add_default_headers."""

    def __init__(self):
        self.headers: dict[str, str] = {}

    def add_default_header(self, header_name, header_value):
        self.headers[header_name] = header_value


@pytest.fixture
def ctx() -> Context:
    """A fully populated Context, built directly rather than from env."""
    return Context(
        nutanix_host="pc.example.test",
        nutanix_host_scheme="https",
        nutanix_host_verify_ssl=False,
        nutanix_api_key="secret-key",
        nutanix_host_port=9440,
        nutanix_client_certificate_file="/tmp/client.pem",
        nutanix_root_ca_certificate_file="/tmp/ca.pem",
        nutanix_connect_timeout_secs=11,
        nutanix_read_timeout_secs=13,
    )


@pytest.fixture
def clear_nutanix_env(monkeypatch):
    """Remove every NUTANIX_* var so env-driven tests start from a clean slate."""
    import os

    for key in list(os.environ):
        if key.startswith("NUTANIX_"):
            monkeypatch.delenv(key, raising=False)
