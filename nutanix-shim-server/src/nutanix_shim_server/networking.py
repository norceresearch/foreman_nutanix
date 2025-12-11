from __future__ import annotations

import dataclasses
import logging
from typing import Self, cast

import ntnx_networking_py_client as net

from nutanix_shim_server import server
from nutanix_shim_server.utils import paginate

logger = logging.getLogger(__name__)


class Networking:
    config: net.Configuration

    def __init__(self, ctx: server.Context):
        self.config = net.Configuration()
        self.config.host = ctx.nutanix_host
        self.config.scheme = ctx.nutanix_host_scheme
        self.config.set_api_key(ctx.nutanix_api_key)
        self.config.max_retry_attempts = 3
        self.config.backoff_factor = 3
        self.config.verify_ssl = ctx.nutanix_host_verify_ssl
        self.config.port = ctx.nutanix_host_port
        self.config.client_certificate_file = ctx.nutanix_client_certificate_file
        self.config.root_ca_certificate_file = ctx.nutanix_root_ca_certificate_file

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
        subnets: list[net.Subnet] = paginate(self.subnets_api.list_subnets)
        return [SubnetMetadata.from_nutanix_subnet(subnet) for subnet in subnets]


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

        # Check if cluster_ext_id exists (it might be in cluster_reference)
        cluster_ext_id = None
        if hasattr(subnet, "cluster_ext_id"):
            cluster_ext_id = subnet.cluster_ext_id  # type: ignore
        elif hasattr(subnet, "cluster_reference") and subnet.cluster_reference:
            cluster_ext_id = (
                subnet.cluster_reference.ext_id
                if hasattr(subnet.cluster_reference, "ext_id")
                else None
            )

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
