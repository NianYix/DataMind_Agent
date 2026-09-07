from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from server.core.config import get_settings
from server.models import Dataset
from server.services.dataset_service import get_dataset


@dataclass
class DatasetSource:
    id: str
    alias: str  # data | data_2 | …
    frame: str  # df | df_2 | …
    path: str
    source_type: str
    table_name: str | None = None
    connection_id: str | None = None
    name: str = ""
    row_count: int = 0
    col_count: int = 0
    profile: dict[str, Any] | None = None


@dataclass
class DatasetBinding:
    primary_id: str
    dataset_ids: list[str]
    sources: list[DatasetSource] = field(default_factory=list)


def alias_for_index(i: int) -> str:
    """0-based index in ordered list after primary is at 0 → data, data_2, …"""
    if i <= 0:
        return "data"
    return f"data_{i + 1}"


def frame_for_alias(alias: str) -> str:
    if alias == "data":
        return "df"
    if alias.startswith("data_"):
        return f"df_{alias.split('_', 1)[1]}"
    return "df"


def normalize_dataset_ids(
    *,
    dataset_id: str | None = None,
    dataset_ids: list[str] | None = None,
    primary_dataset_id: str | None = None,
    max_n: int | None = None,
) -> tuple[list[str], str]:
    """Return (ordered_ids with primary first, primary_id)."""
    settings = get_settings()
    limit = max_n if max_n is not None else int(settings.max_datasets_per_conversation)

    raw: list[str] = []
    if dataset_ids:
        raw.extend([str(x).strip() for x in dataset_ids if str(x).strip()])
    elif dataset_id:
        raw.append(str(dataset_id).strip())

    if not raw:
        raise HTTPException(status_code=400, detail="dataset_id or dataset_ids is required")

    seen: set[str] = set()
    ordered: list[str] = []
    for x in raw:
        if x not in seen:
            seen.add(x)
            ordered.append(x)

    if len(ordered) > limit:
        raise HTTPException(
            status_code=400,
            detail=f"At most {limit} datasets per conversation",
        )

    primary = (primary_dataset_id or dataset_id or ordered[0]).strip()
    if primary not in ordered:
        raise HTTPException(status_code=400, detail="primary_dataset_id must be in dataset_ids")

    rest = [x for x in ordered if x != primary]
    return [primary, *rest], primary


def validate_workspace_datasets(db: Session, workspace_id: str, dataset_ids: list[str]) -> list[Dataset]:
    rows: list[Dataset] = []
    for did in dataset_ids:
        ds = get_dataset(db, did)
        if ds.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail=f"Dataset not in workspace: {did}")
        rows.append(ds)
    return rows


def build_sources(datasets: list[Dataset]) -> list[DatasetSource]:
    """datasets[0] is primary → alias data / df."""
    sources: list[DatasetSource] = []
    for i, ds in enumerate(datasets):
        alias = alias_for_index(i)
        st = getattr(ds, "source_type", None) or "file"
        sources.append(
            DatasetSource(
                id=ds.id,
                alias=alias,
                frame=frame_for_alias(alias),
                path=ds.file_path,
                source_type=st,
                table_name=getattr(ds, "table_name", None),
                connection_id=getattr(ds, "connection_id", None),
                name=ds.name or alias,
                row_count=int(ds.row_count or 0),
                col_count=int(ds.col_count or 0),
                profile=ds.profile_json if isinstance(ds.profile_json, dict) else None,
            )
        )
    return sources


def resolve_binding(
    db: Session,
    workspace_id: str,
    *,
    dataset_id: str | None = None,
    dataset_ids: list[str] | None = None,
    primary_dataset_id: str | None = None,
) -> DatasetBinding:
    ids, primary = normalize_dataset_ids(
        dataset_id=dataset_id,
        dataset_ids=dataset_ids,
        primary_dataset_id=primary_dataset_id,
    )
    datasets = validate_workspace_datasets(db, workspace_id, ids)
    # reorder ORM rows to match ids order
    by_id = {d.id: d for d in datasets}
    ordered = [by_id[i] for i in ids]
    return DatasetBinding(primary_id=primary, dataset_ids=ids, sources=build_sources(ordered))


def sources_to_dicts(sources: list[DatasetSource]) -> list[dict[str, Any]]:
    return [
        {
            "id": s.id,
            "alias": s.alias,
            "frame": s.frame,
            "path": s.path,
            "source_type": s.source_type,
            "table_name": s.table_name,
            "connection_id": s.connection_id,
            "name": s.name,
            "row_count": s.row_count,
            "col_count": s.col_count,
            "profile": s.profile,
        }
        for s in sources
    ]


def format_datasets_prompt(sources: list[DatasetSource] | list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    lines: list[str] = []
    if len(sources) == 1:
        return ""
    lines.append("Multiple datasets are bound for this run. Use these aliases:")
    lines.append("SQL tables: data (primary), data_2, … | Python: df (primary), df_2, …")
    for s in sources:
        if isinstance(s, dict):
            alias = s.get("alias", "data")
            name = s.get("name") or alias
            rows = s.get("row_count") or 0
            cols = s.get("col_count") or 0
            profile = s.get("profile") or {}
            fields = profile.get("fields") or []
        else:
            alias = s.alias
            name = s.name or alias
            rows = s.row_count
            cols = s.col_count
            profile = s.profile or {}
            fields = profile.get("fields") or []
        field_bits = []
        for f in fields[:24]:
            fname = f.get("name") if isinstance(f, dict) else None
            ftype = (f.get("inferred_type") or f.get("type")) if isinstance(f, dict) else None
            if fname:
                field_bits.append(f"{fname}:{ftype or '?'}")
        lines.append(
            f"- {alias} / {frame_for_alias(alias)} · {name} · {rows}×{cols}"
            + (f" · fields[{', '.join(field_bits)}]" if field_bits else "")
        )
    lines.append("Join or compare across tables when the question needs it.")
    return "\n".join(lines)


def conversation_binding_fields(conv: Any) -> tuple[list[str], str | None]:
    primary = getattr(conv, "dataset_id", None)
    ctx = getattr(conv, "context_json", None) or {}
    ids = ctx.get("dataset_ids") if isinstance(ctx, dict) else None
    if isinstance(ids, list) and ids:
        clean = [str(x) for x in ids if x]
        if primary and primary not in clean:
            clean = [primary, *clean]
        elif primary and clean and clean[0] != primary:
            clean = [primary, *[x for x in clean if x != primary]]
        return clean, primary
    if primary:
        return [primary], primary
    return [], None


def assert_sources_sandboxable(sources: list[DatasetSource]) -> None:
    """Multi-source DuckDB path requires local file/sqlite datasets."""
    if len(sources) <= 1:
        return
    for s in sources:
        if s.source_type in {"mysql", "postgresql", "mock"} or str(s.path).startswith("remote://"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Multi-dataset runs currently support file/sqlite sources only; "
                    f"'{s.name or s.id}' is {s.source_type}"
                ),
            )
