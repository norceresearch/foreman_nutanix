"""Tests for utils.paginate.

Termination is fragile by design in the current implementation: the loop only
stops on an explicit ``self == last`` link, on falsy ``resp.data``, or on
absent metadata/links. There is no page cap. These tests pin that behaviour,
including the case where a ``last`` link is missing and pagination therefore
runs until the server happens to return an empty page.
"""

from __future__ import annotations

import pytest
from nutanix_shim_server.utils import paginate

from .conftest import Link, Meta, Resp


class FakePagedOp:
    """A fake ``list_*`` callable that hands back a canned response per page.

    Records every kwargs dict it was called with so tests can assert on the
    ``_page``/``_limit`` parameters paginate injects.
    """

    def __init__(self, responses: list[Resp]):
        self._responses = responses
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        page = kwargs["_page"]
        if page >= len(self._responses):
            raise AssertionError(
                f"paginate asked for page {page}; only "
                f"{len(self._responses)} page(s) were configured "
                "(runaway pagination)"
            )
        return self._responses[page]


def _links(self_href: str, last_href: str | None) -> Meta:
    links = [Link("self", self_href)]
    if last_href is not None:
        links.append(Link("last", last_href))
    return Meta(links=links)


def test_multi_page_accumulates_in_order():
    op = FakePagedOp(
        [
            Resp(["a", "b"], _links("?page=0", "?page=2")),
            Resp(["c", "d"], _links("?page=1", "?page=2")),
            Resp(["e"], _links("?page=2", "?page=2")),
        ]
    )

    assert paginate(op) == ["a", "b", "c", "d", "e"]
    assert [c["_page"] for c in op.calls] == [0, 1, 2]


def test_single_page_stops_when_self_equals_last():
    op = FakePagedOp([Resp(["only"], _links("?page=0", "?page=0"))])

    assert paginate(op) == ["only"]
    assert len(op.calls) == 1


def test_empty_first_page_returns_empty_list():
    op = FakePagedOp([Resp([], _links("?page=0", "?page=9"))])

    assert paginate(op) == []
    # Metadata is never consulted: the falsy-data break wins first.
    assert len(op.calls) == 1


def test_data_none_is_treated_as_end_of_pagination():
    op = FakePagedOp([Resp(None, _links("?page=0", "?page=9"))])

    assert paginate(op) == []
    assert len(op.calls) == 1


def test_missing_last_link_paginates_until_data_runs_out():
    """No ``last`` link => ``links.get("last")`` is None, never equal to
    ``self``, so the only brake left is an empty data page."""
    op = FakePagedOp(
        [
            Resp(["a"], _links("?page=0", None)),
            Resp(["b"], _links("?page=1", None)),
            Resp([], _links("?page=2", None)),
        ]
    )

    assert paginate(op) == ["a", "b"]
    assert len(op.calls) == 3


def test_missing_last_link_and_never_empty_page_runs_away():
    """Documents the missing page cap: a server that keeps returning data
    without a ``last`` link is paged forever."""
    op = FakePagedOp([Resp(["x"], _links("?page=0", None))] * 4)

    with pytest.raises(AssertionError, match="runaway pagination"):
        paginate(op)
    # All four configured pages were consumed and a fifth was still requested.
    assert len(op.calls) == 5


def test_no_metadata_stops_after_first_page():
    op = FakePagedOp([Resp(["a"], None)])

    assert paginate(op) == ["a"]
    assert len(op.calls) == 1


def test_empty_links_list_stops_after_first_page():
    op = FakePagedOp([Resp(["a"], Meta(links=[]))])

    assert paginate(op) == ["a"]
    assert len(op.calls) == 1


def test_links_none_stops_after_first_page():
    op = FakePagedOp([Resp(["a"], Meta(links=None))])

    assert paginate(op) == ["a"]
    assert len(op.calls) == 1


def test_default_limit_is_injected():
    op = FakePagedOp([Resp(["a"], _links("?page=0", "?page=0"))])

    paginate(op)

    assert op.calls[0]["_limit"] == 100


def test_caller_limit_and_extra_kwargs_are_forwarded_to_every_call():
    op = FakePagedOp(
        [
            Resp(["a"], _links("?page=0", "?page=1")),
            Resp(["b"], _links("?page=1", "?page=1")),
        ]
    )

    paginate(op, _limit=5, clusterExtId="cluster-1")

    assert [c["_limit"] for c in op.calls] == [5, 5]
    assert [c["clusterExtId"] for c in op.calls] == ["cluster-1", "cluster-1"]
