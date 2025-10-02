from contextlib import asynccontextmanager

from fastapi import FastAPI

from nutanix_shim_server.clustermgmt import ClusterMgmt
from nutanix_shim_server.routes.clustermgmt import router as clustermgmt_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clustermgmt = ClusterMgmt()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(clustermgmt_router)
