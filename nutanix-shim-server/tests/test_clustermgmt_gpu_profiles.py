"""Tests for ``ClusterMgmt.list_physical_gpu_profiles``.

Most API-calling methods have no seam (see tests/README.md), but the cached
``_clusters_api`` attribute is one: the ``clusters_api`` property only builds a
client when ``_clusters_api`` is absent, so assigning it swaps the API out
without patching module globals. That is enough to pin the two things that can
silently go wrong here - the ``clusterExtId`` keyword spelling ``paginate``
forwards, and that each page is translated.
"""

from __future__ import annotations

import ntnx_clustermgmt_py_client as cm
from nutanix_shim_server.clustermgmt import ClusterMgmt, GpuProfileMetadata

from .conftest import Resp

CLUSTER_EXT_ID = "00061663-9fa0-28ca-185b-ac1f6b6f97e2"
GPU_PROFILE_EXT_ID = "0005a1b2-1111-2222-3333-444455556666"


class RecordingClustersApi:
    """Stands in for ``cm.ClustersApi`` - records the kwargs it is called with."""

    def __init__(self, profiles):
        self.profiles = profiles
        self.calls: list[dict] = []

    def list_physical_gpu_profiles(self, **kwargs):
        self.calls.append(kwargs)
        return Resp(data=self.profiles, metadata=None)


def make_profile() -> cm.PhysicalGpuProfile:
    config = cm.PhysicalGpuConfig()
    config.device_id = 7864
    config.device_name = "Tesla T4"
    config.vendor_name = "NVIDIA"
    config.type = cm.GpuType.PASSTHROUGH_GRAPHICS
    config.mode = cm.GpuMode.UNUSED
    config.assignable = 2

    profile = cm.PhysicalGpuProfile()
    profile.ext_id = GPU_PROFILE_EXT_ID
    profile.physical_gpu_config = config
    return profile


def test_list_physical_gpu_profiles_passes_the_cluster_id_as_clusterextid(ctx):
    api = RecordingClustersApi([make_profile()])
    mgmt = ClusterMgmt(ctx)
    mgmt._clusters_api = api  # type: ignore[attr-defined]

    mgmt.list_physical_gpu_profiles(CLUSTER_EXT_ID)

    assert api.calls[0]["clusterExtId"] == CLUSTER_EXT_ID


def test_list_physical_gpu_profiles_translates_every_profile(ctx):
    api = RecordingClustersApi([make_profile(), make_profile()])
    mgmt = ClusterMgmt(ctx)
    mgmt._clusters_api = api  # type: ignore[attr-defined]

    result = mgmt.list_physical_gpu_profiles(CLUSTER_EXT_ID)

    assert len(result) == 2
    assert all(isinstance(item, GpuProfileMetadata) for item in result)
    assert result[0].device_name == "Tesla T4"
    assert result[0].gpu_type == "PASSTHROUGH_GRAPHICS"


def test_list_physical_gpu_profiles_returns_empty_when_the_cluster_has_none(ctx):
    api = RecordingClustersApi([])
    mgmt = ClusterMgmt(ctx)
    mgmt._clusters_api = api  # type: ignore[attr-defined]

    assert mgmt.list_physical_gpu_profiles(CLUSTER_EXT_ID) == []
