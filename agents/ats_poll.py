"""
ats_poll.py — poll employer job boards and write listings_ats.json.

Run directly: python3 agents/ats_poll.py

Reads config/ats_sources.json. Disabled tenants are skipped and reported as
skipped; a tenant whose facet ids have not been read from its own board is
disabled rather than given guessed ids.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.workday import fetch_tenant, load_tenants  # noqa: E402

ROOT = Path(__file__).parent.parent
CONFIG = ROOT / "config" / "ats_sources.json"


def main() -> None:
    cfg = json.loads(CONFIG.read_text())
    enabled = load_tenants(str(CONFIG))
    disabled = [t["company"] for t in cfg["tenants"] if not t.get("enabled", True)]
    today = date.today().isoformat()

    listings, reports = [], []
    for t in enabled:
        r = fetch_tenant(t, received=today)
        listings += r["listings"]
        reports.append({k: r[k] for k in
                        ("company", "total", "pages", "error", "complete")}
                       | {"parsed": len(r["listings"]),
                          "truncated": r.get("truncated_at_max_pages", False)})
        status = "ok" if r["complete"] else (r["error"] or "incomplete")
        print(f"  {t['company']:10} {len(r['listings']):4}/{r['total'] or '?':>4}  {status}")

    out = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "polled": reports,
        "skipped_disabled": disabled,
        "not_workday": cfg.get("not_workday", {}),
        "coverage": (f"{sum(1 for r in reports if r['complete'])} of "
                     f"{len(enabled) + len(disabled)} configured employers polled completely"),
        "listings": listings,
    }
    d = ROOT / "output" / today
    d.mkdir(parents=True, exist_ok=True)
    (d / "listings_ats.json").write_text(json.dumps(out, indent=2))
    print(f"\n{len(listings)} listings -> output/{today}/listings_ats.json")
    print(out["coverage"])


if __name__ == "__main__":
    main()
