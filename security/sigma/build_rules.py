"""Compile SigmaHQ command-line rules into rules.json for sigma_hook.py.

Downloads a pinned SigmaHQ release, keeps the rules that can be evaluated against a
shell command, and converts each one to a SQLite WHERE clause with pySigma's SQLite
backend. The hook then only needs the Python standard library.

Run through `make sigma-rules`, which provides pySigma in security/sigma/.venv.
"""
import io
import json
import sys
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sigma.backends.sqlite import sqliteBackend
from sigma.collection import SigmaCollection
from sigma.rule import SigmaDetection, SigmaDetectionItem

SIGMA_RELEASE = "r2026-07-01"
# "core+" = stable and test rules at level medium, high and critical
PACKAGE = "sigma_core%2B.zip"
URL = f"https://github.com/SigmaHQ/sigma/releases/download/{SIGMA_RELEASE}/{PACKAGE}"

HERE = Path(__file__).parent
CACHE = HERE / ".cache" / f"{SIGMA_RELEASE}-core+.zip"
OUT = HERE / "rules.json"

# Log sources a shell command can stand in for
LOGSOURCES = {
    ("process_creation", "linux"),
    ("process_creation", "macos"),
    ("process_creation", "windows"),
    ("ps_script", "windows"),
}
# Fields the hook fills from the command. Every other field stays NULL.
POPULATED_FIELDS = {"CommandLine", "Image", "OriginalFileName", "ScriptBlockText"}
LEVELS = {"medium", "high", "critical"}
STATUSES = {"stable", "test"}


def download():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {URL}")
        CACHE.write_bytes(urllib.request.urlopen(URL, timeout=60).read())
    return zipfile.ZipFile(io.BytesIO(CACHE.read_bytes()))


def fields(detection):
    """All field names referenced by a detection, recursively."""
    for item in detection.detection_items:
        if isinstance(item, SigmaDetection):
            yield from fields(item)
        elif isinstance(item, SigmaDetectionItem) and item.field:
            yield item.field


def text(value):
    return str(value) if value else ""


def main():
    archive = download()
    backend = sqliteBackend()
    rules, skipped = [], Counter()

    for name in sorted(archive.namelist()):
        if not name.endswith(".yml"):
            continue
        try:
            collection = SigmaCollection.from_yaml(archive.read(name).decode("utf-8"))
        except Exception:
            skipped["unparseable"] += 1
            continue
        for rule in collection.rules:
            source = (rule.logsource.category, rule.logsource.product)
            if source not in LOGSOURCES:
                continue
            level = rule.level.name.lower() if rule.level else ""
            status = rule.status.name.lower() if rule.status else ""
            if level not in LEVELS or status not in STATUSES:
                skipped["level or status"] += 1
                continue
            used = {f for d in rule.detection.detections.values() for f in fields(d)}
            if not used & POPULATED_FIELDS:
                skipped["no command-line field"] += 1
                continue
            try:
                query = backend.convert(SigmaCollection([rule]))[0]
            except Exception:
                skipped["conversion error"] += 1
                continue
            prefix = "SELECT * FROM logs WHERE "
            if not query.startswith(prefix):
                skipped["unexpected query shape"] += 1
                continue
            tags = [f"{t.namespace}.{t.name}" for t in rule.tags]
            rules.append({
                "id": str(rule.id),
                "title": rule.title,
                "level": level,
                "status": status,
                "author": text(rule.author),
                "description": text(rule.description),
                "falsepositives": [str(f) for f in rule.falsepositives or []],
                "references": [str(r) for r in (rule.references or [])[:3]],
                "tags": tags,
                "category": source[0],
                "product": source[1],
                "fields": sorted(used),
                "sql": query[len(prefix):],
            })

    out = {
        "sigma_release": SIGMA_RELEASE,
        "package": "core+",
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "populated_fields": sorted(POPULATED_FIELDS),
        "fields": sorted({f for r in rules for f in r["fields"]}),
        "rules": rules,
    }
    # One rule per line keeps diffs readable when the pinned release changes
    header = json.dumps({k: v for k, v in out.items() if k != "rules"}, ensure_ascii=False)[:-1]
    lines = ",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rules)
    OUT.write_text(f'{header}, "rules": [\n{lines}\n]}}\n', encoding="utf-8")

    by_source = Counter(f"{r['category']}/{r['product']}" for r in rules)
    by_level = Counter(r["level"] for r in rules)
    print(f"Kept {len(rules)} rules from SigmaHQ {SIGMA_RELEASE} -> {OUT.name}")
    for key, n in sorted(by_source.items()):
        print(f"  {key}: {n}")
    print("  levels: " + ", ".join(f"{k}={v}" for k, v in sorted(by_level.items())))
    print("Skipped: " + (", ".join(f"{k}={v}" for k, v in skipped.most_common()) or "none"))


if __name__ == "__main__":
    sys.exit(main())
