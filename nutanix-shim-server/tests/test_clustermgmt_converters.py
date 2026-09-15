"""Tests for the clustermgmt.py translation classmethods.

Real SDK models are used throughout: they construct empty and accept attribute
assignment, so there is no reason to fake them.
"""

from __future__ import annotations

import ntnx_clustermgmt_py_client as cm
import pytest
from nutanix_shim_server.clustermgmt import (
    ClusterMetadata,
    ClusterResourceStats,
    GpuProfileMetadata,
    StorageContainerMetadata,
)

from .conftest import Stub

CLUSTER_EXT_ID = "00061663-9fa0-28ca-185b-ac1f6b6f97e2"
CONTAINER_EXT_ID = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
GPU_PROFILE_EXT_ID = "0005a1b2-1111-2222-3333-444455556666"
VM_EXT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def make_cluster(
    n_nodes=3, arch="X86_64", vm_count=17, is_available=True
) -> cm.Cluster:
    nodes = cm.NodeReference()
    nodes.number_of_nodes = n_nodes

    config = cm.ClusterConfigReference()
    config.cluster_arch = arch
    config.is_available = is_available

    cluster = cm.Cluster()
    cluster.ext_id = CLUSTER_EXT_ID
    cluster.name = "prod-cluster"
    cluster.nodes = nodes
    cluster.config = config
    cluster.vm_count = vm_count
    return cluster


def time_values(*values) -> list[cm.TimeValuePair]:
    pairs = []
    for value in values:
        pair = cm.TimeValuePair()
        pair.value = value
        pairs.append(pair)
    return pairs


# --------------------------------------------------------------------------
# ClusterMetadata.from_nutanix_cluster
# --------------------------------------------------------------------------


def test_cluster_metadata_maps_nested_node_and_config_references():
    result = ClusterMetadata.from_nutanix_cluster(make_cluster())

    assert result == ClusterMetadata(
        name="prod-cluster",
        ext_id=CLUSTER_EXT_ID,
        n_nodes=3,
        arch="X86_64",
        vm_count=17,
        is_available=True,
    )


def test_cluster_metadata_passes_through_unset_nested_values_untouched():
    """The ``cast`` calls are type-checker-only: None flows straight through."""
    cluster = make_cluster()
    cluster.nodes = cm.NodeReference()
    cluster.config = cm.ClusterConfigReference()
    cluster.vm_count = None

    result = ClusterMetadata.from_nutanix_cluster(cluster)

    assert result.n_nodes is None
    assert result.arch is None
    assert result.is_available is None
    assert result.vm_count is None


def test_cluster_metadata_raises_when_nodes_reference_is_missing():
    """Current behaviour: a cluster with no ``nodes`` blows up with
    AttributeError rather than degrading."""
    cluster = make_cluster()
    cluster.nodes = None

    with pytest.raises(AttributeError):
        ClusterMetadata.from_nutanix_cluster(cluster)


# --------------------------------------------------------------------------
# StorageContainerMetadata.from_nutanix_storage_container
# --------------------------------------------------------------------------


def test_storage_container_metadata_uses_container_ext_id_not_ext_id():
    container = cm.StorageContainer()
    container.ext_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    container.container_ext_id = CONTAINER_EXT_ID
    container.name = "default-container"
    container.cluster_name = "prod-cluster"
    container.cluster_ext_id = CLUSTER_EXT_ID
    container.max_capacity_bytes = 10 * 2**40
    container.logical_advertised_capacity_bytes = 9 * 2**40
    container.replication_factor = 2
    container.is_compression_enabled = True
    container.is_encrypted = False
    container.is_marked_for_removal = False

    result = StorageContainerMetadata.from_nutanix_storage_container(container)

    assert result.ext_id == CONTAINER_EXT_ID
    assert result.name == "default-container"
    assert result.cluster_name == "prod-cluster"
    assert result.cluster_ext_id == CLUSTER_EXT_ID
    assert result.max_capacity_bytes == 10 * 2**40
    assert result.logical_advertised_capacity_bytes == 9 * 2**40
    assert result.replication_factor == 2
    assert result.is_compression_enabled is True
    assert result.is_encrypted is False
    assert result.is_marked_for_removal is False


def test_storage_container_metadata_tolerates_an_entirely_empty_container():
    result = StorageContainerMetadata.from_nutanix_storage_container(
        cm.StorageContainer()
    )

    assert result.ext_id is None
    assert result.name is None
    assert result.max_capacity_bytes is None


# --------------------------------------------------------------------------
# ClusterResourceStats.from_nutanix_cluster_stats
# --------------------------------------------------------------------------


def test_cluster_resource_stats_derives_cpu_memory_and_storage():
    stats = cm.ClusterStats()
    stats.ext_id = CLUSTER_EXT_ID
    # 25% of capacity, expressed in parts-per-million
    stats.hypervisor_cpu_usage_ppm = time_values(250_000)
    stats.overall_memory_usage_bytes = time_values(2_000_000_000)
    stats.storage_capacity_bytes = time_values(1_000_000_000_000)
    stats.storage_usage_bytes = time_values(250_000_000_000)

    result = ClusterResourceStats.from_nutanix_cluster_stats(
        stats,
        cpu_capacity_hz=100_000_000_000,
        memory_capacity_bytes=8_000_000_000,
        cpu_cores_total=64,
    )

    assert result.ext_id == CLUSTER_EXT_ID
    assert result.cpu_capacity_hz == 100_000_000_000
    assert result.cpu_usage_hz == 25_000_000_000
    assert result.cpu_usage_percent == 25.0
    assert result.cpu_cores_total == 64
    assert result.cpu_cores_usage == 16
    assert result.memory_capacity_bytes == 8_000_000_000
    assert result.memory_usage_bytes == 2_000_000_000
    assert result.memory_usage_percent == 25.0
    assert result.storage_capacity_bytes == 1_000_000_000_000
    assert result.storage_usage_bytes == 250_000_000_000
    assert result.storage_usage_percent == 25.0


def test_cluster_resource_stats_uses_the_last_point_of_a_time_series():
    stats = cm.ClusterStats()
    stats.ext_id = CLUSTER_EXT_ID
    stats.hypervisor_cpu_usage_ppm = time_values(100_000, 500_000, 900_000)

    result = ClusterResourceStats.from_nutanix_cluster_stats(
        stats, cpu_capacity_hz=1_000_000
    )

    assert result.cpu_usage_hz == 900_000


def test_cluster_resource_stats_zero_capacity_avoids_division_by_zero():
    """All the derived percentages short-circuit to 0 rather than raising."""
    stats = cm.ClusterStats()
    stats.ext_id = CLUSTER_EXT_ID
    stats.hypervisor_cpu_usage_ppm = time_values(500_000)

    result = ClusterResourceStats.from_nutanix_cluster_stats(stats)

    assert result.cpu_capacity_hz == 0
    assert result.cpu_usage_hz == 0
    assert result.cpu_usage_percent == 0
    assert result.cpu_cores_usage == 0
    assert result.memory_usage_percent == 0
    assert result.storage_usage_percent == 0


def test_cluster_resource_stats_missing_and_empty_series_become_zero():
    stats = cm.ClusterStats()
    stats.ext_id = CLUSTER_EXT_ID
    stats.hypervisor_cpu_usage_ppm = None
    stats.overall_memory_usage_bytes = []
    stats.storage_capacity_bytes = time_values(None)
    stats.storage_usage_bytes = None

    result = ClusterResourceStats.from_nutanix_cluster_stats(
        stats, memory_capacity_bytes=1_000
    )

    assert result.memory_usage_bytes == 0
    assert result.storage_capacity_bytes == 0
    assert result.storage_usage_bytes == 0


def test_cluster_resource_stats_accepts_bare_scalars_as_well_as_pairs():
    """``extract_value`` also handles plain numbers, not just TimeValuePairs."""
    stats = Stub(
        ext_id=CLUSTER_EXT_ID,
        hypervisor_cpu_usage_ppm=500_000,
        overall_memory_usage_bytes=512,
        storage_capacity_bytes=1_000,
        storage_usage_bytes=100,
    )

    result = ClusterResourceStats.from_nutanix_cluster_stats(
        stats,  # type: ignore[arg-type]
        cpu_capacity_hz=1_000,
        memory_capacity_bytes=1_024,
    )

    assert result.cpu_usage_hz == 500
    assert result.memory_usage_percent == 50.0
    assert result.storage_usage_percent == 10.0


def test_cluster_resource_stats_rounds_percentages_to_two_places():
    stats = cm.ClusterStats()
    stats.ext_id = CLUSTER_EXT_ID
    stats.storage_capacity_bytes = time_values(3)
    stats.storage_usage_bytes = time_values(1)

    result = ClusterResourceStats.from_nutanix_cluster_stats(stats)

    assert result.storage_usage_percent == 33.33


# --------------------------------------------------------------------------
# GpuProfileMetadata.from_nutanix_physical_gpu_profile
# --------------------------------------------------------------------------


def make_physical_gpu_profile(
    gpu_type=cm.GpuType.PASSTHROUGH_GRAPHICS,
    mode=cm.GpuMode.USED_FOR_PASSTHROUGH,
) -> cm.PhysicalGpuProfile:
    config = cm.PhysicalGpuConfig()
    config.device_id = 7864
    config.device_name = "Tesla T4"
    config.vendor_name = "NVIDIA"
    config.type = gpu_type
    config.mode = mode
    config.assignable = 3
    config.is_in_use = True
    config.frame_buffer_size_bytes = 16 * 2**30
    config.numa_node = "0"
    config.sbdf = "0000:3b:00.0"

    profile = cm.PhysicalGpuProfile()
    profile.ext_id = GPU_PROFILE_EXT_ID
    profile.physical_gpu_config = config
    profile.allocated_vm_ext_ids = [VM_EXT_ID]
    return profile


def test_gpu_profile_metadata_flattens_the_nested_physical_gpu_config():
    result = GpuProfileMetadata.from_nutanix_physical_gpu_profile(
        make_physical_gpu_profile()
    )

    assert result == GpuProfileMetadata(
        ext_id=GPU_PROFILE_EXT_ID,
        device_id=7864,
        device_name="Tesla T4",
        vendor_name="NVIDIA",
        gpu_type="PASSTHROUGH_GRAPHICS",
        assignable=3,
        is_in_use=True,
        frame_buffer_size_bytes=16 * 2**30,
        numa_node="0",
        sbdf="0000:3b:00.0",
        allocated_vm_ext_ids=[VM_EXT_ID],
    )


def test_gpu_profile_metadata_tolerates_an_absent_physical_gpu_config():
    """Consistent with the other converters: an absent nested object degrades
    to all-None rather than raising."""
    profile = cm.PhysicalGpuProfile()
    profile.ext_id = GPU_PROFILE_EXT_ID
    profile.physical_gpu_config = None

    result = GpuProfileMetadata.from_nutanix_physical_gpu_profile(profile)

    assert result.ext_id == GPU_PROFILE_EXT_ID
    assert result.device_id is None
    assert result.device_name is None
    assert result.vendor_name is None
    assert result.gpu_type is None
    assert result.assignable is None
    assert result.is_in_use is None
    assert result.frame_buffer_size_bytes is None
    assert result.numa_node is None
    assert result.sbdf is None
    assert result.allocated_vm_ext_ids == []


@pytest.mark.parametrize(
    "gpu_type",
    [
        cm.GpuType.PASSTHROUGH_COMPUTE,
        cm.GpuType.PASSTHROUGH_GRAPHICS,
        cm.GpuType.VIRTUAL,
    ],
)
def test_gpu_profile_metadata_stringifies_every_gpu_type(gpu_type):
    profile = make_physical_gpu_profile(gpu_type=gpu_type)

    result = GpuProfileMetadata.from_nutanix_physical_gpu_profile(profile)

    assert result.gpu_type == str(gpu_type)


@pytest.mark.parametrize(
    "mode",
    [cm.GpuMode.UNUSED, cm.GpuMode.USED_FOR_PASSTHROUGH, cm.GpuMode.USED_FOR_VIRTUAL],
)
def test_gpu_profile_metadata_reads_gpu_type_from_type_never_from_mode(mode):
    """Regression guard for the trap this model exists to avoid.

    ``PhysicalGpuConfig.mode`` is allocation *state* (UNUSED /
    USED_FOR_PASSTHROUGH / USED_FOR_VIRTUAL). The field that maps onto
    ``vmm.GpuMode`` is ``PhysicalGpuConfig.type``. Both are strings, so reading
    the wrong one type-checks and only fails against a live cluster: pin it.
    """
    profile = make_physical_gpu_profile(
        gpu_type=cm.GpuType.PASSTHROUGH_COMPUTE, mode=mode
    )

    result = GpuProfileMetadata.from_nutanix_physical_gpu_profile(profile)

    assert result.gpu_type == "PASSTHROUGH_COMPUTE"
    assert result.gpu_type != str(mode)
