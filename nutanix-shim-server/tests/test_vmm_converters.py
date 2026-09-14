"""Tests for the vmm.py translation classmethods.

These build *real* Nutanix SDK model objects. That turned out to be practical:
the SDK models construct with no arguments and accept attribute assignment
(subject to UUID validation on ``ext_id`` fields), and the converters use
``isinstance`` against concrete SDK classes (``VmDisk``, ``UefiBoot``,
``NicNetworkInfo``, ``SubnetReference``) which a duck-typed stub could not
satisfy. Only ``ImageMetadata.from_nutanix_image`` uses a stub, because it
consumes ``image.to_dict()`` and nothing else.
"""

from __future__ import annotations

import datetime

import ntnx_vmm_py_client as vmm
import pytest
from ntnx_vmm_py_client.models.common.v1.config.IPv4Address import IPv4Address
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.ClusterReference import (
    ClusterReference,
)
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Disk import Disk
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.EmulatedNic import EmulatedNic
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Ipv4Config import Ipv4Config
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Nic import Nic
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.NicNetworkInfo import NicNetworkInfo
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.PowerState import PowerState
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.SubnetReference import SubnetReference
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.VmDisk import (
    VmDisk,
    VmDiskContainerReference,
)
from nutanix_shim_server.vmm import (
    GpuMetadata,
    ImageMetadata,
    VmDetailsMetadata,
    VmListMetadata,
    _disk_container_ref_from_disk,
    _disk_sizes_bytes_from_disks,
)

from .conftest import Stub

# The GPU that make_vm() attaches, as it comes out the other side. Shared by the
# list and detail assertions so the two can never drift apart.
EXPECTED_GPU = GpuMetadata(
    ext_id=None,
    name="Tesla T4",
    mode="PASSTHROUGH_GRAPHICS",
    vendor="NVIDIA",
    device_id=42,
    fraction=None,
    frame_buffer_size_bytes=None,
    num_virtual_display_heads=None,
    guest_driver_version=None,
)

VM_EXT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
CLUSTER_EXT_ID = "00061663-9fa0-28ca-185b-ac1f6b6f97e2"
SUBNET_EXT_ID = "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a"
CONTAINER_EXT_ID = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
NIC_EXT_ID = "9f9f9f9f-1111-2222-3333-444444444444"
CREATE_TIME = datetime.datetime(2026, 1, 8, 12, 0, tzinfo=datetime.timezone.utc)


def make_disk(size_bytes: int | None = 107374182400, container: bool = True) -> Disk:
    backing = VmDisk()
    backing.disk_size_bytes = size_bytes
    if container:
        ref = VmDiskContainerReference()
        ref.ext_id = CONTAINER_EXT_ID
        backing.storage_container = ref
    disk = Disk()
    disk.backing_info = backing
    return disk


def make_nic(mac: str | None = "50:6b:8d:11:22:33", ip: str | None = "10.0.0.5") -> Nic:
    nic = Nic()
    nic.ext_id = NIC_EXT_ID

    if mac is not None:
        backing = EmulatedNic()
        backing.mac_address = mac
        nic.backing_info = backing

    network_info = NicNetworkInfo()
    subnet = SubnetReference()
    subnet.ext_id = SUBNET_EXT_ID
    network_info.subnet = subnet
    if ip is not None:
        ipv4_config = Ipv4Config()
        address = IPv4Address()
        address.value = ip
        ipv4_config.ip_address = address
        network_info.ipv4_config = ipv4_config
    nic.network_info = network_info
    return nic


def make_vm(**overrides) -> vmm.AhvConfigVm:
    """A fully populated VM; pass ``key=None`` to blank out a branch."""
    cluster = ClusterReference()
    cluster.ext_id = CLUSTER_EXT_ID

    boot_config = vmm.UefiBoot()
    boot_config.is_secure_boot_enabled = True

    gpu = vmm.Gpu()
    gpu.device_id = 42
    gpu.name = "Tesla T4"
    gpu.mode = vmm.GpuMode.PASSTHROUGH_GRAPHICS
    gpu.vendor = vmm.GpuVendor.NVIDIA

    defaults = {
        "ext_id": VM_EXT_ID,
        "name": "web-01",
        "description": "a test vm",
        "cluster": cluster,
        "power_state": PowerState.ON,
        "num_sockets": 2,
        "num_cores_per_socket": 4,
        "memory_size_bytes": 8589934592,
        "create_time": CREATE_TIME,
        "boot_config": boot_config,
        "gpus": [gpu],
        "nics": [make_nic()],
        "disks": [make_disk()],
    }
    defaults.update(overrides)

    vm = vmm.AhvConfigVm()
    for key, value in defaults.items():
        setattr(vm, key, value)
    return vm


# --------------------------------------------------------------------------
# VmListMetadata.from_nutanix_vm
# --------------------------------------------------------------------------


def test_vm_list_metadata_full_vm():
    result = VmListMetadata.from_nutanix_vm(make_vm())

    assert result == VmListMetadata(
        ext_id=VM_EXT_ID,
        name="web-01",
        description="a test vm",
        cluster_ext_id=CLUSTER_EXT_ID,
        power_state="ON",
        num_sockets=2,
        num_cores_per_socket=4,
        memory_size_bytes=8589934592,
        mac_address="50:6b:8d:11:22:33",
        ip_addresses=["10.0.0.5"],
        create_time=CREATE_TIME,
        disk_size_bytes=107374182400,
        gpus=[EXPECTED_GPU],
    )


def test_vm_list_metadata_bare_vm_has_no_optional_data():
    result = VmListMetadata.from_nutanix_vm(
        make_vm(cluster=None, power_state=None, nics=None, disks=None, create_time=None)
    )

    assert result.cluster_ext_id is None
    assert result.power_state is None
    assert result.mac_address is None
    assert result.ip_addresses == []
    assert result.disk_size_bytes is None
    assert result.create_time is None


def test_vm_list_metadata_only_reports_the_first_nic():
    vm = make_vm(nics=[make_nic(mac="aa:aa:aa:aa:aa:aa", ip="10.0.0.1"), make_nic()])

    result = VmListMetadata.from_nutanix_vm(vm)

    assert result.mac_address == "aa:aa:aa:aa:aa:aa"
    assert result.ip_addresses == ["10.0.0.1"]


def test_vm_list_metadata_only_reports_the_first_disk():
    vm = make_vm(disks=[make_disk(size_bytes=1), make_disk(size_bytes=2)])

    assert VmListMetadata.from_nutanix_vm(vm).disk_size_bytes == 1


def test_vm_list_metadata_nic_without_ipv4_config_yields_no_addresses():
    vm = make_vm(nics=[make_nic(ip=None)])

    assert VmListMetadata.from_nutanix_vm(vm).ip_addresses == []


def test_vm_list_metadata_nic_without_backing_info_yields_no_mac():
    vm = make_vm(nics=[make_nic(mac=None)])

    assert VmListMetadata.from_nutanix_vm(vm).mac_address is None


# --------------------------------------------------------------------------
# VmDetailsMetadata.from_nutanix_vm
# --------------------------------------------------------------------------


def test_vm_details_metadata_full_vm():
    result = VmDetailsMetadata.from_nutanix_vm(make_vm())

    assert result == VmDetailsMetadata(
        ext_id=VM_EXT_ID,
        name="web-01",
        description="a test vm",
        cluster_ext_id=CLUSTER_EXT_ID,
        power_state="ON",
        network_id=SUBNET_EXT_ID,
        num_sockets=2,
        num_cores_per_socket=4,
        memory_size_bytes=8589934592,
        mac_address="50:6b:8d:11:22:33",
        ip_addresses=["10.0.0.5"],
        create_time=CREATE_TIME,
        boot_method="uefi",
        secure_boot=True,
        gpus=[EXPECTED_GPU],
        disk_size_bytes=107374182400,
        container_id=CONTAINER_EXT_ID,
    )


def test_vm_details_metadata_uefi_without_secure_boot():
    boot_config = vmm.UefiBoot()
    boot_config.is_secure_boot_enabled = False

    result = VmDetailsMetadata.from_nutanix_vm(make_vm(boot_config=boot_config))

    assert result.boot_method == "uefi"
    assert result.secure_boot is False


def test_vm_details_metadata_legacy_boot_reports_bios_and_no_secure_boot():
    result = VmDetailsMetadata.from_nutanix_vm(make_vm(boot_config=vmm.LegacyBoot()))

    assert result.boot_method == "bios"
    assert result.secure_boot is None


def test_vm_details_metadata_unknown_boot_config_stringifies_the_type():
    """Current fallback: the *type repr* leaks into the API response."""
    result = VmDetailsMetadata.from_nutanix_vm(make_vm(boot_config=None))

    assert result.boot_method == f"{type(None)}"
    assert result.secure_boot is None


def test_vm_details_metadata_falls_back_to_nic_ext_id_without_a_subnet():
    nic = make_nic()
    nic.network_info.subnet = None

    result = VmDetailsMetadata.from_nutanix_vm(make_vm(nics=[nic]))

    assert result.network_id == NIC_EXT_ID


def test_vm_details_metadata_uses_the_first_nic_that_has_a_subnet():
    without_subnet = make_nic()
    without_subnet.network_info.subnet = None

    result = VmDetailsMetadata.from_nutanix_vm(
        make_vm(nics=[without_subnet, make_nic()])
    )

    assert result.network_id == SUBNET_EXT_ID


def test_vm_details_metadata_no_nics_means_no_network_id():
    assert VmDetailsMetadata.from_nutanix_vm(make_vm(nics=None)).network_id is None


def test_vm_details_metadata_no_gpus_yields_empty_list():
    assert VmDetailsMetadata.from_nutanix_vm(make_vm(gpus=None)).gpus == []


def test_vm_details_metadata_disk_without_storage_container_has_no_container_id():
    vm = make_vm(disks=[make_disk(container=False)])

    assert VmDetailsMetadata.from_nutanix_vm(vm).container_id is None


def test_vm_details_metadata_no_disks_means_no_size_or_container():
    result = VmDetailsMetadata.from_nutanix_vm(make_vm(disks=None))

    assert result.disk_size_bytes is None
    assert result.container_id is None


# --------------------------------------------------------------------------
# disk helpers
# --------------------------------------------------------------------------


def test_disk_sizes_bytes_from_disks_maps_non_vmdisk_backing_to_none():
    volume_group_backed = Disk()
    volume_group_backed.backing_info = None

    sizes = _disk_sizes_bytes_from_disks(
        [make_disk(size_bytes=10), volume_group_backed, make_disk(size_bytes=20)]
    )

    assert sizes == [10, None, 20]


def test_disk_sizes_bytes_from_disks_empty():
    assert _disk_sizes_bytes_from_disks([]) == []


def test_disk_container_ref_returns_none_for_non_vmdisk_backing():
    disk = Disk()
    disk.backing_info = None

    assert _disk_container_ref_from_disk(disk) is None


def test_disk_container_ref_returns_the_storage_container():
    ref = _disk_container_ref_from_disk(make_disk())

    assert ref is not None
    assert ref.ext_id == CONTAINER_EXT_ID


# --------------------------------------------------------------------------
# ImageMetadata.from_nutanix_image
# --------------------------------------------------------------------------


def _image_dict(**overrides) -> dict:
    payload = {
        "name": "rocky-9.qcow2",
        "description": "base image",
        "create_time": CREATE_TIME,
        "last_update_time": CREATE_TIME,
        "ext_id": VM_EXT_ID,
        "cluster_location_ext_ids": [CLUSTER_EXT_ID],
        "source": None,
        "placement_policy_status": None,
        "owner_ext_id": CLUSTER_EXT_ID,
        "tenant_id": None,
        "size_bytes": 1234,
        "type": "DISK_IMAGE",
    }
    payload.update(overrides)
    return payload


def test_image_metadata_selects_only_the_declared_keys():
    image = Stub(to_dict=lambda: _image_dict(links=[], extra_field="ignored"))

    result = ImageMetadata.from_nutanix_image(image)

    assert result.name == "rocky-9.qcow2"
    assert result.size_bytes == 1234
    assert result.cluster_location_ext_ids == [CLUSTER_EXT_ID]
    assert not hasattr(result, "extra_field")


def test_image_metadata_raises_when_the_payload_omits_a_declared_key():
    """No defaults: a key missing from ``to_dict()`` is a hard TypeError."""
    payload = _image_dict()
    payload.pop("size_bytes")
    image = Stub(to_dict=lambda: payload)

    with pytest.raises(TypeError, match="size_bytes"):
        ImageMetadata.from_nutanix_image(image)


# --------------------------------------------------------------------------
# GpuMetadata.from_nutanix_gpu
# --------------------------------------------------------------------------


def test_gpu_metadata_translates_every_exposed_field():
    gpu = vmm.Gpu()
    gpu.ext_id = "8a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"
    gpu.name = "Tesla T4"
    gpu.mode = vmm.GpuMode.VIRTUAL
    gpu.vendor = vmm.GpuVendor.NVIDIA
    gpu.device_id = 7864
    gpu.fraction = 50
    gpu.frame_buffer_size_bytes = 16106127360
    gpu.num_virtual_display_heads = 4
    gpu.guest_driver_version = "535.129.03"

    assert GpuMetadata.from_nutanix_gpu(gpu) == GpuMetadata(
        ext_id="8a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
        name="Tesla T4",
        mode="VIRTUAL",
        vendor="NVIDIA",
        device_id=7864,
        fraction=50,
        frame_buffer_size_bytes=16106127360,
        num_virtual_display_heads=4,
        guest_driver_version="535.129.03",
    )


def test_gpu_metadata_device_id_stays_an_int():
    # Regression: the field was annotated list[str] while being populated with
    # the SDK's int device_id. The SDK declares Gpu.device_id as int.
    gpu = vmm.Gpu()
    gpu.device_id = 7864
    device_id = GpuMetadata.from_nutanix_gpu(gpu).device_id
    assert device_id == 7864
    assert isinstance(device_id, int)


def test_gpu_metadata_bare_gpu_is_all_none():
    result = GpuMetadata.from_nutanix_gpu(vmm.Gpu())
    assert result == GpuMetadata(
        ext_id=None,
        name=None,
        mode=None,
        vendor=None,
        device_id=None,
        fraction=None,
        frame_buffer_size_bytes=None,
        num_virtual_display_heads=None,
        guest_driver_version=None,
    )


@pytest.mark.parametrize(
    "mode",
    [
        vmm.GpuMode.PASSTHROUGH_COMPUTE,
        vmm.GpuMode.PASSTHROUGH_GRAPHICS,
        vmm.GpuMode.VIRTUAL,
    ],
)
def test_gpu_metadata_stringifies_every_mode(mode):
    gpu = vmm.Gpu()
    gpu.mode = mode
    assert GpuMetadata.from_nutanix_gpu(gpu).mode == str(mode)


@pytest.mark.parametrize(
    "vendor", [vmm.GpuVendor.AMD, vmm.GpuVendor.INTEL, vmm.GpuVendor.NVIDIA]
)
def test_gpu_metadata_stringifies_every_vendor(vendor):
    gpu = vmm.Gpu()
    gpu.vendor = vendor
    assert GpuMetadata.from_nutanix_gpu(gpu).vendor == str(vendor)


def test_list_and_detail_report_identical_gpus():
    # The two converters used to disagree: detail emitted raw device ids and
    # list had no gpus field at all, so the VM index could never show GPUs.
    vm = make_vm()
    assert (
        VmListMetadata.from_nutanix_vm(vm).gpus
        == VmDetailsMetadata.from_nutanix_vm(vm).gpus
    )


def test_absent_gpus_yields_empty_list_on_both_converters():
    vm = make_vm(gpus=None)
    assert VmListMetadata.from_nutanix_vm(vm).gpus == []
    assert VmDetailsMetadata.from_nutanix_vm(vm).gpus == []
