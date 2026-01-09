import functools
import logging
from typing import TYPE_CHECKING, Callable, Concatenate, TypeVar

from ntnx_vmm_py_client import ApiResponseMetadata
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

if TYPE_CHECKING:
    from nutanix_shim_server.server import Context

logger = logging.getLogger(__name__)

ResponseType = TypeVar("ResponseType")
Page = TypeVar("Page", bound="int")
Kwargs = TypeVar("Kwargs", bound=dict)
T = TypeVar("T")


def configure_sdk(config, ctx: "Context") -> None:
    """Configure a Nutanix SDK Configuration object from Context.

    All Nutanix SDK packages (vmm, networking, clustermgmt, prism) use the same
    Configuration interface, so this works for any of them.
    """
    config.host = ctx.nutanix_host
    config.scheme = ctx.nutanix_host_scheme
    config.set_api_key(ctx.nutanix_api_key)
    config.max_retry_attempts = 3
    config.backoff_factor = 3
    config.verify_ssl = ctx.nutanix_host_verify_ssl
    config.port = ctx.nutanix_host_port
    config.client_certificate_file = ctx.nutanix_client_certificate_file
    config.root_ca_certificate_file = ctx.nutanix_root_ca_certificate_file
    config.connect_timeout = ctx.nutanix_connect_timeout_secs * 1000
    config.read_timeout = ctx.nutanix_read_timeout_secs * 1000


def add_default_headers(client) -> None:
    """Add default headers to a Nutanix SDK ApiClient."""
    client.add_default_header(
        header_name="Accept-Encoding", header_value="gzip, deflate, br"
    )


def retry_on_timeout(func):
    """Decorator that retries once with a fresh client on read timeout.

    On ReadTimeoutError or MaxRetryError, clears cached clients by calling
    the instance's _clear_clients() method (if it exists), then retries once.

    This helps recover from stale connection pool issues.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (ReadTimeoutError, MaxRetryError) as e:
            logger.warning(
                f"Timeout in {func.__name__}, clearing clients and retrying: {e}"
            )
            if hasattr(self, "_clear_clients"):
                self._clear_clients()
            return func(self, *args, **kwargs)

    return wrapper


def paginate(op: Callable[Concatenate[...], ResponseType], **kwargs) -> list[object]:
    """
    Paginate a Nutanix `list_*` method from an API.

    These methods typically take a 'page' and other args but always return a
    `.metadata` of type `ApiResponseMetadata` which says something about the
    end of pagination thru links or total results. This function handles the
    pagination of these calls by checking metadata from the responses.

    Parameters
    ----------
    op: callable
        The `list_*` method, ie vmm.VmApi(...).list_vms
    kwargs:
        Any kwargs to pass to each call, will set the '_page' parameter in this call.

    Returns
    -------
    list[T]
        Where T is the response.data item type.
    """
    page: int = 0
    collection = []
    kwargs = kwargs if kwargs else {}

    if "_limit" not in kwargs:
        kwargs["_limit"] = 100

    while True:
        kwargs["_page"] = page
        resp = op(**kwargs)

        if resp.data:  # type: ignore
            collection.extend(resp.data)  # type: ignore
        else:
            break

        metadata: None | ApiResponseMetadata = resp.metadata  # type: ignore
        if metadata:
            links = {link.rel: link.href for link in metadata.links or []}
            if not links or links.get("self") == links.get("last"):
                break
        else:
            break

        page += 1
    return collection
