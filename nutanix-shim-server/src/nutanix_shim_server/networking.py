from __future__ import annotations

import dataclasses
from typing import Self, cast

import ntnx_networking_py_client as net

from nutanix_shim_server import server
from nutanix_shim_server.utils import (
    add_default_headers,
    configure_sdk,
    paginate,
    retry_on_timeout,
)


class Networking:
    config: net.Configuration

    def __init__(self, ctx: server.Context):
        self.config = net.Configuration()
        configure_sdk(self.config, ctx)

    def _clear_clients(self) -> None:
        """Clear cached clients to force re-creation on next access."""
        if hasattr(self, "_client"):
            del self._client
        if hasattr(self, "_subnets_api"):
            del self._subnets_api

    @property
    def client(self) -> net.ApiClient:
        if not hasattr(self, "_client"):
            self._client = net.ApiClient(self.config)
            add_default_headers(self._client)
        return self._client

    @property
    def subnets_api(self) -> net.SubnetsApi:
        if not hasattr(self, "_subnets_api"):
            self._subnets_api = net.SubnetsApi(api_client=self.client)
        return self._subnets_api

    @retry_on_timeout
    def list_subnets(
        self, cluster_map: dict[str, str] | None = None
    ) -> list[SubnetMetadata]:
        """Return list of available subnets/networks

        Args:
            cluster_map: Optional mapping of cluster ext_id -> cluster name.
                         Used to resolve cluster names for subnets.
        """
        subnets: list[net.Subnet] = paginate(self.subnets_api.list_subnets)
        return [
            SubnetMetadata.from_nutanix_subnet(subnet, cluster_map)
            for subnet in subnets
        ]


@dataclasses.dataclass(frozen=True)
class SubnetMetadata:
    """
    Metadata about a network/subnet.

    Includes network ID, name, type, IP configuration, and DHCP settings.
    """

    ext_id: str
    name: str
    description: None | str
    subnet_type: None | str
    network_id: None | int
    cluster_name: None | str
    cluster_ext_id: None | str
    ipv4_subnet: None | str  # CIDR notation (e.g., "10.0.0.0/24")
    ipv4_gateway: None | str
    dhcp_server_address: None | str
    is_nat_enabled: None | bool
    is_external: None | bool
    vpc_reference: None | str

    @classmethod
    def from_nutanix_subnet(
        cls, subnet: net.Subnet, cluster_map: dict[str, str] | None = None
    ) -> Self:
        """Convert Nutanix SDK Subnet to our response model

        Args:
            subnet: The Nutanix SDK Subnet object
            cluster_map: Optional mapping of cluster ext_id -> cluster name
        """
        # Extract IPv4 configuration if available
        ipv4_subnet = None
        ipv4_gateway = None
        dhcp_server_address = None

        if subnet.ip_config:
            # Get the first IP config (typically only one)
            ip_config = subnet.ip_config[0] if subnet.ip_config else None
            if ip_config and ip_config.ipv4:
                ipv4_config = ip_config.ipv4
                # Build CIDR notation
                if ipv4_config.ip_subnet:
                    ip = (
                        cast(str, ipv4_config.ip_subnet.ip.value)
                        if ipv4_config.ip_subnet.ip
                        else None
                    )
                    prefix = ipv4_config.ip_subnet.prefix_length
                    if ip and prefix:
                        ipv4_subnet = f"{ip}/{prefix}"

                # Get gateway
                if ipv4_config.default_gateway_ip:
                    ipv4_gateway = cast(str, ipv4_config.default_gateway_ip.value)

                # Get DHCP server
                if ipv4_config.dhcp_server_address:
                    dhcp_server_address = cast(
                        str, ipv4_config.dhcp_server_address.value
                    )

        # Extract cluster_ext_id - try multiple possible attribute names
        # The Nutanix SDK uses different names in different API versions
        cluster_ext_id = None

        # Try direct cluster_ext_id attribute
        if hasattr(subnet, "cluster_ext_id") and subnet.cluster_ext_id:
            cluster_ext_id = subnet.cluster_ext_id  # type: ignore
        # Try "cluster" attribute (like VMs use) - could be object or string
        elif hasattr(subnet, "cluster") and subnet.cluster:
            if isinstance(subnet.cluster, str):
                cluster_ext_id = subnet.cluster
            elif hasattr(subnet.cluster, "ext_id"):
                cluster_ext_id = subnet.cluster.ext_id
        # Try "cluster_reference" attribute - could be object or string
        elif hasattr(subnet, "cluster_reference") and subnet.cluster_reference:
            if isinstance(subnet.cluster_reference, str):
                cluster_ext_id = subnet.cluster_reference
            elif hasattr(subnet.cluster_reference, "ext_id"):
                cluster_ext_id = subnet.cluster_reference.ext_id

        # Resolve cluster name from cluster_ext_id using the provided map
        cluster_name = None
        if cluster_ext_id and cluster_map:
            cluster_name = cluster_map.get(cluster_ext_id)

        return cls(
            ext_id=cast(str, subnet.ext_id),
            name=cast(str, subnet.name),
            description=subnet.description,
            subnet_type=str(subnet.subnet_type) if subnet.subnet_type else None,
            network_id=subnet.network_id,
            cluster_name=cluster_name,
            cluster_ext_id=cluster_ext_id,
            ipv4_subnet=ipv4_subnet,
            ipv4_gateway=ipv4_gateway,
            dhcp_server_address=dhcp_server_address,
            is_nat_enabled=subnet.is_nat_enabled,
            is_external=subnet.is_external,
            vpc_reference=subnet.vpc_reference,
        )
