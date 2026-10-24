"""Apply only hash-reviewed public model repairs, preserving every other data byte.

Dry-run by default. The application service is paused only during the fenced writes
and restarted in finally. Originals and a complete data hash receipt are retained.
Never use this to synchronize a model directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(app, manifest):
    app = app.resolve()
    rows = []
    if not 1 <= len(manifest["repairs"]) <= 20:
        raise ValueError("Expected 1–20 explicitly reviewed repairs")
    seen = set()
    for entry in manifest["repairs"]:
        relative = Path(entry["file"])
        if relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "models" or relative.suffix != ".json":
            raise ValueError("Only individual model JSON paths are permitted")
        if str(relative) in seen:
            raise ValueError("Duplicate repair path")
        seen.add(str(relative))
        target = app / relative
        if target.is_symlink() or not target.resolve().is_relative_to(app / "models"):
            raise ValueError("Model path escapes the models directory")
        payload = entry["content"].encode("utf-8")
        if hashlib.sha256(payload).hexdigest() != entry["after_sha256"]:
            raise ValueError("Replacement hash mismatch: " + str(relative))
        original = target.read_bytes()
        if hashlib.sha256(original).hexdigest() != entry["before_sha256"]:
            raise ValueError("Model changed since reviewed baseline: " + str(relative))
        if json.loads(original)["id"] != json.loads(payload)["id"]:
            raise ValueError("Repair cannot change model identity")
        rows.append((relative, target, payload, original, target.stat()))
    return rows


def data_hashes(app):
    paths = sorted((app / "models").rglob("*.json"))
    if (app / "models.db").exists():
        paths.append(app / "models.db")
    return {str(path.relative_to(app)): digest(path) for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--service", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    app = args.app.resolve()
    manifest = json.loads(args.manifest.read_text())
    rows = plan(app, manifest)
    if not args.apply:
        print(json.dumps({"dry_run": True, "reviewed_models": [str(row[0]) for row in rows]}))
        return
    # No write occurs before a complete plan passes. Revalidate after stopping the
    # writer so an in-flight edit cannot race the replacement.
    subprocess.run(["systemctl", "stop", args.service], check=True)
    applied = []
    try:
        rows = plan(app, manifest)
        before = data_hashes(app)
        args.backup.mkdir(parents=True, exist_ok=False, mode=0o700)
        (args.backup / "data-before.json").write_text(json.dumps(before, indent=2))
        (args.backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
        for relative, target, payload, original, stat in rows:
            saved = args.backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            temporary = target.with_name("." + target.name + ".reviewed-repair")
            with temporary.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, stat.st_mode & 0o777)
            os.chown(temporary, stat.st_uid, stat.st_gid)
            os.replace(temporary, target)
            applied.append((target, original, payload, stat))
        expected = dict(before)
        expected.update({entry["file"]: entry["after_sha256"] for entry in manifest["repairs"]})
        actual = data_hashes(app)
        if actual != expected:
            raise RuntimeError("Unexpected data change during targeted repair")
        receipt = {"changed_models": [entry["file"] for entry in manifest["repairs"]],
                   "all_other_data_unchanged": True, "files_checked": len(actual)}
        (args.backup / "verification.json").write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt))
    except Exception:
        for target, original, payload, stat in reversed(applied):
            if target.read_bytes() == payload:
                temporary = target.with_name("." + target.name + ".repair-rollback")
                shutil.copy2(args.backup / target.relative_to(app), temporary)
                os.chown(temporary, stat.st_uid, stat.st_gid)
                os.replace(temporary, target)
        raise
    finally:
        subprocess.run(["systemctl", "start", args.service], check=True)


if __name__ == "__main__":
    main()
