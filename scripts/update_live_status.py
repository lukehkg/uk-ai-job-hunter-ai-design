"""Refresh the LIVE-STATUS section in README.md from the production API.

Runs daily via .github/workflows/live-status.yml (no credentials needed —
the health endpoint is public). Rewrites only the block between the
LIVE-STATUS markers; exits 0 with no output change when the site is
unchanged.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from urllib.request import urlopen

BASE = "https://jobs.ai-daily.uk"
README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- LIVE-STATUS:START -->"
END = "<!-- LIVE-STATUS:END -->"


def _get(path: str, timeout: int = 20):
    try:
        with urlopen(BASE + path, timeout=timeout) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - status page must never crash
        return None, {"error": str(exc)[:120]}


def _age_hours(seconds: float) -> str:
    if seconds < 3600:
        return f"{int(seconds / 60)} min old"
    return f"{seconds / 3600:.1f} h old"


def _health_row(name: str, info: dict) -> str:
    size_mb = info.get("size_bytes", 0) / 1_000_000
    age = info.get("age_seconds")
    fresh = isinstance(age, (int, float)) and age < 26 * 3600
    mark = "✅" if fresh else "⚠️"
    age_txt = _age_hours(age) if isinstance(age, (int, float)) else "unknown"
    return f"| {mark} {name} | {size_mb:.1f} MB, {age_txt} |"


def build_table() -> str:
    lines = ["| Check | Value |", "|---|---|"]
    status, health = _get("/api/v1/healthz")
    if status == 200:
        lines.append(
            f"| ✅ API health | ok — `{health.get('service')}` "
            f"v{health.get('version')} |"
        )
        lines.append(f"| Deployed commit | `{str(health.get('commit'))[:8]}` |")
        fresh = health.get("exports_freshness", {})
        for key, label in (
            ("deduped_jobs.json", "Jobs database (`deduped_jobs.json`)"),
            ("adzuna_latest.jsonl", "Board-A feed (`*_latest.jsonl`)"),
            ("jobspy_latest.jsonl", "Scraper feed"),
        ):
            info = fresh.get(key)
            if info:
                lines.append(_health_row(label, info))
    else:
        err = health.get("error", "unreachable") if isinstance(health, dict) else "unreachable"
        lines.append(f"| 🔴 API health | unreachable — {err} |")

    cat_status, catalog = _get("/api/v1/job-catalog")
    if cat_status == 200 and isinstance(catalog, dict):
        sectors = len(catalog.get("sectors", []))
        total = catalog.get("total_today")
        gen = str(catalog.get("generated_at", ""))[:10]
        total_txt = f", {total:,} new jobs" if isinstance(total, (int, float)) else ""
        lines.append(
            f"| ✅ Landing-page sector catalog | {sectors} sectors{total_txt}"
            f" (refreshed {gen}) |"
        )
    else:
        lines.append(
            "| ⚠️ Landing-page sector catalog | temporarily unavailable |"
        )

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"| *Snapshot taken* | *{now} — auto-updates daily ~07:00 UTC* |")
    return "\n".join(lines)


def main() -> int:
    text = README.read_text(encoding="utf-8")
    start = text.index(START) + len(START)
    end = text.index(END)
    updated = text[:start] + "\n" + build_table() + "\n" + text[end:]
    if updated == text:
        print("live status unchanged")
        return 0
    README.write_text(updated, encoding="utf-8")
    print("live status updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
