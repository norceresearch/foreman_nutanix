"""Tests for the GPU fields on ``VmProvisionRequest``.

The GPU fields are all optional so that an older plugin keeps working
unchanged, which means the dataclass itself has to reject the combinations the
Nutanix API would only reject much later (or, worse, accept and mis-schedule).
Validation runs in ``__post_init__`` and raises ``ValueError`` naming the field
at fault.

Scope is passthrough only - ``VIRTUAL`` is rejected on purpose; see
``_PASSTHROUGH_GPU_MODES`` in vmm.py.
"""

from __future__ import annotations

import ntnx_vmm_py_client as vmm
import pytest
from nutanix_shim_server.vmm import VmProvisionRequest

CLUSTER_EXT_ID = "00061663-9fa0-28ca-185b-ac1f6b6f97e2"
SUBNET_EXT_ID = "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a"
CONTAINER_EXT_ID = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"


def make_request(**overrides) -> VmProvisionRequest:
    kwargs = dict(
        name="my-vm-01",
        cluster_ext_id=CLUSTER_EXT_ID,
        subnet_ext_id=SUBNET_EXT_ID,
        storage_container_ext_id=CONTAINER_EXT_ID,
        num_sockets=2,
        num_cores_per_socket=2,
        memory_size_bytes=8 * 2**30,
        disk_size_bytes=100 * 2**30,
    )
    kwargs.update(overrides)
    return VmProvisionRequest(**kwargs)


# --------------------------------------------------------------------------
# Defaults: a request with no GPU fields at all
# --------------------------------------------------------------------------


def test_gpu_fields_default_to_no_gpu():
    request = make_request()

    assert request.gpu_device_id is None
    assert request.gpu_vendor is None
    assert request.gpu_mode is None
    assert request.gpu_count == 0


# --------------------------------------------------------------------------
# A well-formed GPU request
# --------------------------------------------------------------------------


def test_a_complete_passthrough_gpu_request_is_accepted():
    request = make_request(
        gpu_device_id=7864,
        gpu_vendor="NVIDIA",
        gpu_mode="PASSTHROUGH_GRAPHICS",
        gpu_count=2,
    )

    assert request.gpu_device_id == 7864
    assert request.gpu_vendor == "NVIDIA"
    assert request.gpu_mode == "PASSTHROUGH_GRAPHICS"
    assert request.gpu_count == 2


@pytest.mark.parametrize("vendor", ["nvidia", "Nvidia", "NVIDIA", "nViDiA"])
def test_gpu_vendor_is_matched_case_insensitively(vendor):
    request = make_request(
        gpu_device_id=7864,
        gpu_vendor=vendor,
        gpu_mode="PASSTHROUGH_COMPUTE",
        gpu_count=1,
    )

    assert request.gpu_vendor == vmm.GpuVendor.NVIDIA


@pytest.mark.parametrize(
    "mode", ["PASSTHROUGH_COMPUTE", "PASSTHROUGH_GRAPHICS", "passthrough_graphics"]
)
def test_every_passthrough_mode_is_accepted(mode):
    request = make_request(
        gpu_device_id=7864, gpu_vendor="AMD", gpu_mode=mode, gpu_count=1
    )

    assert request.gpu_mode == mode.upper()


# --------------------------------------------------------------------------
# Rejections
# --------------------------------------------------------------------------


def test_negative_gpu_count_is_rejected():
    with pytest.raises(ValueError, match="gpu_count"):
        make_request(gpu_count=-1)


@pytest.mark.parametrize(
    "missing", ["gpu_device_id", "gpu_vendor", "gpu_mode"]
)
def test_requesting_gpus_without_the_full_triple_is_rejected(missing):
    kwargs = dict(
        gpu_device_id=7864,
        gpu_vendor="NVIDIA",
        gpu_mode="PASSTHROUGH_GRAPHICS",
        gpu_count=1,
    )
    kwargs[missing] = None

    with pytest.raises(ValueError, match=missing):
        make_request(**kwargs)


def test_an_unknown_vendor_is_rejected():
    with pytest.raises(ValueError, match="gpu_vendor"):
        make_request(
            gpu_device_id=7864,
            gpu_vendor="MATROX",
            gpu_mode="PASSTHROUGH_GRAPHICS",
            gpu_count=1,
        )


def test_an_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="gpu_mode"):
        make_request(
            gpu_device_id=7864,
            gpu_vendor="NVIDIA",
            gpu_mode="PASSTHROUGH",
            gpu_count=1,
        )


def test_virtual_mode_is_rejected_because_vgpu_is_out_of_scope():
    with pytest.raises(ValueError, match="gpu_mode"):
        make_request(
            gpu_device_id=7864,
            gpu_vendor="NVIDIA",
            gpu_mode=vmm.GpuMode.VIRTUAL,
            gpu_count=1,
        )


def test_the_allocation_state_mode_of_a_profile_is_not_accepted_as_a_gpu_mode():
    """``PhysicalGpuConfig.mode`` values (USED_FOR_PASSTHROUGH and friends) are
    allocation state, not attach modes. If one ever reaches the shim it means
    the caller read the wrong field, so fail loudly instead of guessing."""
    with pytest.raises(ValueError, match="gpu_mode"):
        make_request(
            gpu_device_id=7864,
            gpu_vendor="NVIDIA",
            gpu_mode="USED_FOR_PASSTHROUGH",
            gpu_count=1,
        )


# --------------------------------------------------------------------------
# gpu_count == 0 short-circuits the whole thing
# --------------------------------------------------------------------------


def test_zero_gpu_count_ignores_every_other_gpu_field():
    """Nothing is attached, so nothing about the other fields matters - even
    values that would be rejected outright were any GPU actually requested."""
    request = make_request(
        gpu_device_id=None,
        gpu_vendor="MATROX",
        gpu_mode="USED_FOR_VIRTUAL",
        gpu_count=0,
    )

    assert request.gpu_count == 0


@pytest.mark.parametrize("device_id", [0, -1])
def test_non_positive_device_id_is_rejected(device_id):
    # A malformed compute-profile composite (e.g. "abc:NVIDIA:PASSTHROUGH_GRAPHICS")
    # coerces to 0 on the Ruby side. Reject locally with a clear message rather
    # than forwarding a nonsense device id to Nutanix.
    with pytest.raises(ValueError, match="gpu_device_id"):
        make_request(
            gpu_device_id=device_id,
            gpu_vendor="NVIDIA",
            gpu_mode="PASSTHROUGH_GRAPHICS",
            gpu_count=1,
        )
