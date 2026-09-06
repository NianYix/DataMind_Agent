from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any

from sandbox.security import SecurityError, validate_code
from server.core.config import get_settings


def execute_python(
    code: str,
    dataset_path: str,
    *,
    timeout_sec: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    timeout = timeout_sec or settings.tool_timeout_sec
    started = time.perf_counter()

    try:
        validate_code(code)
    except SecurityError as exc:
        return {
            "success": False,
            "error": str(exc),
            "stdout": "",
            "result": None,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }

    runner = textwrap.dedent(
        f"""
        import json
        import pandas as pd
        from pathlib import Path

        path = Path({dataset_path!r})
        if path.suffix.lower() == '.csv':
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        for col in df.columns:
            if 'date' in str(col).lower() or 'time' in str(col).lower():
                df[col] = pd.to_datetime(df[col], errors='coerce')

        result = None
        stdout_lines = []

        def _print(*args, **kwargs):
            stdout_lines.append(' '.join(str(a) for a in args))

        print = _print

        # --- user code start ---
{textwrap.indent(code, '        ')}
        # --- user code end ---

        def _to_jsonable(obj):
            import numpy as np
            import pandas as pd
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            if isinstance(obj, pd.Series):
                return json.loads(obj.to_json(orient='index', date_format='iso', force_ascii=False))
            if isinstance(obj, pd.DataFrame):
                return json.loads(obj.to_json(orient='records', date_format='iso', force_ascii=False))
            if isinstance(obj, (list, dict)):
                return obj
            return str(obj)

        payload = {{
            'success': True,
            'stdout': '\\n'.join(stdout_lines),
            'result': _to_jsonable(result),
            'error': None,
        }}
        print_json = json.dumps(payload, ensure_ascii=False)
        import sys
        sys.stdout.write('<<<RESULT>>>' + print_json + '<<<END>>>')
        """
    )

    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "run.py"
        script_path.write_text(runner, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {timeout}s",
                "stdout": "",
                "result": None,
                "duration_ms": int((time.perf_counter() - started) * 1000),
            }

        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        if "<<<RESULT>>>" in stdout and "<<<END>>>" in stdout:
            raw = stdout.split("<<<RESULT>>>", 1)[1].split("<<<END>>>", 1)[0]
            try:
                payload = json.loads(raw)
                payload["duration_ms"] = duration_ms
                return payload
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse sandbox result JSON",
                    "stdout": stdout,
                    "result": None,
                    "duration_ms": duration_ms,
                }

        return {
            "success": False,
            "error": stderr.strip() or f"Process exited with code {proc.returncode}",
            "stdout": stdout,
            "result": None,
            "duration_ms": duration_ms,
        }
