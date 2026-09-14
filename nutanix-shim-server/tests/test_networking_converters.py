"""Tests for SubnetMetadata.from_nutanix_subnet.

Note: the real ``net.Subnet`` model exposes only ``cluster_reference`` - it has
neither ``cluster_ext_id`` nor ``cluster``. The other two branches of the
cluster-id lookup are therefore unreachable with a genuine SDK object and are
covered with stubs purely to pin what they would do.
"""

from __future__ import annotations

import ntnx_networking_py_client as net
from nutanix_shim_server.networking import SubnetMetadata

from .conftest import Stub

SUBNET_EXT_ID = "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a"
CLUSTER_EXT_ID = "00061663-9fa0-28ca-185b-ac1f6b6f97e2"


def make_ip_config(
    ip: str | None = "10.0.0.0",
    prefix: int | None = 24,
    gateway: str | None = "10.0.0.1",
    dhcp: str | None = "10.0.0.2",
) -> net.IPConfig:
    ipv4 = net.IPv4Config()

    if ip is not None:
        subnet_ip = net.IPv4Address()
        subnet_ip.value = ip
        ip_subnet = net.IPv4Subnet()
        ip_subnet.ip = subnet_ip
        if prefix is not None:
            # The SDK setter rejects None outright, so leave it at its default.
            ip_subnet.prefix_length = prefix
        ipv4.ip_subnet = ip_subnet

    if gateway is not None:
        gw = net.IPv4Address()
        gw.value = gateway
        ipv4.default_gateway_ip = gw

    if dhcp is not None:
        dhcp_addr = net.IPv4Address()
        dhcp_addr.value = dhcp
        ipv4.dhcp_server_address = dhcp_addr

    ip_config = net.IPConfig()
    ip_config.ipv4 = ipv4
    return ip_config


def make_subnet(**overrides) -> net.Subnet:
    defaults = {
        "ext_id": SUBNET_EXT_ID,
        "name": "vlan-100",
        "description": "prod vlan",
        "subnet_type": net.SubnetType.VLAN,
        "network_id": 100,
        "cluster_reference": CLUSTER_EXT_ID,
        "ip_config": [make_ip_config()],
        "is_nat_enabled": False,
        "is_external": False,
        "vpc_reference": None,
    }
    defaults.update(overrides)

    subnet = net.Subnet()
    for key, value in defaults.items():
        setattr(subnet, key, value)
    return subnet


def test_full_subnet_is_translated():
    result = SubnetMetadata.from_nutanix_subnet(make_subnet())

    assert result.ext_id == SUBNET_EXT_ID
    assert result.name == "vlan-100"
    assert result.description == "prod vlan"
    assert result.subnet_type == "VLAN"
    assert result.network_id == 100
    assert result.cluster_ext_id == CLUSTER_EXT_ID
    assert result.ipv4_subnet == "10.0.0.0/24"
    assert result.ipv4_gateway == "10.0.0.1"
    assert result.dhcp_server_address == "10.0.0.2"
    assert result.is_nat_enabled is False
    assert result.is_external is False
    assert result.vpc_reference is None


def test_cluster_name_is_resolved_from_the_supplied_map():
    result = SubnetMetadata.from_nutanix_subnet(
        make_subnet(), {CLUSTER_EXT_ID: "prod-cluster"}
    )

    assert result.cluster_name == "prod-cluster"


def test_cluster_name_is_none_without_a_map():
    assert SubnetMetadata.from_nutanix_subnet(make_subnet()).cluster_name is None


def test_cluster_name_is_none_when_the_map_misses_the_cluster():
    result = SubnetMetadata.from_nutanix_subnet(make_subnet(), {"other-id": "other"})

    assert result.cluster_name is None


def test_subnet_without_ip_config_has_no_ipv4_fields():
    result = SubnetMetadata.from_nutanix_subnet(make_subnet(ip_config=None))

    assert result.ipv4_subnet is None
    assert result.ipv4_gateway is None
    assert result.dhcp_server_address is None


def test_cidr_requires_both_ip_and_prefix_length():
    result = SubnetMetadata.from_nutanix_subnet(
        make_subnet(ip_config=[make_ip_config(prefix=None)])
    )

    assert result.ipv4_subnet is None
    # The other fields of the same ip_config still come through.
    assert result.ipv4_gateway == "10.0.0.1"


def test_only_the_first_ip_config_entry_is_read():
    result = SubnetMetadata.from_nutanix_subnet(
        make_subnet(
            ip_config=[
                make_ip_config(ip="192.168.1.0", prefix=25, gateway="192.168.1.1"),
                make_ip_config(),
            ]
        )
    )

    assert result.ipv4_subnet == "192.168.1.0/25"
    assert result.ipv4_gateway == "192.168.1.1"


def test_subnet_type_none_stays_none():
    assert (
        SubnetMetadata.from_nutanix_subnet(make_subnet(subnet_type=None)).subnet_type
        is None
    )


def test_real_sdk_subnet_resolves_cluster_via_cluster_reference_only():
    """Pins that the real model has none of the alternative attribute names."""
    subnet = make_subnet()

    assert not hasattr(subnet, "cluster_ext_id")
    assert not hasattr(subnet, "cluster")
    assert SubnetMetadata.from_nutanix_subnet(subnet).cluster_ext_id == CLUSTER_EXT_ID


def test_cluster_reference_object_is_unwrapped_via_ext_id():
    """Unreachable via the real SDK model - ``Subnet.cluster_reference`` has a
    setter that rejects anything but a UUID string - so a stub stands in."""
    subnet = Stub(
        ext_id=SUBNET_EXT_ID,
        name="vlan-100",
        description=None,
        subnet_type=None,
        network_id=None,
        ip_config=None,
        is_nat_enabled=None,
        is_external=None,
        vpc_reference=None,
        cluster_reference=Stub(ext_id=CLUSTER_EXT_ID),
    )

    result = SubnetMetadata.from_nutanix_subnet(subnet)  # type: ignore[arg-type]

    assert result.cluster_ext_id == CLUSTER_EXT_ID


def test_cluster_ext_id_attribute_wins_when_present():
    """Unreachable via the real SDK model - covered with a stub for the record."""
    subnet = Stub(
        ext_id=SUBNET_EXT_ID,
        name="vlan-100",
        description=None,
        subnet_type=None,
        network_id=None,
        ip_config=None,
        is_nat_enabled=None,
        is_external=None,
        vpc_reference=None,
        cluster_ext_id=CLUSTER_EXT_ID,
        cluster=Stub(ext_id="ignored"),
        cluster_reference="ignored",
    )

    result = SubnetMetadata.from_nutanix_subnet(subnet)  # type: ignore[arg-type]

    assert result.cluster_ext_id == CLUSTER_EXT_ID


def test_cluster_attribute_as_plain_string_is_used():
    """Unreachable via the real SDK model - covered with a stub for the record."""
    subnet = Stub(
        ext_id=SUBNET_EXT_ID,
        name="vlan-100",
        description=None,
        subnet_type=None,
        network_id=None,
        ip_config=None,
        is_nat_enabled=None,
        is_external=None,
        vpc_reference=None,
        cluster=CLUSTER_EXT_ID,
    )

    result = SubnetMetadata.from_nutanix_subnet(subnet)  # type: ignore[arg-type]

    assert result.cluster_ext_id == CLUSTER_EXT_ID
