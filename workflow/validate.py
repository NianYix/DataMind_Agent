from __future__ import annotations

from typing import Any

from workflow.types import ALLOWED_NODE_TYPES, MAX_WORKFLOW_NODES


def validate_graph(graph: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(graph, dict):
        return ["graph must be an object"]
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not nodes:
        errors.append("graph.nodes must be a non-empty list")
        return errors
    if len(nodes) > MAX_WORKFLOW_NODES:
        errors.append(f"too many nodes (max {MAX_WORKFLOW_NODES})")
    if not isinstance(edges, list):
        errors.append("graph.edges must be a list")
        edges = []

    ids: set[str] = set()
    starts = 0
    ends = 0
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{i}] must be an object")
            continue
        nid = str(node.get("id") or "").strip()
        ntype = str(node.get("type") or "").strip()
        if not nid:
            errors.append(f"nodes[{i}] missing id")
            continue
        if nid in ids:
            errors.append(f"duplicate node id: {nid}")
        ids.add(nid)
        if ntype not in ALLOWED_NODE_TYPES:
            errors.append(f"node {nid}: unknown type {ntype}")
        if ntype == "start":
            starts += 1
        if ntype == "end":
            ends += 1
        cfg = node.get("config")
        if cfg is not None and not isinstance(cfg, dict):
            errors.append(f"node {nid}: config must be an object")

    if starts != 1:
        errors.append(f"exactly one start node required (found {starts})")
    if ends < 1:
        errors.append("at least one end node required")

    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{i}] must be an object")
            continue
        frm = str(edge.get("from") or "").strip()
        to = str(edge.get("to") or "").strip()
        if frm not in ids:
            errors.append(f"edges[{i}].from unknown: {frm}")
        if to not in ids:
            errors.append(f"edges[{i}].to unknown: {to}")
        when = edge.get("when")
        if when is not None and str(when) not in {"true", "false"}:
            errors.append(f"edges[{i}].when must be true|false if set")

    return errors
