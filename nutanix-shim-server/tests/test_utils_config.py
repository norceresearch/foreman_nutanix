"""Tests for utils.configure_sdk and utils.add_default_headers.

Both functions mutate an object handed to them, so the assertions are on the
resulting config/client state.
"""

from __future__ import annotations

import ntnx_clustermgmt_py_client as cm
import ntnx_networking_py_client as net
import ntnx_vmm_py_client as vmm
import pytest
from nutanix_shim_server.utils import add_default_headers, configure_sdk

from .conftest import FakeApiClient, FakeConfig


def test_configure_sdk_copies_context_onto_config(ctx):
    config = FakeConfig()

    configure_sdk(config, ctx)

    assert config.host == "pc.example.test"
    assert config.scheme == "https"
    assert config.api_key == "secret-key"
    assert config.verify_ssl is False
    assert config.port == 9440
    assert config.client_certificate_file == "/tmp/client.pem"
    assert config.root_ca_certificate_file == "/tmp/ca.pem"


def test_configure_sdk_hardcodes_retry_policy(ctx):
    config = FakeConfig()

    configure_sdk(config, ctx)

    assert config.max_retry_attempts == 3
    assert config.backoff_factor == 3


def test_configure_sdk_converts_timeouts_from_seconds_to_milliseconds(ctx):
    config = FakeConfig()

    configure_sdk(config, ctx)

    assert config.connect_timeout == 11_000
    assert config.read_timeout == 13_000


@pytest.mark.parametrize(
    "configuration",
    [vmm.Configuration, net.Configuration, cm.Configuration],
    ids=["vmm", "networking", "clustermgmt"],
)
def test_configure_sdk_works_against_real_sdk_configurations(configuration, ctx):
    """The docstring claims one shape fits every SDK package - verify it."""
    config = configuration()

    configure_sdk(config, ctx)

    assert config.host == "pc.example.test"
    assert config.port == 9440
    assert config.read_timeout == 13_000


def test_add_default_headers_sets_accept_encoding():
    client = FakeApiClient()

    add_default_headers(client)

    assert client.headers == {"Accept-Encoding": "gzip, deflate, br"}
