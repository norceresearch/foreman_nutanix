"""Tests for the GPU half of ``VirtualMachineMgmt.provision_vm``.

``provision_vm`` has no clock seam (see tests/README.md), but it does have an
API seam: ``vms_api`` / ``tasks_api`` only build a client when the cached
``_vms_api`` / ``_tasks_api`` attribute is absent, so assigning them swaps the
APIs out. A task that reports SUCCEEDED on the first poll never reaches the
``time.sleep`` in the loop, so these run instantly.

What is under test is the ``vmm.AhvConfigVm`` handed to ``create_vm``: the GPU
list is the only thing the shim can get wrong on its own.
"""

from __future__ import annotations

import ntnx_vmm_py_client as vmm
import pytest
from nutanix_shim_server.vmm import VirtualMachineMgmt, VmProvisionRequest

from .conftest import Stub

CLUSTER_EXT_ID = "00061663-9fa0-28ca-185b-ac1f6b6f97e2"
SUBNET_EXT_ID = "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a"
CONTAINER_EXT_ID = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
VM_EXT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TASK_EXT_ID = "ZXJnb24=:ffffffff-ffff-ffff-ffff-ffffffffffff"


class RecordingVmApi:
    """Stands in for ``vmm.VmApi`` - keeps the spec it was asked to create."""

    def __init__(self):
        self.created: list[vmm.AhvConfigVm] = []

    def create_vm(self, body):
        self.created.append(body)
        return Stub(data=Stub(ext_id=TASK_EXT_ID))


class SucceedingTasksApi:
    """Stands in for ``prism.TasksApi`` - the task is done on the first poll."""

    def get_task_by_id(self, extId):  # noqa: N803 - SDK keyword spelling
        return Stub(
            data=Stub(
                status="SUCCEEDED",
                entities_affected=[Stub(ext_id=VM_EXT_ID)],
            )
        )


@pytest.fixture
def mgmt(ctx) -> VirtualMachineMgmt:
    api = VirtualMachineMgmt(ctx)
    api._vms_api = RecordingVmApi()  # type: ignore[attr-defined]
    api._tasks_api = SucceedingTasksApi()  # type: ignore[attr-defined]
    return api


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


def created_spec(mgmt: VirtualMachineMgmt) -> vmm.AhvConfigVm:
    return mgmt._vms_api.created[0]  # type: ignore[attr-defined]


def test_no_gpu_requested_leaves_gpus_off_the_spec_entirely(mgmt):
    mgmt.provision_vm(make_request())

    assert created_spec(mgmt).gpus is None


def test_a_single_gpu_is_attached_with_vendor_and_mode_as_sdk_values(mgmt):
    mgmt.provision_vm(
        make_request(
            gpu_device_id=7864,
            gpu_vendor="nvidia",
            gpu_mode="PASSTHROUGH_GRAPHICS",
            gpu_count=1,
        )
    )

    gpus = created_spec(mgmt).gpus
    assert len(gpus) == 1
    assert gpus[0].device_id == 7864
    assert gpus[0].vendor == vmm.GpuVendor.NVIDIA
    assert gpus[0].mode == vmm.GpuMode.PASSTHROUGH_GRAPHICS


@pytest.mark.parametrize("count", [1, 2, 4, 8])
def test_the_spec_carries_one_gpu_entry_per_requested_gpu(mgmt, count):
    mgmt.provision_vm(
        make_request(
            gpu_device_id=7864,
            gpu_vendor="NVIDIA",
            gpu_mode="PASSTHROUGH_COMPUTE",
            gpu_count=count,
        )
    )

    assert len(created_spec(mgmt).gpus) == count


def test_each_gpu_entry_is_a_distinct_object(mgmt):
    """``[gpu] * n`` would put the *same* object in the list n times. The SDK
    serialises it n times so it can look like it works, but it is aliasing:
    build a fresh Gpu per iteration."""
    mgmt.provision_vm(
        make_request(
            gpu_device_id=7864,
            gpu_vendor="NVIDIA",
            gpu_mode="PASSTHROUGH_COMPUTE",
            gpu_count=4,
        )
    )

    gpus = created_spec(mgmt).gpus
    assert len({id(gpu) for gpu in gpus}) == 4


def test_every_gpu_entry_carries_identical_settings(mgmt):
    mgmt.provision_vm(
        make_request(
            gpu_device_id=4242,
            gpu_vendor="AMD",
            gpu_mode="PASSTHROUGH_GRAPHICS",
            gpu_count=3,
        )
    )

    gpus = created_spec(mgmt).gpus
    assert [(g.device_id, g.vendor, g.mode) for g in gpus] == [
        (4242, vmm.GpuVendor.AMD, vmm.GpuMode.PASSTHROUGH_GRAPHICS)
    ] * 3


def test_the_rest_of_the_spec_is_unchanged_by_attaching_a_gpu(mgmt):
    """Adding GPUs must not disturb anything else that was already sent."""
    mgmt.provision_vm(
        make_request(
            gpu_device_id=7864,
            gpu_vendor="NVIDIA",
            gpu_mode="PASSTHROUGH_GRAPHICS",
            gpu_count=1,
        )
    )

    spec = created_spec(mgmt)
    assert spec.name == "my-vm-01"
    assert spec.num_sockets == 2
    assert spec.num_cores_per_socket == 2
    assert spec.memory_size_bytes == 8 * 2**30
    assert len(spec.nics) == 1
    assert len(spec.disks) == 1
