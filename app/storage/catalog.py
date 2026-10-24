"""Small, file-versioned model index. Full definitions are fetched on demand."""
from pathlib import Path
from threading import Lock
import json
import logging
import hashlib

from app.storage import models as storage

_lock = Lock()
_signature = None
_catalog = []
logger = logging.getLogger(__name__)
AUDIT_PATH = Path(__file__).resolve().parents[2] / "static" / "library-validation.json"


def list_summaries():
    global _signature, _catalog
    with _lock:
        paths = sorted(Path(storage.MODELS_DIR).rglob("*.json"))
        signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
        signature += (AUDIT_PATH.stat().st_mtime_ns if AUDIT_PATH.exists() else 0,)
        if signature != _signature:
            rows = []
            audits = {}
            if AUDIT_PATH.exists():
                audits = {r["id"]: r for r in json.loads(AUDIT_PATH.read_text()).get("models", [])}
            for path in paths:
                try:
                    raw = path.read_bytes()
                    data = json.loads(raw)
                    audit = audits.get(data["id"], {})
                    checked = audit.get("sha256") == hashlib.sha256(raw).hexdigest()
                    rows.append({
                        "id": data["id"], "name": data.get("name", "Untitled Model"),
                        "description": data.get("description", ""),
                        "category": path.parent.name if path.parent != Path(storage.MODELS_DIR)
                        else (data.get("category") or "other"),
                        "stock_count": len(data.get("stocks", [])),
                        "flow_count": len(data.get("flows", [])),
                        "variable_count": len(data.get("variables", [])),
                        "numerical_check": audit.get("status", "not_checked") if checked else "not_checked",
                        "check_error": audit.get("error", "")[:300] if checked else "",
                    })
                except (ValueError, KeyError, TypeError):
                    logger.warning("Invalid catalog entry: %s", path.name)
            _catalog = sorted(rows, key=lambda row: (row["name"].casefold(), row["id"]))
            _signature = signature
        return [dict(row) for row in _catalog]
