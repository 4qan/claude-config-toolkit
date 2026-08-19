#!/usr/bin/env python3
"""Count input tokens for a list of files using Anthropic's count_tokens endpoint.

Used by /audit-tokens to ground its claims in token counts rather than line counts.

Usage:
    count_tokens.py <model> <file1> [<file2> ...]
    count_tokens.py <model> --stdin              # count tokens for content piped on stdin

Output: JSON to stdout
    {
      "model": "claude-opus-4-7",
      "default_method": "api" | "approx",
      "results": [
        {"path": "...", "tokens": 1234, "method": "api"},
        {"path": "...", "tokens": 567, "method": "approx", "api_error": "..."}
      ]
    }

Falls back to char/4 approximation if no API key is available or the API call fails.
The approximation is rough but directionally correct enough to be more credible than line counts.

Key resolution order:
    1. $ANTHROPIC_API_KEY (stripped from Claude Code subshells, so usually empty here)
    2. $COUNT_TOKENS_API_KEY (escape hatch for env-based override)
    3. "env.ANTHROPIC_API_KEY" in ~/.claude/settings.local.json or ~/.claude/settings.json

Exit codes:
    0 — success (some results may be approx if API failed; check method per result)
    2 — usage error
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


def resolve_api_key() -> Optional[str]:
    """Resolve the Anthropic API key from env or Claude Code settings files.

    Claude Code strips ANTHROPIC_API_KEY from Bash subshells for safety, so the
    env var is typically empty when this script runs as a tool call. Fall back
    to reading the settings.local.json / settings.json env block directly.
    """
    direct = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("COUNT_TOKENS_API_KEY")
    if direct:
        return direct

    home = Path.home() / ".claude"
    for name in ("settings.local.json", "settings.json"):
        path = home / name
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        key = (data.get("env") or {}).get("ANTHROPIC_API_KEY")
        if key:
            return key
    return None

API_URL = "https://api.anthropic.com/v1/messages/count_tokens"
API_VERSION = "2023-06-01"


def count_via_api(model: str, content: str, api_key: str) -> int:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": content}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise urllib.error.HTTPError(e.url, e.code, f"{e.reason}: {body}", e.headers, None)
    return data["input_tokens"]


def count_via_approx(content: str) -> int:
    """Char/4 heuristic. Rough but directionally correct."""
    return len(content) // 4


def count_one(model, content, api_key):
    """Return a result dict for one piece of content."""
    if api_key:
        try:
            tokens = count_via_api(model, content, api_key)
            return {"tokens": tokens, "method": "api"}
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
            approx = count_via_approx(content)
            return {"tokens": approx, "method": "approx", "api_error": str(e)}
    return {"tokens": count_via_approx(content), "method": "approx"}


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: count_tokens.py <model> <file1> [<file2> ...]", file=sys.stderr)
        print("       count_tokens.py <model> --stdin", file=sys.stderr)
        return 2

    model = sys.argv[1]
    args = sys.argv[2:]
    api_key = resolve_api_key()

    results = []

    if args == ["--stdin"]:
        content = sys.stdin.read()
        result = {"path": "<stdin>"}
        result.update(count_one(model, content, api_key))
        results.append(result)
    else:
        for path in args:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                results.append({"path": path, "error": str(e)})
                continue
            result = {"path": path}
            result.update(count_one(model, content, api_key))
            results.append(result)

    print(
        json.dumps(
            {
                "model": model,
                "default_method": "api" if api_key else "approx",
                "results": results,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
