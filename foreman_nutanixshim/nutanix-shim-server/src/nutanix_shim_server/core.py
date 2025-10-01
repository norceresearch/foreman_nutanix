import os
from pprint import pprint
import ntnx_clustermgmt_py_client as clustermgmt
import ntnx_vmm_py_client as vmm


config = clustermgmt.Configuration()
config.host = os.environ["NUTANIX_HOST"]
config.scheme = "https"
config.set_api_key(os.environ["NUTANIX_API_KEY"])
config.max_retry_attempts = 3
config.backoff_factor = 3
config.verify_ssl = False  # TODO: True
config.port = os.environ.get("NUTANIX_PORT", 9440)

client = clustermgmt.ApiClient(config)
client.add_default_header(
    header_name="Accept-Encoding", header_value="gzip, deflate, br"
)


storage_instance = clustermgmt.StorageContainersApi(api_client=client)
# container_list = storage_instance.list_storage_containers()  # 404
clusters_api = clustermgmt.ClustersApi(api_client=client)
resp = clusters_api.list_clusters()


from IPython.terminal import embed

embed.embed()
