from fastapi import APIRouter, Request
from nutanix_shim_server.clustermgmt import ClusterMgmt, ClusterMetadata

router = APIRouter(prefix="/api/v1/clustermgmt", tags=["Cluster Management"])


@router.get(
    "/list-clusters",
    response_model=list[ClusterMetadata],
    tags=["Cluster Management"],
)
def list_clusters(request: Request) -> list[ClusterMetadata]:
    api: ClusterMgmt = request.app.state.clustermgmt
    return api.list_clusters()
