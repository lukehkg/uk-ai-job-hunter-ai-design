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


def _arrow(delta: float) -> str:
    return "▲" if delta > 0 else ("▼" if delta < 0 else "＝")


def _sector_table(catalog: dict) -> str:
    """Markdown mirror of the landing page's 'UK job market — live by
    sector' strip (same ordering: named sectors by volume, Other last)."""
    lines = [
        "",
        "**UK job market — live by sector**",
        "",
        "| Sector | Jobs | 3-day | 7-day | Median £ | Top employers |",
        "|---|---:|---:|---:|---:|---|",
    ]
    ordered = sorted(
        catalog.get("sectors", []),
        key=lambda s: (s.get("sector") == "Other", -(s.get("today") or 0)),
    )
    for s in ordered:
        today = s.get("today") or 0
        d3, d3p = s.get("delta_3d") or 0, s.get("delta_3d_pct") or 0
        d7, d7p = s.get("delta_7d") or 0, s.get("delta_7d_pct") or 0
        med = s.get("median_salary")
        med_txt = f"£{int(med):,}" if med else "—"
        emp = ", ".join(s.get("top_employers") or []) or "—"
        lines.append(
            f"| {s.get('sector')} | {today:,} "
            f"| {_arrow(d3)} {d3:+,} ({d3p:+.0f}%) "
            f"| {_arrow(d7)} {d7:+,} ({d7p:+.0f}%) "
            f"| {med_txt} | {emp} |"
        )
    total = catalog.get("total_today")
    if isinstance(total, (int, float)):
        lines.append(f"| **All sectors** | **{total:,}** | — | — | — | — |")
    return "\n".join(lines)


def build_table() -> str:
    lines = ["| Jobs data | Value |", "|---|---|"]

    # --- Live job counts from the production catalog API ---
    cat_status, catalog = _get("/api/v1/job-catalog")
    have_catalog = cat_status == 200 and isinstance(catalog, dict) and catalog.get("sectors")
    if cat_status == 200 and isinstance(catalog, dict):
        total_db = catalog.get("total_jobs_in_dataset")
        total_today = catalog.get("total_today")
        sectors = catalog.get("sectors", [])
        gen = str(catalog.get("generated_at", ""))[:10]
        if isinstance(total_db, (int, float)):
            lines.append(
                f"| 🗄 Jobs in the full database | **{total_db:,}** (UK-deduplicated) |"
            )
        if isinstance(total_today, (int, float)):
            lines.append(
                f"| 🆕 New jobs collected (latest day) | **{total_today:,}** |"
            )
        lines.append(f"| 🏷 Sectors tracked | {len(sectors)} |")
        if gen:
            lines.append(f"| 🕒 Data last refreshed | {gen} |")
    else:
        lines.append(
            "| ⚠️ Live refresh | catalog feed temporarily unavailable — job counts "
            "below are the last published snapshot |"
        )
        # Last published snapshot (keep in sync with monthly compaction notes)
        lines.append("| 🗄 Jobs in the full database | **10,728** (UK-deduplicated) |")
        lines.append("| 🆕 New jobs collected (latest day) | **357** |")
        lines.append("| 🏷 Sectors tracked | 8 |")

    # --- Collection freshness (is the pipeline still running?) ---
    status, health = _get("/api/v1/healthz")
    if status == 200:
        dedup = health.get("exports_freshness", {}).get("deduped_jobs.json", {})
        age = dedup.get("age_seconds")
        if isinstance(age, (int, float)):
            lines.append(
                f"| ♻️ Collection pipeline | healthy — last batch {age / 3600:.1f} h ago |"
            )
    else:
        lines.append("| 🔴 Collection pipeline | unreachable |")

    # --- AI training data + scam-detection coverage (static, updated at
    #     compaction milestones; see docs/02-data-flow.md for the numbers) ---
    lines.append("")
    lines.append("| 🧠 AI training corpus | 128,627 gated rows · 12.9× the 10k minimum |")
    lines.append(
        "| 🛡 Scam screening | every listing passes rule + duplicate screening; "
        "RAG trust scoring live, labels accumulating toward student distillation |"
    )

    # --- The sector table itself (mirrors the landing-page strip) ---
    if have_catalog:
        lines.append("")
        lines.append(_sector_table(catalog))

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"| *Snapshot* | *{now} — auto-updates daily ~07:00 UTC* |")
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
