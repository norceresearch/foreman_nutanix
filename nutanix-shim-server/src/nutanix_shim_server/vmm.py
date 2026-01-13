from __future__ import annotations

import dataclasses
import datetime
import enum
import logging
import time
from typing import Literal, Self, cast

import ntnx_prism_py_client as prism
import ntnx_vmm_py_client as vmm
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.ADSFVolumeGroupReference import (
    ADSFVolumeGroupReference,
)
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Disk import Disk
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.Nic import Nic
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.NicNetworkInfo import (
    NicNetworkInfo,
)
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.SubnetReference import (
    SubnetReference,
)
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.VmDisk import (
    VmDisk,
    VmDiskContainerReference,
)

from nutanix_shim_server import server
from nutanix_shim_server.utils import (
    add_default_headers,
    configure_sdk,
    paginate,
    retry_on_timeout,
)

logger = logging.getLogger(__name__)


class VirtualMachineMgmt:
    config: vmm.Configuration

    def __init__(self, ctx: server.Context):
        self.config = vmm.Configuration()
        configure_sdk(self.config, ctx)

        # Prism config for task polling
        self.prism_config = prism.Configuration()
        configure_sdk(self.prism_config, ctx)

    def _clear_clients(self) -> None:
        """Clear cached clients to force re-creation on next access."""
        if hasattr(self, "_client"):
            del self._client
        if hasattr(self, "_prism_client"):
            del self._prism_client
        if hasattr(self, "_tasks_api"):
            del self._tasks_api
        if hasattr(self, "_images_api"):
            del self._images_api
        if hasattr(self, "_vms_api"):
            del self._vms_api

    @property
    def client(self) -> vmm.ApiClient:
        if not hasattr(self, "_client"):
            self._client = vmm.ApiClient(self.config)
            add_default_headers(self._client)
        return self._client

    @property
    def prism_client(self) -> prism.ApiClient:
        if not hasattr(self, "_prism_client"):
            self._prism_client = prism.ApiClient(self.prism_config)
            add_default_headers(self._prism_client)
        return self._prism_client

    @property
    def tasks_api(self) -> prism.TasksApi:
        if not hasattr(self, "_tasks_api"):
            self._tasks_api = prism.TasksApi(self.prism_client)
        return self._tasks_api

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

    @retry_on_timeout
    def list_images(self) -> list[ImageMetadata]:
        images: list[vmm.Image] = paginate(self.images_api.list_images)
        return [ImageMetadata.from_nutanix_image(img) for img in images]

    @retry_on_timeout
    def list_vms(self) -> list["VmListMetadata"]:
        """List all VMs in the Nutanix environment"""
        data: list[vmm.AhvConfigVm] = paginate(self.vms_api.list_vms)
        vms = [VmListMetadata.from_nutanix_vm(vm) for vm in data]
        return vms

    @retry_on_timeout
    def get_vm_details(self, vm_ext_id: str) -> "VmDetailsMetadata":
        """
        Get detailed information about a VM including MAC address and IP addresses.

        Parameters
        ----------
            vm_ext_id: The external ID of the VM

        Returns
        -------
            VmDetailsMetadata with full VM details
        """
        resp: vmm.AhvConfigGetVmApiResponse = self.vms_api.get_vm_by_id(extId=vm_ext_id)  # type: ignore
        vm: vmm.AhvConfigVm = resp.data  # type: ignore
        return VmDetailsMetadata.from_nutanix_vm(vm)

    @retry_on_timeout
    def get_vm_power_state(self, vm_ext_id: str) -> "VmPowerStateResponse":
        """
        Get the current power state of a VM.

        Parameters
        ----------
            vm_ext_id: The external ID of the VM

        Returns
        -------
            VmPowerStateResponse with the current power state
        """
        resp: vmm.AhvConfigGetVmApiResponse = self.vms_api.get_vm_by_id(extId=vm_ext_id)  # type: ignore
        vm: vmm.AhvConfigVm = resp.data  # type: ignore
        power_state = str(vm.power_state) if vm.power_state else "UNDETERMINED"
        return VmPowerStateResponse(
            ext_id=vm_ext_id,
            name=cast(str, vm.name),
            power_state=power_state,
        )

    @retry_on_timeout
    def set_vm_power_state(
        self, vm_ext_id: str, action: "PowerAction"
    ) -> "VmPowerStateResponse":
        """
        Change the power state of a VM.

        Parameters
        ----------
            vm_ext_id: The external ID of the VM
            action: The power action to perform

        Returns
        -------
        VmPowerStateResponse
            with the new power state
        """
        # Fetch VM to get ETag (required for all power state operations)
        get_resp = self.vms_api.get_vm_by_id(extId=vm_ext_id)
        etag = self.client.get_etag(get_resp)

        # Perform the requested power action with ETag
        if action == PowerAction.POWER_ON:
            self.vms_api.power_on_vm(extId=vm_ext_id, if_match=etag)
        elif action == PowerAction.POWER_OFF:
            self.vms_api.power_off_vm(extId=vm_ext_id, if_match=etag)
        elif action == PowerAction.SHUTDOWN:
            self.vms_api.shutdown_vm(extId=vm_ext_id, if_match=etag)
        elif action == PowerAction.REBOOT:
            self.vms_api.reboot_vm(extId=vm_ext_id, if_match=etag)
        elif action == PowerAction.RESET:
            self.vms_api.reset_vm(extId=vm_ext_id, if_match=etag)
        else:
            raise ValueError(f"Unknown power action: {action}")

        return self.get_vm_power_state(vm_ext_id)

    @retry_on_timeout
    def delete_vm(self, vm_ext_id: str) -> None:
        """
        Delete a virtual machine.

        Parameters
        ----------
            vm_ext_id: The external ID of the VM to delete

        Raises
        ------
            ApiException: If the VM cannot be deleted
        """
        # First fetch the VM to get its ETag (required for deletion)
        get_resp = self.vms_api.get_vm_by_id(extId=vm_ext_id)
        etag = self.client.get_etag(get_resp)

        # Delete with the ETag header
        self.vms_api.delete_vm_by_id(extId=vm_ext_id, if_match=etag)

    @retry_on_timeout
    def provision_vm(self, request: "VmProvisionRequest") -> "VmMetadata":
        """
        Provision a new VM with network (not image-based), CPU, memory, and disk configuration.

        Parameters
        ----------
            request: VM provisioning request with all required specifications

        Returns
        -------
        VmMetadata
            with information about the created VM
        """
        # TODO: This method is wildly too large

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

        if request.boot_method == "bios":
            boot_config = vmm.LegacyBoot()
        else:
            boot_config = vmm.UefiBoot(is_secure_boot_enabled=request.secure_boot)

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
            boot_config=boot_config,
        )

        # Create the VM - this returns a task reference, not the VM directly
        resp: vmm.CreateVmApiResponse = self.vms_api.create_vm(body=vm_spec)  # type: ignore

        # Get task ID - keep the full format including prefix for the tasks API
        task_ext_id = cast(str, resp.data.ext_id)  # type: ignore

        logger.info(f"Waiting for VM creation task {task_ext_id} to complete...")

        # Poll for task completion
        max_wait_seconds = 120
        poll_interval = 2
        elapsed = 0

        while elapsed < max_wait_seconds:
            task_resp = self.tasks_api.get_task_by_id(extId=task_ext_id)
            task = task_resp.data  # type: ignore
            status = str(task.status) if task.status else "UNKNOWN"

            logger.info(f"Task status: {status}")

            if status == "SUCCEEDED":
                # Extract VM ext_id from entities_affected
                if task.entities_affected:
                    for entity in task.entities_affected:
                        # The VM entity will have the ext_id we need
                        vm_ext_id = entity.ext_id
                        logger.info(f"VM created successfully with ext_id: {vm_ext_id}")

                        # Note: Power-on is handled separately by Foreman after
                        # orchestration completes, not during provisioning.
                        # Use the set_vm_power_state endpoint to power on the VM.

                        return VmMetadata(
                            ext_id=vm_ext_id,
                            name=request.name,
                            description=request.description,
                            num_sockets=request.num_sockets,
                            num_cores_per_socket=request.num_cores_per_socket,
                            memory_size_bytes=request.memory_size_bytes,
                            disk_size_bytes=request.disk_size_bytes,
                        )

                raise ValueError("Task succeeded but no VM entity found in response")

            elif status == "FAILED":
                error_msg = (
                    task.error_messages
                    if hasattr(task, "error_messages")
                    else "Unknown error"
                )
                raise ValueError(f"VM creation task failed: {error_msg}")

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"VM creation task did not complete within {max_wait_seconds} seconds"
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


@dataclasses.dataclass(frozen=True)
class VmListMetadata:
    """
    Metadata for listing VMs.

    Contains essential information about VMs for display in Foreman.
    """

    ext_id: str
    name: str
    description: None | str
    cluster_ext_id: None | str
    power_state: None | str
    num_sockets: None | int
    num_cores_per_socket: None | int
    memory_size_bytes: None | int
    mac_address: None | str
    ip_addresses: list[str]
    create_time: None | datetime.datetime
    disk_size_bytes: None | int

    @classmethod
    def from_nutanix_vm(cls, vm: vmm.AhvConfigVm) -> Self:
        """Convert Nutanix SDK VM to our response model"""
        # Extract cluster ext_id from cluster reference
        cluster_ext_id = None
        if hasattr(vm, "cluster") and vm.cluster:
            cluster_ext_id = (
                vm.cluster.ext_id if hasattr(vm.cluster, "ext_id") else None
            )

        power_state = str(vm.power_state) if vm.power_state else None

        # Extract MAC address from first NIC
        mac_address = None
        ip_addresses = []
        if hasattr(vm, "nics") and vm.nics:
            first_nic = vm.nics[0]
            if hasattr(first_nic, "backing_info") and first_nic.backing_info:
                mac_address = getattr(first_nic.backing_info, "mac_address", None)

            # Extract IP addresses from NIC network info
            if hasattr(first_nic, "network_info") and first_nic.network_info:
                ipv4_config = getattr(first_nic.network_info, "ipv4_config", None)
                if ipv4_config and hasattr(ipv4_config, "ip_address"):
                    ip_addr = ipv4_config.ip_address
                    if ip_addr and hasattr(ip_addr, "value"):
                        ip_addresses.append(ip_addr.value)

        disk_sizes = _disk_sizes_bytes_from_disks(vm.disks or [])
        disk_size_bytes = disk_sizes[0] if disk_sizes else None

        description = cast(str, vm.description)

        return cls(
            ext_id=cast(str, vm.ext_id),
            name=cast(str, vm.name),
            description=description,
            cluster_ext_id=cluster_ext_id,
            power_state=power_state,
            num_sockets=vm.num_sockets,
            num_cores_per_socket=vm.num_cores_per_socket,
            memory_size_bytes=vm.memory_size_bytes,
            mac_address=mac_address,
            ip_addresses=ip_addresses,
            create_time=vm.create_time if hasattr(vm, "create_time") else None,
            disk_size_bytes=disk_size_bytes,
        )


@dataclasses.dataclass(frozen=True)
class VmDetailsMetadata:
    """
    Detailed metadata for a single VM.

    Contains all information needed for Foreman host details view.
    """

    ext_id: str
    name: str
    description: None | str
    cluster_ext_id: None | str
    power_state: None | str
    network_id: None | str
    num_sockets: None | int
    num_cores_per_socket: None | int
    memory_size_bytes: None | int
    mac_address: None | str
    ip_addresses: list[str]
    create_time: None | datetime.datetime
    boot_method: None | str
    secure_boot: None | bool
    gpus: None | list[str]
    disk_size_bytes: None | int
    container_id: None | str

    @classmethod
    def from_nutanix_vm(cls, vm: vmm.AhvConfigVm) -> Self:
        """Convert Nutanix SDK VM to our detailed response model"""
        # Extract cluster ext_id from cluster reference
        cluster_ext_id = None
        if hasattr(vm, "cluster") and vm.cluster:
            cluster_ext_id = (
                vm.cluster.ext_id if hasattr(vm.cluster, "ext_id") else None
            )

        # Convert power state enum to string
        power_state = str(vm.power_state) if vm.power_state else None

        # Convert boot config to the boot method
        secure_boot = None
        if isinstance(vm.boot_config, vmm.UefiBoot):
            boot_method = "uefi"
            secure_boot = vm.boot_config.is_secure_boot_enabled
        elif isinstance(vm.boot_config, vmm.LegacyBoot):
            boot_method = "bios"
        else:
            boot_method = f"{type(vm.boot_config)}"

        # Extract MAC address from first NIC
        mac_address = None
        ip_addresses = []
        if hasattr(vm, "nics") and vm.nics:
            first_nic = vm.nics[0]
            if hasattr(first_nic, "backing_info") and first_nic.backing_info:
                mac_address = getattr(first_nic.backing_info, "mac_address", None)
            # Extract IP addresses from NIC network info
            if hasattr(first_nic, "network_info") and first_nic.network_info:
                ipv4_config = getattr(first_nic.network_info, "ipv4_config", None)
                if ipv4_config and hasattr(ipv4_config, "ip_address"):
                    ip_addr = ipv4_config.ip_address
                    if ip_addr and hasattr(ip_addr, "value"):
                        ip_addresses.append(ip_addr.value)

        # Initial info about GPUs (if any)
        gpus: list[str] = []
        gpu: vmm.Gpu
        for gpu in vm.gpus or []:
            gpus.append(str(gpu.device_id or "unknown device id"))

        # Get boot disk size
        # TODO: Can potentially be more than one disk - right now we assume one
        #       since ability to add more is not implemented.
        disk_sizes = _disk_sizes_bytes_from_disks(vm.disks or [])
        disk_size_bytes = disk_sizes[0] if disk_sizes else None

        # Network
        network_id = None
        nic: Nic
        for nic in vm.nics or []:
            network_id = nic.ext_id
            network_info: NicNetworkInfo | None = nic.network_info
            if isinstance(network_info, NicNetworkInfo):
                subnet: SubnetReference | None = network_info.subnet
                if isinstance(subnet, SubnetReference):
                    network_id = subnet.ext_id
                    break

        # Storage container
        container_id = None
        if vm.disks:
            disk: Disk = vm.disks[0]
            if ref := _disk_container_ref_from_disk(disk):
                container_id = ref.ext_id

        return cls(
            ext_id=cast(str, vm.ext_id),
            name=cast(str, vm.name),
            description=cast(str, vm.description),
            cluster_ext_id=cluster_ext_id,
            power_state=power_state,
            network_id=network_id,
            num_sockets=vm.num_sockets,
            num_cores_per_socket=vm.num_cores_per_socket,
            memory_size_bytes=vm.memory_size_bytes,
            mac_address=mac_address,
            ip_addresses=ip_addresses,
            create_time=vm.create_time if hasattr(vm, "create_time") else None,
            boot_method=boot_method,
            secure_boot=secure_boot,
            gpus=[g.device_id for g in vm.gpus or []],
            disk_size_bytes=disk_size_bytes,
            container_id=container_id,
        )


def _disk_container_ref_from_disk(disk: Disk) -> VmDiskContainerReference | None:
    info: None | VmDisk | ADSFVolumeGroupReference = disk.backing_info
    if isinstance(info, VmDisk):
        return cast(VmDiskContainerReference, info.storage_container)


def _disk_sizes_bytes_from_disks(disks: list[Disk]) -> list[int | None]:
    disk: Disk
    sizes = []
    for disk in disks:
        info: None | VmDisk | ADSFVolumeGroupReference = disk.backing_info
        if isinstance(info, VmDisk):
            sizes.append(info.disk_size_bytes)
        else:
            sizes.append(None)
    return sizes


@dataclasses.dataclass
class VmProvisionRequest:
    """
    Request model for provisioning a new VM.

    Note: VMs are always created in OFF state. Power-on is handled separately
    by calling the set_vm_power_state endpoint after Foreman orchestration completes.

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
            "disk_size_bytes": 107374182400,   # 100 GB
            "boot_method": "uefi",             # uefi | bios
            "secure_boot": true,               # secure boot conf - applicable only to UEFI
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
    boot_method: Literal["bios", "uefi"] = "uefi"
    secure_boot: bool = False


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


class PowerAction(str, enum.Enum):
    """
    Available power actions for VMs.

    - POWER_ON: Turn on the VM (hard power on)
    - POWER_OFF: Turn off the VM (hard power off)
    - SHUTDOWN: Gracefully shut down the VM
    - REBOOT: Reboot the VM (hard reboot)
    - RESET: Reset the VM (hard reset/power cycle)
    """

    POWER_ON = "POWER_ON"
    POWER_OFF = "POWER_OFF"
    SHUTDOWN = "SHUTDOWN"
    REBOOT = "REBOOT"
    RESET = "RESET"


@dataclasses.dataclass
class PowerStateChangeRequest:
    """
    Request model for changing VM power state.

    Example:
        {
            "action": "POWER_ON"
        }
    """

    action: PowerAction


@dataclasses.dataclass(frozen=True)
class VmPowerStateResponse:
    """
    Response model containing VM power state information.

    Power states:
    - ON: VM is powered on
    - OFF: VM is powered off
    - PAUSED: VM is paused
    - UNDETERMINED: Power state cannot be determined
    """

    ext_id: str
    name: str
    power_state: str
