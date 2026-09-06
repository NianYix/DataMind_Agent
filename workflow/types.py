from __future__ import annotations

from typing import Any, TypedDict


MAX_WORKFLOW_NODES = 30
ALLOWED_NODE_TYPES = frozenset({"start", "analyze", "condition", "end"})


class NodeDict(TypedDict, total=False):
    id: str
    type: str
    config: dict[str, Any]


class EdgeDict(TypedDict, total=False):
    from_: str  # use "from" in JSON
    to: str
    when: str


GraphDict = dict[str, Any]
