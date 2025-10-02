from __future__ import annotations

import os
import dataclasses
from typing import Self, cast
import ntnx_clustermgmt_py_client as cm

try:
    from IPython.terminal.embed import embed
except ImportError:

    def embed():
        pass


class ClusterMgmt:
    config: cm.Configuration

    def __init__(self):
        self.config = cm.Configuration()
        self.config.host = os.environ["NUTANIX_HOST"]
        self.config.scheme = "https"
        self.config.set_api_key(os.environ["NUTANIX_API_KEY"])
        self.config.max_retry_attempts = 3
        self.config.backoff_factor = 3
        self.config.verify_ssl = False  # TODO: True
        self.config.port = os.environ.get("NUTANIX_PORT", 9440)

    @property
    def client(self) -> cm.ApiClient:
        if not hasattr(self, "_client"):
            self._client = cm.ApiClient(self.config)
            self._client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )
        return self._client

    @property
    def storage_containers_api(self) -> cm.StorageContainersApi:
        if not hasattr(self, "_storage_containers_api"):
            self._storage_containers_api = cm.StorageContainersApi(
                api_client=self.client
            )
        return self._storage_containers_api

    def list_storage_containers(self):
        containers = self.storage_containers_api.list_storage_containers()
        return containers

    @property
    def clusters_api(self) -> cm.ClustersApi:
        if not hasattr(self, "_clusters_api"):
            self._clusters_api = cm.ClustersApi(api_client=self.client)
        return self._clusters_api

    def list_clusters(self) -> list[ClusterMetadata]:
        """Return list of clusters"""
        resp: cm.ListClustersApiResponse = self.clusters_api.list_clusters()
        clusters: None | list[cm.Cluster] = resp.data
        if clusters:
            return [
                ClusterMetadata.from_nutanix_cluster(cluster) for cluster in clusters
            ]
        return []


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


if __name__ == "__main__":
    mgmt = ClusterMgmt()
    mgmt.list_clusters()
