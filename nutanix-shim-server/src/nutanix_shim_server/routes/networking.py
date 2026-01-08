from fastapi import APIRouter, Request

from nutanix_shim_server.clustermgmt import ClusterMgmt
from nutanix_shim_server.networking import Networking, SubnetMetadata

router = APIRouter(prefix="/api/v1/networking", tags=["Networking"])


@router.get(
    "/list-networks",
    response_model=list[SubnetMetadata],
    summary="List available networks/subnets",
    description="""
    Returns a list of all available networks (subnets) in the Nutanix environment.

    Each network includes:
    - Network ID (ext_id) - required for VM provisioning
    - Name and description
    - Subnet type (VLAN or OVERLAY)
    - IPv4 configuration (CIDR, gateway, DHCP server)
    - NAT and external connectivity settings
    - Cluster and VPC associations

    Example response:
    ```json
    [
        {
            "ext_id": "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a",
            "name": "default-network",
            "description": "Default network for VMs",
            "subnet_type": "VLAN",
            "network_id": 0,
            "cluster_name": "my-cluster",
            "ipv4_subnet": "10.0.0.0/24",
            "ipv4_gateway": "10.0.0.1",
            "dhcp_server_address": "10.0.0.2",
            "is_nat_enabled": false,
            "is_external": false,
            "vpc_reference": null
        }
    ]
    ```
    """,
)
def list_networks(request: Request) -> list[SubnetMetadata]:
    # Build cluster ext_id -> name mapping for resolving cluster names
    clustermgmt: ClusterMgmt = request.app.state.clustermgmt
    clusters = clustermgmt.list_clusters()
    cluster_map = {cluster.ext_id: cluster.name for cluster in clusters}

    api: Networking = request.app.state.networking
    return api.list_subnets(cluster_map)
