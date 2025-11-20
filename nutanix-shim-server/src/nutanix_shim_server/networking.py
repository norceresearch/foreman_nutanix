from __future__ import annotations

import os
import dataclasses
import logging
from typing import Self, cast
import ntnx_networking_py_client as net

logger = logging.getLogger(__name__)

try:
    from IPython.terminal.embed import embed
except ImportError:

    def embed():
        pass


class Networking:
    config: net.Configuration

    def __init__(self):
        self.config = net.Configuration()
        self.config.host = os.environ["NUTANIX_HOST"]
        self.config.scheme = "https"
        self.config.set_api_key(os.environ["NUTANIX_API_KEY"])
        self.config.max_retry_attempts = 3
        self.config.backoff_factor = 3
        self.config.verify_ssl = False  # TODO: True
        self.config.port = os.environ.get("NUTANIX_PORT", 9440)

    @property
    def client(self) -> net.ApiClient:
        if not hasattr(self, "_client"):
            self._client = net.ApiClient(self.config)
            self._client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )
        return self._client

    @property
    def subnets_api(self) -> net.SubnetsApi:
        if not hasattr(self, "_subnets_api"):
            self._subnets_api = net.SubnetsApi(api_client=self.client)
        return self._subnets_api

    def list_subnets(self) -> list[SubnetMetadata]:
        """Return list of available subnets/networks"""
        # TODO: paginate
        resp: net.ListSubnetsApiResponse = self.subnets_api.list_subnets(_limit=100)  # type: ignore
        subnets: None | list[net.Subnet] = resp.data  # type: ignore
        if subnets:
            return [SubnetMetadata.from_nutanix_subnet(subnet) for subnet in subnets]
        return []


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
    def from_nutanix_subnet(cls, subnet: net.Subnet) -> Self:
        """Convert Nutanix SDK Subnet to our response model"""
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
                    ip = cast(str, ipv4_config.ip_subnet.ip.value) if ipv4_config.ip_subnet.ip else None
                    prefix = ipv4_config.ip_subnet.prefix_length
                    if ip and prefix:
                        ipv4_subnet = f"{ip}/{prefix}"

                # Get gateway
                if ipv4_config.default_gateway_ip:
                    ipv4_gateway = cast(str, ipv4_config.default_gateway_ip.value)

                # Get DHCP server
                if ipv4_config.dhcp_server_address:
                    dhcp_server_address = cast(str, ipv4_config.dhcp_server_address.value)

        # Check if cluster_ext_id exists (it might be in cluster_reference)
        cluster_ext_id = None
        if hasattr(subnet, 'cluster_ext_id'):
            cluster_ext_id = subnet.cluster_ext_id
        elif hasattr(subnet, 'cluster_reference') and subnet.cluster_reference:
            cluster_ext_id = subnet.cluster_reference.ext_id if hasattr(subnet.cluster_reference, 'ext_id') else None

        return cls(
            ext_id=cast(str, subnet.ext_id),
            name=cast(str, subnet.name),
            description=subnet.description,
            subnet_type=str(subnet.subnet_type) if subnet.subnet_type else None,
            network_id=subnet.network_id,
            cluster_name=subnet.cluster_name,
            cluster_ext_id=cluster_ext_id,
            ipv4_subnet=ipv4_subnet,
            ipv4_gateway=ipv4_gateway,
            dhcp_server_address=dhcp_server_address,
            is_nat_enabled=subnet.is_nat_enabled,
            is_external=subnet.is_external,
            vpc_reference=subnet.vpc_reference,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgmt = Networking()
    subnets = mgmt.list_subnets()
    logger.info(f"Found {len(subnets)} subnets")
    for subnet in subnets:
        logger.info(f"  - {subnet.name} ({subnet.ext_id}): {subnet.ipv4_subnet}")
