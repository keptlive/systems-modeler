"""Optional isolated cross-engine benchmark; never a production backend.
Run with the evaluation venv containing pysimlin and project dependencies.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import statistics
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def timed(call, repeats):
    measurements = []
    value = None
    for _ in range(repeats):
        start = time.perf_counter()
        value = call()
        measurements.append(time.perf_counter() - start)
    return value, {"median_seconds": statistics.median(measurements), "samples_seconds": measurements}


def benchmark(path, repeats, method):
    import numpy as np
    import simlin
    from app.core.xmile_parser import parse_xmile
    from app.core.simulator import simulate
    raw = path.read_bytes()
    ours, parse_ours = timed(lambda: parse_xmile(raw.decode()), repeats)
    settings = ours.time_settings.model_copy(update={"integration_method": method, "random_seed": 0})
    ours.time_settings = settings
    theirs, parse_theirs = timed(lambda: simlin.load(path), repeats)
    theirs.project.set_sim_specs(start=settings.start, stop=settings.end, dt=settings.dt, save_step=settings.dt, sim_method=method)
    # Both engines receive the same original equations, interval and method.
    a, cold_ours = timed(lambda: simulate(ours), 1)
    b, cold_theirs = timed(lambda: theirs.run(analyze_loops=False).results, 1)
    a, warm_ours = timed(lambda: simulate(ours), repeats)
    b, warm_theirs = timed(lambda: theirs.run(analyze_loops=False).results, repeats)
    normalize = lambda s: s.lower().replace(" ", "_")
    columns = {normalize(str(c)): c for c in b.columns}
    comparisons = {}
    for name, values in a.values.items():
        other = np.asarray(b[columns[normalize(name)]], dtype=float)
        actual = np.asarray(values, dtype=float)
        comparisons[name] = {"max_abs_error": float(np.max(np.abs(actual-other))), "allclose": bool(np.allclose(actual, other, rtol=6e-6, atol=5e-6))}
    return {"input": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(), "settings": settings.model_dump(mode="json"), "rows": len(a.time), "simlin_rows": len(b), "time_matches": bool(np.allclose(a.time, b[columns["time"]] if "time" in columns else b.index.to_numpy(), rtol=0, atol=1e-10)), "columns": comparisons, "stockflow": {"parse": parse_ours, "cold_run": cold_ours, "warm_run": warm_ours}, "simlin": {"parse": parse_theirs, "cold_run": cold_theirs, "warm_run": warm_theirs}, "warm_stockflow_over_simlin": warm_ours["median_seconds"]/warm_theirs["median_seconds"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--method", choices=("euler", "rk4"), default="euler")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 100:
        parser.error("repeats must be between 1 and 100")
    try:
        version = importlib.metadata.version("pysimlin")
    except importlib.metadata.PackageNotFoundError:
        parser.exit(2, "Optional reference unavailable: install pysimlin in an isolated evaluation environment.\n")
    result = {"stockflow_engine_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT / "app/core").glob("*.py"))}, "reference_distribution": "pysimlin", "reference_version": version, "python": sys.version, "platform": platform.platform(), "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "pydantic", "scipy")}, "methodology": "Original scalar SDXorg XMILE; matched method/time grid; loop analysis disabled; parse/cold/warm timings separated; complete output comparisons. Timings include result materialization, exclude process startup. Warm Simlin may reuse compilation; Stock & Flow currently rebuilds each simulation.", "cases": []}
    for folder, filename in (("teacup", "teacup.xmile"), ("SIR", "SIR.xmile")):
        path = ROOT / "tests/fixtures/sdxorg" / folder / filename
        try:
            result["cases"].append(benchmark(path, args.repeats, args.method))
        except Exception as error:
            result["cases"].append({"input": str(path.relative_to(ROOT)), "error": type(error).__name__ + ": " + str(error)})
    encoded = json.dumps(result, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(encoded + "\n")
    else:
        print(encoded)
    return int(any("error" in case or not case.get("time_matches") or not all(c["allclose"] for c in case.get("columns", {}).values()) for case in result["cases"]))

if __name__ == "__main__":
    raise SystemExit(main())
