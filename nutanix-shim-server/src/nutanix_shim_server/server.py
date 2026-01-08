from __future__ import annotations

import ast
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from nutanix_shim_server.clustermgmt import ClusterMgmt
from nutanix_shim_server.networking import Networking
from nutanix_shim_server.routes.clustermgmt import router as clustermgmt_router
from nutanix_shim_server.routes.networking import router as networking_router
from nutanix_shim_server.routes.vmm import router as vmm_router
from nutanix_shim_server.vmm import VirtualMachineMgmt


@dataclass(frozen=True)
class Context:
    nutanix_host: str
    nutanix_host_scheme: str
    nutanix_host_verify_ssl: bool
    nutanix_api_key: str
    nutanix_host_port: int
    nutanix_client_certificate_file: None | str
    nutanix_root_ca_certificate_file: None | str
    nutanix_connect_timeout_secs: int
    nutanix_read_timeout_secs: int

    _vars = __annotations__

    @classmethod
    def from_env(cls):
        return cls(
            nutanix_host=os.environ["NUTANIX_HOST"],
            nutanix_api_key=os.environ["NUTANIX_API_KEY"],
            nutanix_host_scheme=cls.get_nutanix_host_scheme(),
            nutanix_host_verify_ssl=cls.get_nutanix_host_verify_ssl(),
            nutanix_host_port=cls.get_nutanix_host_port(),
            nutanix_client_certificate_file=cls.get_nutanix_client_certificate_file(),
            nutanix_root_ca_certificate_file=cls.get_nutanix_root_ca_certificate_file(),
            nutanix_connect_timeout_secs=cls.get_nutanix_connect_timeout_secs(),
            nutanix_read_timeout_secs=cls.get_nutanix_read_timeout_secs(),
        )

    @staticmethod
    def state_str() -> str:
        state = ""
        for attr in Context._vars:
            key = attr.upper()
            value = getattr(Context, f"get_{attr}")()
            if value is None:
                value = ""
            state += f"\n{key}={value}"
        return state

    @staticmethod
    def get_nutanix_host() -> None | str:
        return os.getenv("NUTANIX_HOST")

    @staticmethod
    def get_nutanix_api_key() -> None | str:
        return os.getenv("NUTANIX_API_KEY")

    @staticmethod
    def get_nutanix_host_scheme() -> str:
        return os.getenv("NUTANIX_HOST_SCHEME", "https")

    @staticmethod
    def get_nutanix_host_verify_ssl() -> bool:
        return ast.literal_eval(os.environ.get("NUTANIX_HOST_VERIFY_SSL", "True"))

    @staticmethod
    def get_nutanix_host_port() -> int:
        return int(os.environ.get("NUTANIX_HOST_PORT", 9440))

    @staticmethod
    def get_nutanix_client_certificate_file() -> None | str:
        return os.getenv("NUTANIX_CLIENT_CERTIFICATE_FILE")

    @staticmethod
    def get_nutanix_root_ca_certificate_file() -> None | str:
        return os.getenv("NUTANIX_ROOT_CA_CERTIFICATE_FILE")

    @staticmethod
    def get_nutanix_connect_timeout_secs() -> int:
        # Default 30s - same as SDK default
        return int(os.environ.get("NUTANIX_CONNECT_TIMEOUT_SECS", 30))

    @staticmethod
    def get_nutanix_read_timeout_secs() -> int:
        # Default 30s - same as SDK default
        return int(os.environ.get("NUTANIX_READ_TIMEOUT_SECS", 30))


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = Context.from_env()
    app.state.clustermgmt = ClusterMgmt(ctx)
    app.state.vmm = VirtualMachineMgmt(ctx)
    app.state.networking = Networking(ctx)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(clustermgmt_router)
app.include_router(vmm_router)
app.include_router(networking_router)
