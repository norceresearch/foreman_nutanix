from contextlib import asynccontextmanager

from fastapi import FastAPI

from nutanix_shim_server.clustermgmt import ClusterMgmt, ClusterMetadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clustermgmt = ClusterMgmt()
    yield


app = FastAPI(lifespan=lifespan)


@app.get(
    "/api/v1/clustermgmt/list-clusters",
    response_model=list[ClusterMetadata],
    tags=["Cluster Management"],
)
def list_clusters() -> list[ClusterMetadata]:
    api: ClusterMgmt = app.state.clustermgmt
    return api.list_clusters()
