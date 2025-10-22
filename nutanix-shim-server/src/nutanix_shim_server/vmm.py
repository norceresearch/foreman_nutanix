from __future__ import annotations

import os
import datetime
import dataclasses
from typing import Self, cast
import ntnx_vmm_py_client as vmm

try:
    from IPython.terminal.embed import embed
except ImportError:

    def embed():
        pass


class VirtualMachineMgmt:
    config: vmm.Configuration

    def __init__(self):
        self.config = vmm.Configuration()
        self.config.host = os.environ["NUTANIX_HOST"]
        self.config.scheme = "https"
        self.config.set_api_key(os.environ["NUTANIX_API_KEY"])
        self.config.max_retry_attempts = 3
        self.config.backoff_factor = 3
        self.config.verify_ssl = False  # TODO: True
        self.config.port = os.environ.get("NUTANIX_PORT", 9440)

    @property
    def client(self) -> vmm.ApiClient:
        if not hasattr(self, "_client"):
            self._client = vmm.ApiClient(self.config)
            self._client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )
        return self._client

    @property
    def images_api(self) -> vmm.ImagesApi:
        if not hasattr(self, "_images_api"):
            self._images_api = vmm.ImagesApi(self.client)
        return self._images_api

    def list_images(self) -> list[ImageMetadata]:
        # TODO: paginate
        resp: vmm.ListImagesApiResponse = self.images_api.list_images(_limit=100)  # type: ignore
        images: list[vmm.Image] = resp.data  # type: ignore
        return [ImageMetadata.from_nutanix_image(img) for img in images]


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


if __name__ == "__main__":
    mgmt = VirtualMachineMgmt()
    images = mgmt.list_images()
