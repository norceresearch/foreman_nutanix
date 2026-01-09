from __future__ import annotations

import dataclasses
import datetime
from typing import Self, cast

import ntnx_clustermgmt_py_client as cm

from nutanix_shim_server import server
from nutanix_shim_server.utils import (
    add_default_headers,
    configure_sdk,
    paginate,
    retry_on_timeout,
)


class ClusterMgmt:
    config: cm.Configuration

    def __init__(self, ctx: server.Context):
        self.config = cm.Configuration()
        configure_sdk(self.config, ctx)

    def _clear_clients(self) -> None:
        """Clear cached clients to force re-creation on next access."""
        if hasattr(self, "_client"):
            del self._client
        if hasattr(self, "_storage_containers_api"):
            del self._storage_containers_api
        if hasattr(self, "_clusters_api"):
            del self._clusters_api

    @property
    def client(self) -> cm.ApiClient:
        if not hasattr(self, "_client"):
            self._client = cm.ApiClient(self.config)
            add_default_headers(self._client)
        return self._client

    @property
    def storage_containers_api(self) -> cm.StorageContainersApi:
        if not hasattr(self, "_storage_containers_api"):
            self._storage_containers_api = cm.StorageContainersApi(
                api_client=self.client
            )
        return self._storage_containers_api

    @retry_on_timeout
    def list_storage_containers(self) -> list[StorageContainerMetadata]:
        """Return list of storage containers"""
        containers: list[cm.StorageContainer] = paginate(
            self.storage_containers_api.list_storage_containers
        )
        return [
            StorageContainerMetadata.from_nutanix_storage_container(container)
            for container in containers
        ]

    @property
    def clusters_api(self) -> cm.ClustersApi:
        if not hasattr(self, "_clusters_api"):
            self._clusters_api = cm.ClustersApi(api_client=self.client)
        return self._clusters_api

    @retry_on_timeout
    def list_clusters(self) -> list[ClusterMetadata]:
        """Return list of clusters"""
        clusters: list[cm.Cluster] = paginate(self.clusters_api.list_clusters)
        return [ClusterMetadata.from_nutanix_cluster(cluster) for cluster in clusters]

    @retry_on_timeout
    def get_cluster_stats(self, cluster_ext_id: str) -> ClusterResourceStats:
        """Get resource usage statistics for a specific cluster

        Gets CPU/memory capacity by aggregating from cluster hosts, and usage
        stats from the cluster stats API.
        """

        # Get cluster stats for usage metrics
        end_time = datetime.datetime.now(datetime.timezone.utc)
        start_time = end_time - datetime.timedelta(hours=1)

        stats_resp: cm.ClusterStatsApiResponse = self.clusters_api.get_cluster_stats(
            extId=cluster_ext_id,
            _startTime=start_time,
            _endTime=end_time,
        )
        stats: cm.ClusterStats = stats_resp.data  # type: ignore

        # Get hosts to aggregate CPU and memory capacity
        hosts: list[cm.Host] = paginate(
            self.clusters_api.list_hosts_by_cluster_id, clusterExtId=cluster_ext_id
        )

        # Aggregate capacity from all hosts in the cluster
        total_cpu_capacity_hz = 0
        total_memory_capacity_bytes = 0
        total_cpu_cores = 0

        if hosts:
            for host in hosts:
                # Try cpu_capacity_hz first, fall back to calculating from frequency and cores
                if host.cpu_capacity_hz:
                    total_cpu_capacity_hz += host.cpu_capacity_hz
                elif host.cpu_frequency_hz and host.number_of_cpu_cores:
                    # Calculate capacity: frequency * number of cores
                    total_cpu_capacity_hz += (
                        host.cpu_frequency_hz * host.number_of_cpu_cores
                    )

                if host.memory_size_bytes:
                    total_memory_capacity_bytes += host.memory_size_bytes

                if host.number_of_cpu_cores:
                    total_cpu_cores += host.number_of_cpu_cores

        return ClusterResourceStats.from_nutanix_cluster_stats(
            stats, total_cpu_capacity_hz, total_memory_capacity_bytes, total_cpu_cores
        )


@dataclasses.dataclass(frozen=True)
class ClusterMetadata:
    name: str
    ext_id: str
    n_nodes: int
    arch: str
    vm_count: int
    is_available: bool

    @classmethod
    def from_nutanix_cluster(cls, cluster: cm.Cluster) -> Self:
        # nutanix typing is almost always "Unknown | None" - hence the casting
        nodes = cast(cm.NodeReference, cluster.nodes)
        config = cast(cm.ClusterConfigReference, cluster.config)
        return cls(
            name=cast(str, cluster.name),
            n_nodes=cast(int, nodes.number_of_nodes),
            ext_id=cast(str, cluster.ext_id),
            arch=cast(str, config.cluster_arch),
            vm_count=cast(int, cluster.vm_count),
            is_available=cast(bool, config.is_available),
        )


@dataclasses.dataclass(frozen=True)
class StorageContainerMetadata:
    """
    Metadata about a storage container.

    Includes container ID, name, capacity information, and storage features.
    """

    ext_id: str
    name: str
    cluster_name: None | str
    cluster_ext_id: None | str
    max_capacity_bytes: None | int
    logical_advertised_capacity_bytes: None | int
    replication_factor: None | int
    is_compression_enabled: None | bool
    is_encrypted: None | bool
    is_marked_for_removal: None | bool

    @classmethod
    def from_nutanix_storage_container(cls, container: cm.StorageContainer) -> Self:
        """Convert Nutanix SDK StorageContainer to our response model"""
        return cls(
            ext_id=cast(
                str, container.container_ext_id
            ),  # Note: SDK uses container_ext_id, not ext_id
            name=cast(str, container.name),
            cluster_name=container.cluster_name,
            cluster_ext_id=container.cluster_ext_id,
            max_capacity_bytes=container.max_capacity_bytes,
            logical_advertised_capacity_bytes=container.logical_advertised_capacity_bytes,
            replication_factor=container.replication_factor,
            is_compression_enabled=container.is_compression_enabled,
            is_encrypted=container.is_encrypted,
            is_marked_for_removal=container.is_marked_for_removal,
        )


@dataclasses.dataclass(frozen=True)
class ClusterResourceStats:
    """
    Resource usage statistics for a cluster.

    Includes CPU, memory, and storage capacity and usage information.
    """

    ext_id: str
    # CPU stats
    cpu_capacity_hz: int
    cpu_usage_hz: int
    cpu_usage_percent: float
    cpu_cores_total: int
    cpu_cores_usage: int
    # Memory stats
    memory_capacity_bytes: int
    memory_usage_bytes: int
    memory_usage_percent: float
    # Storage stats
    storage_capacity_bytes: int
    storage_usage_bytes: int
    storage_usage_percent: float

    @classmethod
    def from_nutanix_cluster_stats(
        cls,
        stats: cm.ClusterStats,
        cpu_capacity_hz: int = 0,
        memory_capacity_bytes: int = 0,
        cpu_cores_total: int = 0,
    ) -> Self:
        """
        Convert Nutanix SDK ClusterStats to our response model

        Notes
        -----
        Stats from Nutanix API can be time-series (lists) or scalar values.
        We extract the latest/last value from lists if needed.

        CPU and memory capacity, and CPU cores are passed in separately since
        they must be aggregated from cluster hosts (not available in ClusterStats).
        """

        def extract_value(val, field_name="unknown"):
            """Extract scalar value from either a list or scalar

            Handles:
            - None -> 0
            - Scalar values -> value
            - Lists of TimeValuePair -> extract value from last pair
            - Empty lists -> 0
            """
            if val is None:
                return 0
            if isinstance(val, list):
                if not val:
                    return 0
                # Take the last value from time series
                last_item = val[-1]
                # If it's a TimeValuePair object, extract the value
                if hasattr(last_item, "value"):
                    return last_item.value if last_item.value is not None else 0
                return last_item
            # Handle TimeValuePair objects directly
            if hasattr(val, "value"):
                return val.value if val.value is not None else 0
            return val

        # Extract usage values from stats (storage includes capacity too)
        # CPU: Use hypervisor_cpu_usage_ppm to calculate usage from capacity
        cpu_usage_ppm = extract_value(
            stats.hypervisor_cpu_usage_ppm, "hypervisor_cpu_usage_ppm"
        )
        cpu_usage_hz = (
            int(cpu_capacity_hz * (cpu_usage_ppm / 1_000_000)) if cpu_capacity_hz else 0
        )
        cpu_usage_pct = (cpu_usage_hz / cpu_capacity_hz * 100) if cpu_capacity_hz else 0

        # Estimate cores in use based on usage percentage
        cpu_cores_usage = (
            int(cpu_cores_total * (cpu_usage_pct / 100)) if cpu_cores_total else 0
        )

        # Memory: overall_memory_usage_bytes from stats, capacity from aggregated hosts
        memory_usage = extract_value(
            stats.overall_memory_usage_bytes, "overall_memory_usage_bytes"
        )
        memory_usage_pct = (
            (memory_usage / memory_capacity_bytes * 100) if memory_capacity_bytes else 0
        )

        # Storage: both capacity and usage from stats
        storage_capacity = extract_value(
            stats.storage_capacity_bytes, "storage_capacity_bytes"
        )
        storage_usage = extract_value(stats.storage_usage_bytes, "storage_usage_bytes")
        storage_usage_pct = (
            (storage_usage / storage_capacity * 100) if storage_capacity else 0
        )

        return cls(
            ext_id=cast(str, stats.ext_id),
            cpu_capacity_hz=int(cpu_capacity_hz),
            cpu_usage_hz=int(cpu_usage_hz),
            cpu_usage_percent=round(cpu_usage_pct, 2),
            cpu_cores_total=int(cpu_cores_total),
            cpu_cores_usage=int(cpu_cores_usage),
            memory_capacity_bytes=int(memory_capacity_bytes),
            memory_usage_bytes=int(memory_usage),
            memory_usage_percent=round(memory_usage_pct, 2),
            storage_capacity_bytes=int(storage_capacity),
            storage_usage_bytes=int(storage_usage),
            storage_usage_percent=round(storage_usage_pct, 2),
        )


if __name__ == "__main__":
    mgmt = ClusterMgmt()
    mgmt.list_clusters()
