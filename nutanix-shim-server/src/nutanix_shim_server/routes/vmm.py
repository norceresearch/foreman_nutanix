from fastapi import APIRouter, Request

from nutanix_shim_server.vmm import (
    VirtualMachineMgmt,
    ImageMetadata,
    VmProvisionRequest,
    VmMetadata,
)

router = APIRouter(prefix="/api/v1/vmm", tags=["Virtual Machine Management (VMM)"])


@router.get(
    "/list-images",
    response_model=list[ImageMetadata],
)
def list_clusters(request: Request) -> list[ImageMetadata]:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.list_images()


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
