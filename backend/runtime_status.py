"""Utilitários para status compartilhado do sistema em tempo de execução."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


STATUS_FILE = Path(__file__).resolve().parent / ".runtime" / "system_status.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_status() -> Dict[str, Any]:
    return {
        "server_role": "unknown",
        "state": "unknown",
        "source": "unknown",
        "engine_host": "127.0.0.1",
        "engine_port": 5000,
        "last_failover_reason": None,
        "last_failover_at": None,
        "updated_at": _utc_now(),
    }


def read_system_status() -> Dict[str, Any]:
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _default_status()
    except Exception:
        return _default_status()


def write_system_status(**fields: Any) -> Dict[str, Any]:
    status = _default_status()
    status.update(fields)
    status["updated_at"] = _utc_now()

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return status