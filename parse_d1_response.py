import json
import sys
from pathlib import Path


def fail(kind, status, code=None):
    suffix = f"; api_code={code}" if type(code) is int else ""
    print(f"D1 response rejected: kind={kind}; wrangler_exit={status}{suffix}", file=sys.stderr)
    raise SystemExit(1)


def main():
    mode, status_text, response_path, stderr_path = sys.argv[1:]
    status = int(status_text)
    raw = Path(response_path).read_text(errors="replace")
    try:
        data = json.loads(raw)
    except ValueError:
        fail("command-failed" if status else "invalid-json", status)

    if isinstance(data, dict) and "error" in data:
        error = data["error"]
        code = error.get("code") if isinstance(error, dict) else None
        # WHY: CLI error bodies can contain request details and credentials.
        text = json.dumps(error).lower() + Path(stderr_path).read_text(errors="replace").lower()
        kind = "transport-error" if any(term in text for term in (
            "fetch failed", "econnreset", "enotfound", "etimedout", "econnrefused",
        )) else "error-envelope"
        fail(kind, status, code)
    if status:
        fail("command-failed", status)
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        fail("unexpected-envelope", status)
    result = data[0]
    if result.get("success") is not True or result.get("errors"):
        fail("query-failed", status)
    rows = result.get("results")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        fail("invalid-results", status)
    if mode == "max":
        if len(rows) != 1 or type(rows[0].get("m")) is not int or rows[0]["m"] < 0:
            fail("invalid-max-seq", status)
        print(rows[0]["m"])
    elif mode == "rows":
        for row in rows:
            print(json.dumps(row))
    elif mode != "check":
        fail("invalid-mode", status)


if __name__ == "__main__":
    main()
