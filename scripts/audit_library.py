"""Audit every categorized legacy model without changing or deleting any input."""
import argparse
import json
import time
import hashlib
from collections import Counter
from pathlib import Path
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--full", action="store_true", help="Run complete defaults rather than a 4-step smoke check")
parser.add_argument("--random-seed", type=int, default=42, help="Fallback seed for reproducible stochastic audit runs")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
rows = []
started = time.monotonic()
engine_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted((root / "app" / "core").glob("*.py"))}
for path in sorted((root / "models").rglob("*.json")):
    row = {"file": str(path.relative_to(root)), "id": path.stem,
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    try:
        model = Model.model_validate_json(path.read_text())
        row["id"] = model.id
        ts = model.time_settings
        if ts.random_seed is None:
            ts = TimeSettings(**{**ts.model_dump(), "random_seed": args.random_seed})
        if not args.full:
            ts = TimeSettings(**{**ts.model_dump(), "end": min(ts.end, ts.start + 4 * ts.dt)})
        result = simulate(model, ts)
        row.update(status="passed", points=len(result.time), elements=len(result.values), random_seed=result.random_seed)
    except Exception as exc:
        row.update(status="failed", error=str(exc))
    rows.append(row)
report = {"scope": "full default runs" if args.full else "four-step numerical smoke checks",
          "fallback_random_seed": args.random_seed,
          "engine_sha256": engine_hashes,
          "scientific_validation": "not established; inspect assumptions and source references",
          "seconds": round(time.monotonic() - started, 2), "counts": dict(Counter(r["status"] for r in rows)),
          "models": rows}
if engine_hashes != {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((root / "app" / "core").glob("*.py"))}:
    raise RuntimeError("Engine source changed during the audit; rerun against a frozen source")
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k not in ("models", "engine_sha256")}, indent=2))
