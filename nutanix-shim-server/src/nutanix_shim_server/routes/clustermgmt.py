from fastapi import APIRouter, Request

from nutanix_shim_server.clustermgmt import (
    ClusterMetadata,
    ClusterMgmt,
    ClusterResourceStats,
    GpuProfileMetadata,
    StorageContainerMetadata,
)

router = APIRouter(prefix="/api/v1/clustermgmt", tags=["Cluster Management"])


@router.get(
    "/list-clusters",
    response_model=list[ClusterMetadata],
    tags=["Cluster Management"],
)
def list_clusters(request: Request) -> list[ClusterMetadata]:
    api: ClusterMgmt = request.app.state.clustermgmt
    return api.list_clusters()


@router.get(
    "/clusters/{cluster_id}/stats",
    response_model=ClusterResourceStats,
    summary="Get cluster resource statistics",
    description="""
    Returns resource usage statistics for a specific cluster.

    Includes CPU, memory, and storage capacity and usage information with
    calculated usage percentages.

    Path Parameters:
    - cluster_id: The external ID of the cluster

    Example response:
    ```json
    {
        "ext_id": "00061663-9fa0-28ca-185b-ac1f6b6f97e2",
        "cpu_capacity_hz": 96000000000,
        "cpu_usage_hz": 24000000000,
        "cpu_usage_percent": 25.0,
        "memory_capacity_bytes": 274877906944,
        "memory_usage_bytes": 137438953472,
        "memory_usage_percent": 50.0,
        "storage_capacity_bytes": 10995116277760,
        "storage_usage_bytes": 5497558138880,
        "storage_usage_percent": 50.0
    }
    ```
    """,
)
def get_cluster_stats(cluster_id: str, request: Request) -> ClusterResourceStats:
    api: ClusterMgmt = request.app.state.clustermgmt
    return api.get_cluster_stats(cluster_id)


@router.get(
    "/clusters/{cluster_id}/gpu-profiles",
    response_model=list[GpuProfileMetadata],
    summary="List physical GPU profiles on a cluster",
    description="""
    Returns the physical GPU profiles available on a specific cluster.

    A profile describes a GPU *model* present on the cluster rather than one
    physical card. Provisioning attaches by `device_id`, so Nutanix is free to
    schedule any matching card that is not already in use.

    Each profile includes:
    - Profile ID (ext_id)
    - Device ID (device_id) - required to attach the GPU at provision time
    - Device and vendor names for display
    - GPU type (gpu_type): PASSTHROUGH_COMPUTE | PASSTHROUGH_GRAPHICS | VIRTUAL.
      This is the value that maps onto the VM-side GPU mode; it is *not* the
      SDK's allocation-state `mode` field.
    - How many remain assignable, and whether any is in use
    - The VMs the GPU is currently allocated to (allocated_vm_ext_ids)

    Path Parameters:
    - cluster_id: The external ID of the cluster

    Example response:
    ```json
    [
        {
            "ext_id": "0005a1b2-1111-2222-3333-444455556666",
            "device_id": 7864,
            "device_name": "Tesla T4",
            "vendor_name": "NVIDIA",
            "gpu_type": "PASSTHROUGH_GRAPHICS",
            "assignable": 3,
            "is_in_use": true,
            "frame_buffer_size_bytes": 17179869184,
            "numa_node": "0",
            "sbdf": "0000:3b:00.0",
            "allocated_vm_ext_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
        }
    ]
    ```
    """,
)
def list_gpu_profiles(cluster_id: str, request: Request) -> list[GpuProfileMetadata]:
    api: ClusterMgmt = request.app.state.clustermgmt
    return api.list_physical_gpu_profiles(cluster_id)


@router.get(
    "/list-storage-containers",
    response_model=list[StorageContainerMetadata],
    summary="List available storage containers",
    description="""
    Returns a list of all available storage containers in the Nutanix environment.

    Each storage container includes:
    - Container ID (ext_id) - required for VM disk provisioning
    - Name and cluster association
    - Capacity information (max capacity and advertised capacity in bytes)
    - Storage features (compression, encryption, replication factor)
    - Status (marked for removal)

    Example response:
    ```json
    [
        {
            "ext_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
            "name": "default-container",
            "cluster_name": "my-cluster",
            "cluster_ext_id": "00061663-9fa0-28ca-185b-ac1f6b6f97e2",
            "max_capacity_bytes": 10995116277760,
            "logical_advertised_capacity_bytes": 10995116277760,
            "replication_factor": 2,
            "is_compression_enabled": true,
            "is_encrypted": false,
            "is_marked_for_removal": false
        }
    ]
    ```
    """,
)
def list_storage_containers(request: Request) -> list[StorageContainerMetadata]:
    api: ClusterMgmt = request.app.state.clustermgmt
    return api.list_storage_containers()
