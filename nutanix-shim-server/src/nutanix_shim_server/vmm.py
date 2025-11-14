from __future__ import annotations

import os
import datetime
import dataclasses
from typing import Self, cast
import ntnx_vmm_py_client as vmm

try:
    from IPython.terminal.embed import embed
except ImportError:

    def embed():
        pass


class VirtualMachineMgmt:
    config: vmm.Configuration

    def __init__(self):
        self.config = vmm.Configuration()
        self.config.host = os.environ["NUTANIX_HOST"]
        self.config.scheme = "https"
        self.config.set_api_key(os.environ["NUTANIX_API_KEY"])
        self.config.max_retry_attempts = 3
        self.config.backoff_factor = 3
        self.config.verify_ssl = False  # TODO: True
        self.config.port = os.environ.get("NUTANIX_PORT", 9440)

    @property
    def client(self) -> vmm.ApiClient:
        if not hasattr(self, "_client"):
            self._client = vmm.ApiClient(self.config)
            self._client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )
        return self._client

    @property
    def images_api(self) -> vmm.ImagesApi:
        if not hasattr(self, "_images_api"):
            self._images_api = vmm.ImagesApi(self.client)
        return self._images_api

    @property
    def vms_api(self) -> vmm.VmApi:
        if not hasattr(self, "_vms_api"):
            self._vms_api = vmm.VmApi(self.client)
        return self._vms_api

    def list_images(self) -> list[ImageMetadata]:
        # TODO: paginate
        resp: vmm.ListImagesApiResponse = self.images_api.list_images(_limit=100)  # type: ignore
        images: list[vmm.Image] = resp.data  # type: ignore
        return [ImageMetadata.from_nutanix_image(img) for img in images]

    def provision_vm(self, request: "VmProvisionRequest") -> "VmMetadata":
        """
        Provision a new VM with network (not image-based), CPU, memory, and disk configuration.

        Args:
            request: VM provisioning request with all required specifications

        Returns:
            VmMetadata with information about the created VM
        """
        # Create cluster reference
        cluster_ref = vmm.AhvConfigClusterReference(ext_id=request.cluster_ext_id)

        # Create network configuration with subnet reference and DHCP
        subnet_ref = vmm.SubnetReference(ext_id=request.subnet_ext_id)
        ipv4_config = vmm.Ipv4Config(should_assign_ip=True)  # Enable DHCP
        network_info = vmm.AhvConfigNicNetworkInfo(
            subnet=subnet_ref,
            ipv4_config=ipv4_config,
        )

        # Create NIC with VIRTIO emulation
        emulated_nic = vmm.EmulatedNic(
            model=vmm.EmulatedNicModel.VIRTIO,
            is_connected=True,
        )
        nic = vmm.AhvConfigNic(
            backing_info=emulated_nic,
            network_info=network_info,
        )

        # Create disk configuration (empty disk on storage container)
        storage_container = vmm.AhvConfigVmDiskContainerReference(
            ext_id=request.storage_container_ext_id
        )
        vm_disk = vmm.AhvConfigVmDisk(
            disk_size_bytes=request.disk_size_bytes,
            storage_container=storage_container,
        )
        disk_address = vmm.AhvConfigDiskAddress(
            bus_type=vmm.AhvConfigDiskBusType.SCSI,
            index=0,
        )
        disk = vmm.AhvConfigDisk(
            backing_info=vm_disk,
            disk_address=disk_address,
        )

        # Create VM specification
        vm_spec = vmm.AhvConfigVm(
            name=request.name,
            description=request.description,
            cluster=cluster_ref,
            num_sockets=request.num_sockets,
            num_cores_per_socket=request.num_cores_per_socket,
            memory_size_bytes=request.memory_size_bytes,
            nics=[nic],
            disks=[disk],
        )

        # Create the VM
        resp: vmm.CreateVmApiResponse = self.vms_api.create_vm(body=vm_spec)  # type: ignore
        vm: vmm.AhvConfigVm = resp.data.ext_id  # type: ignore

        # Return metadata about the created VM
        return VmMetadata(
            ext_id=cast(str, resp.data.ext_id),
            name=request.name,
            description=request.description,
            num_sockets=request.num_sockets,
            num_cores_per_socket=request.num_cores_per_socket,
            memory_size_bytes=request.memory_size_bytes,
            disk_size_bytes=request.disk_size_bytes,
        )


@dataclasses.dataclass(frozen=True)
class ImageMetadata:
    name: str
    description: None | str
    create_time: datetime.datetime
    last_update_time: datetime.datetime
    ext_id: str
    cluster_location_ext_ids: list[str]
    source: None | str
    placement_policy_status: None | str
    owner_ext_id: str
    tenant_id: None | str
    size_bytes: int
    type: str

    keys = __annotations__

    @classmethod
    def from_nutanix_image(cls, image: vmm.Image) -> Self:
        kwargs = {k: v for k, v in image.to_dict().items() if k in cls.keys}
        return cls(**kwargs)


@dataclasses.dataclass
class VmProvisionRequest:
    """
    Request model for provisioning a new VM.

    Example:
        {
            "name": "my-vm-01",
            "description": "Development VM for testing",
            "cluster_ext_id": "00061663-9fa0-28ca-185b-ac1f6b6f97e2",
            "subnet_ext_id": "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a",
            "storage_container_ext_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
            "num_sockets": 2,
            "num_cores_per_socket": 2,
            "memory_size_bytes": 8589934592,  # 8 GB
            "disk_size_bytes": 107374182400    # 100 GB
        }
    """

    name: str
    cluster_ext_id: str
    subnet_ext_id: str
    storage_container_ext_id: str
    num_sockets: int
    num_cores_per_socket: int
    memory_size_bytes: int
    disk_size_bytes: int
    description: str = ""


@dataclasses.dataclass(frozen=True)
class VmMetadata:
    """
    Response model containing information about a provisioned VM.
    """

    ext_id: str
    name: str
    description: str
    num_sockets: int
    num_cores_per_socket: int
    memory_size_bytes: int
    disk_size_bytes: int


if __name__ == "__main__":
    mgmt = VirtualMachineMgmt()
    images = mgmt.list_images()
