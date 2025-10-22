from fastapi import APIRouter, Request

from nutanix_shim_server.vmm import VirtualMachineMgmt, ImageMetadata

router = APIRouter(prefix="/api/v1/vmm", tags=["Virtual Machine Management (VMM)"])


@router.get(
    "/list-images",
    response_model=list[ImageMetadata],
)
def list_clusters(request: Request) -> list[ImageMetadata]:
    api: VirtualMachineMgmt = request.app.state.vmm
    return api.list_images()
