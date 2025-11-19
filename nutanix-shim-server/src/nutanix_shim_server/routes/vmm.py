from fastapi import APIRouter, Request

from nutanix_shim_server.vmm import (
    VirtualMachineMgmt,
    ImageMetadata,
    VmListMetadata,
    VmProvisionRequest,
    VmMetadata,
    PowerStateChangeRequest,
    VmPowerStateResponse,
)

router = APIRouter(prefix="/api/v1/vmm", tags=["Virtual Machine Management (VMM)"])


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
        "disk_size_bytes": 107374182400
    }
    ```

    Returns the VM metadata including the external ID of the created VM.
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
def delete_vm(request: Request, vm_id: str) -> None:
    api: VirtualMachineMgmt = request.app.state.vmm
    api.delete_vm(vm_id)
