import logging
from functools import wraps

from fastapi import APIRouter, HTTPException, Request

from nutanix_shim_server.vmm import (
    ImageMetadata,
    PowerStateChangeRequest,
    VirtualMachineMgmt,
    VmDetailsMetadata,
    VmListMetadata,
    VmMetadata,
    VmPowerStateResponse,
    VmProvisionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vmm", tags=["Virtual Machine Management (VMM)"])


def handle_vm_not_found(func):
    """
    Decorator to handle 404 Not Found errors gracefully for VM operations.

    Catches ApiException with status 404 and converts it to a clean HTTPException.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if hasattr(e, "status") and e.status == 404:
                vm_id = kwargs.get("vm_id", "unknown")
                logger.warning(f"VM not found: {vm_id}")
                raise HTTPException(
                    status_code=404, detail=f"VM with ID '{vm_id}' not found"
                )
            raise

    return wrapper


@router.get(
    "/list-images",
    response_model=list[ImageMetadata],
)
def list_clusters(request: Request) -> list[ImageMetadata]:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.list_images()


@router.get(
    "/list-vms",
    response_model=list[VmListMetadata],
    summary="List all virtual machines",
    description="""
    Returns a list of all VMs in the Nutanix environment.

    Each VM entry includes:
    - External ID (ext_id) - unique identifier
    - Name
    - Cluster association (cluster_ext_id)
    - Power state (ON, OFF, PAUSED, etc.)
    - CPU configuration (sockets and cores per socket)
    - Memory size in bytes

    Example response:
    ```json
    [
        {
            "ext_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "name": "my-vm-01",
            "cluster_ext_id": "00061663-9fa0-28ca-185b-ac1f6b6f97e2",
            "power_state": "ON",
            "num_sockets": 2,
            "num_cores_per_socket": 2,
            "memory_size_bytes": 8589934592
        }
    ]
    ```
    """,
)
def list_vms(request: Request) -> list[VmListMetadata]:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.list_vms()


@router.get(
    "/vms/{vm_id}",
    response_model=VmDetailsMetadata,
    summary="Get VM details",
    description="""
    Returns detailed information about a specific VM including MAC address and IP addresses.

    The response includes:
    - Basic VM info (name, ext_id, cluster, power state)
    - CPU configuration (sockets and cores)
    - Memory size
    - MAC address of the first NIC
    - IP addresses assigned to the VM

    Example response:
    ```json
    {
        "ext_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "my-vm-01",
        "cluster_ext_id": "00061663-9fa0-28ca-185b-ac1f6b6f97e2",
        "power_state": "ON",
        "num_sockets": 2,
        "num_cores_per_socket": 2,
        "memory_size_bytes": 8589934592,
        "mac_address": "50:6b:8d:12:34:56",
        "ip_addresses": ["192.168.1.100"]
    }
    ```
    """,
)
@handle_vm_not_found
def get_vm_details(request: Request, vm_id: str) -> VmDetailsMetadata:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.get_vm_details(vm_id)


@router.post(
    "/provision-vm",
    response_model=VmMetadata,
    status_code=201,
    summary="Provision a new virtual machine",
    description="""
    Provisions a new VM using network-based configuration (not image-based).

    Configures:
    - Number of CPU sockets and cores per socket
    - Memory size in bytes
    - Disk size in bytes (creates an empty SCSI disk on the specified storage container)
    - Network connectivity via subnet with DHCP (VIRTIO NIC)
    - Optional description as metadata
    - Optional auto power-on with verification (default: true)

    Power-on behavior:
    - If `power_on` is true (default), the VM will be powered on after creation
    - The endpoint will wait up to 60 seconds to verify the VM reaches ON state
    - If power-on fails or times out, the VM will be automatically deleted and an error returned
    - If `power_on` is false, the VM will remain off after creation

    Example request:
    ```json
    {
        "name": "my-vm-01",
        "description": "Development VM for testing - Environment: dev, Owner: team-a",
        "cluster_ext_id": "00061663-9fa0-28ca-185b-ac1f6b6f97e2",
        "subnet_ext_id": "3d5d8e8b-f3e0-4f4e-8c5d-5b5c5d5e5f5a",
        "storage_container_ext_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "num_sockets": 2,
        "num_cores_per_socket": 2,
        "memory_size_bytes": 8589934592,
        "disk_size_bytes": 107374182400,
        "power_on": true
    }
    ```

    Returns the VM metadata including the external ID of the created VM.

    Errors:
    - 400: Invalid request parameters
    - 500: VM creation failed, or power-on failed (VM will be deleted automatically)
    """,
)
def provision_vm(request: Request, vm_request: VmProvisionRequest) -> VmMetadata:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.provision_vm(vm_request)


@router.get(
    "/vms/{vm_id}/power-state",
    response_model=VmPowerStateResponse,
    summary="Get VM power state",
    description="""
    Returns the current power state of a virtual machine.

    Power states:
    - **ON**: VM is powered on
    - **OFF**: VM is powered off
    - **PAUSED**: VM is paused
    - **UNDETERMINED**: Power state cannot be determined

    Example response:
    ```json
    {
        "ext_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "my-vm-01",
        "power_state": "ON"
    }
    ```
    """,
)
@handle_vm_not_found
def get_vm_power_state(request: Request, vm_id: str) -> VmPowerStateResponse:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.get_vm_power_state(vm_id)


@router.post(
    "/vms/{vm_id}/power-state",
    response_model=VmPowerStateResponse,
    summary="Change VM power state",
    description="""
    Change the power state of a virtual machine by performing a power action.

    Available actions:
    - **POWER_ON**: Turn on the VM (hard power on)
    - **POWER_OFF**: Turn off the VM (hard power off - immediate)
    - **SHUTDOWN**: Gracefully shut down the VM (requires guest tools)
    - **REBOOT**: Reboot the VM (hard reboot - immediate)
    - **RESET**: Reset the VM (hard reset/power cycle - immediate)

    Example request:
    ```json
    {
        "action": "POWER_ON"
    }
    ```

    Returns the updated power state after the action completes.

    Note: SHUTDOWN action requires Nutanix Guest Tools to be installed. If guest tools
    are not available, use POWER_OFF instead.
    """,
)
@handle_vm_not_found
def set_vm_power_state(
    request: Request, vm_id: str, power_request: PowerStateChangeRequest
) -> VmPowerStateResponse:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.set_vm_power_state(vm_id, power_request.action)


@router.delete(
    "/vms/{vm_id}",
    status_code=204,
    summary="Delete a virtual machine",
    description="""
    Permanently deletes a virtual machine.

    The VM must be powered off before deletion. If the VM is running, power it off first
    using the power-state endpoint with POWER_OFF action.

    **Warning**: This operation is irreversible. All VM data will be permanently deleted.

    Returns 204 No Content on success.
    """,
)
@handle_vm_not_found
def delete_vm(request: Request, vm_id: str) -> None:
    api: VirtualMachineMgmt = request.app.state.vmm
    api.delete_vm(vm_id)
