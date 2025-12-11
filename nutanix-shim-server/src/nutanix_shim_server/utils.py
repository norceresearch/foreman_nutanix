from typing import Callable, Concatenate, TypeVar

from ntnx_vmm_py_client import ApiResponseMetadata

ResponseType = TypeVar("ResponseType")
Page = TypeVar("Page", bound="int")
Kwargs = TypeVar("Kwargs", bound=dict)
T = TypeVar("T")


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
