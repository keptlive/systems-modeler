"""Audit every categorized legacy model without changing or deleting any input."""
import argparse
import json
import time
import hashlib
import subprocess
from collections import Counter
from pathlib import Path
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate
from app.core.failure_diagnostics import failure_payload
from app.core.validation import inspect_inputs

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--full", action="store_true", help="Run complete defaults rather than a 4-step smoke check")
parser.add_argument("--random-seed", type=int, default=42, help="Fallback seed for reproducible stochastic audit runs")
parser.add_argument("--tracked-only", action="store_true", help="Audit Git-tracked public definitions, excluding local user/test additions")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
rows = []
started = time.monotonic()
engine_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted((root / "app" / "core").glob("*.py"))}
paths = sorted((root / "models").rglob("*.json"))
if args.tracked_only:
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z', 'models'], cwd=root).decode().split('\0'))
    paths = [p for p in paths if p.relative_to(root).as_posix() in tracked]
if not paths:
    raise ValueError('No model JSON files found; an empty audit cannot pass')
for path in paths:
    row = {"file": str(path.relative_to(root)), "id": path.stem,
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    try:
        model = Model.model_validate_json(path.read_text())
        row['input_issues'] = inspect_inputs(model, numerical_check=False)['issues']
        row["id"] = model.id
        ts = model.time_settings
        if ts.random_seed is None:
            ts = TimeSettings(**{**ts.model_dump(), "random_seed": args.random_seed})
        if not args.full:
            ts = TimeSettings(**{**ts.model_dump(), "end": min(ts.end, ts.start + 4 * ts.dt)})
        result = simulate(model, ts)
        if not result.time or not result.values:
            raise ValueError('Empty simulation output cannot pass a library audit')
        row.update(status="passed", points=len(result.time), elements=len(result.values), random_seed=result.random_seed, integration_diagnostics=result.integration_diagnostics)
        row['changing_stocks'] = [s.name for s in model.stocks
                                  if min(result.values[s.name]) != max(result.values[s.name])]
    except Exception as exc:
        row.update(status="failed", error=str(exc), failure=failure_payload(exc))
    rows.append(row)
report = {"scope": "full default runs" if args.full else "four-step numerical smoke checks",
          "library_scope": "Git-tracked public definitions" if args.tracked_only else "All definitions present in models/",
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
