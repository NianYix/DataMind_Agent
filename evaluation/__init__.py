from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def list_suites() -> list[dict[str, Any]]:
    suites = []
    for path in sorted(DATASETS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        suites.append(
            {
                "id": data.get("id") or path.stem,
                "name": data.get("name") or path.stem,
                "description": data.get("description") or "",
                "case_count": len(data.get("cases") or []),
                "path": str(path.relative_to(ROOT)),
            }
        )
    return suites


def load_suite(suite_id: str) -> dict[str, Any]:
    path = DATASETS_DIR / f"{suite_id}.json"
    if not path.exists():
        # allow id mismatch inside file
        for p in DATASETS_DIR.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("id") == suite_id:
                return data
        raise FileNotFoundError(f"Suite not found: {suite_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_dataset_path(rel: str) -> Path:
    p = Path(rel)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"Dataset not found: {rel}")
    return p
