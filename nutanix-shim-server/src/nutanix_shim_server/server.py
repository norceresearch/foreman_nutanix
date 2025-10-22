from contextlib import asynccontextmanager

from fastapi import FastAPI

from nutanix_shim_server.clustermgmt import ClusterMgmt
from nutanix_shim_server.routes.clustermgmt import router as clustermgmt_router
from nutanix_shim_server.vmm import VirtualMachineMgmt
from nutanix_shim_server.routes.vmm import router as vmm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clustermgmt = ClusterMgmt()
    app.state.vmm = VirtualMachineMgmt()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(clustermgmt_router)
app.include_router(vmm_router)
