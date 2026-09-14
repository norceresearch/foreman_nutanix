"""Tests for server.Context.

These pin *current* behaviour, including the bare ``KeyError`` raised for a
missing required variable. That is a defect (no actionable message), but it is
deliberately out of scope to fix here; the test exists so a future fix is a
visible, intentional change.
"""

from __future__ import annotations

import pytest
from nutanix_shim_server.server import Context

REQUIRED = {"NUTANIX_HOST": "pc.example.test", "NUTANIX_API_KEY": "secret-key"}


@pytest.fixture
def required_env(monkeypatch, clear_nutanix_env):
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_from_env_with_only_required_vars_uses_defaults(required_env):
    ctx = Context.from_env()

    assert ctx.nutanix_host == "pc.example.test"
    assert ctx.nutanix_api_key == "secret-key"
    assert ctx.nutanix_host_scheme == "https"
    assert ctx.nutanix_host_verify_ssl is True
    assert ctx.nutanix_host_port == 9440
    assert ctx.nutanix_client_certificate_file is None
    assert ctx.nutanix_root_ca_certificate_file is None
    assert ctx.nutanix_connect_timeout_secs == 30
    assert ctx.nutanix_read_timeout_secs == 30


def test_from_env_reads_every_optional_override(required_env, monkeypatch):
    monkeypatch.setenv("NUTANIX_HOST_SCHEME", "http")
    monkeypatch.setenv("NUTANIX_HOST_VERIFY_SSL", "False")
    monkeypatch.setenv("NUTANIX_HOST_PORT", "8443")
    monkeypatch.setenv("NUTANIX_CLIENT_CERTIFICATE_FILE", "/certs/client.pem")
    monkeypatch.setenv("NUTANIX_ROOT_CA_CERTIFICATE_FILE", "/certs/ca.pem")
    monkeypatch.setenv("NUTANIX_CONNECT_TIMEOUT_SECS", "5")
    monkeypatch.setenv("NUTANIX_READ_TIMEOUT_SECS", "7")

    ctx = Context.from_env()

    assert ctx.nutanix_host_scheme == "http"
    assert ctx.nutanix_host_verify_ssl is False
    assert ctx.nutanix_host_port == 8443
    assert ctx.nutanix_client_certificate_file == "/certs/client.pem"
    assert ctx.nutanix_root_ca_certificate_file == "/certs/ca.pem"
    assert ctx.nutanix_connect_timeout_secs == 5
    assert ctx.nutanix_read_timeout_secs == 7


@pytest.mark.parametrize("missing", sorted(REQUIRED))
def test_from_env_raises_bare_keyerror_for_missing_required_var(
    missing, required_env, monkeypatch
):
    """Current behaviour: an unhelpful bare KeyError naming only the variable."""
    monkeypatch.delenv(missing)

    with pytest.raises(KeyError) as excinfo:
        Context.from_env()

    assert excinfo.value.args == (missing,)


def test_verify_ssl_is_parsed_with_literal_eval_so_only_python_literals_work(
    required_env, monkeypatch
):
    """``ast.literal_eval`` means "True"/"False" work but "true"/"yes" explode."""
    monkeypatch.setenv("NUTANIX_HOST_VERIFY_SSL", "true")

    with pytest.raises(ValueError):
        Context.from_env()


def test_context_is_frozen(ctx):
    with pytest.raises(Exception):
        ctx.nutanix_host = "other.example.test"  # type: ignore[misc]


def test_state_str_lists_every_field(clear_nutanix_env, monkeypatch):
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)

    state = Context.state_str()
    lines = [line for line in state.splitlines() if line]

    assert [line.split("=", 1)[0] for line in lines] == [
        name.upper() for name in Context._vars
    ]


def test_state_str_renders_unset_optionals_as_empty_string(
    clear_nutanix_env, monkeypatch
):
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)

    state = Context.state_str()

    assert "\nNUTANIX_CLIENT_CERTIFICATE_FILE=\n" in state + "\n"
    assert "\nNUTANIX_ROOT_CA_CERTIFICATE_FILE=\n" in state + "\n"


def test_state_str_tolerates_completely_unset_required_vars(clear_nutanix_env):
    """Unlike from_env, state_str uses os.getenv and so never raises."""
    state = Context.state_str()

    assert "\nNUTANIX_HOST=\n" in state + "\n"
    assert "\nNUTANIX_API_KEY=\n" in state + "\n"
