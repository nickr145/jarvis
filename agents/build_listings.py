"""
build_listings.py — merge every listing source into one ranked file.

Run directly: python3 agents/build_listings.py

Reads listings_email.json (written by the email agent's digest miner) and
listings_ats.json (written by ats_poll.py), collapses a role seen through
several sources into one row, ranks, and writes listings.json for the portal.

Coverage from every input is carried forward. A merge is the easiest place to
lose the fact that a harvest was partial, because a combined list looks
authoritative regardless of what went into it.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.alert_parser import (build_alias_index, collapse_across_sources,  # noqa: E402
                                 dedupe, rank)

ROOT = Path(__file__).parent.parent


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def main() -> None:
    today = date.today().isoformat()
    d = ROOT / "output" / today
    profile = json.loads((ROOT / "config" / "profile.json").read_text())
    cfg = json.loads((ROOT / "config" / "ats_sources.json").read_text())
    aliases = build_alias_index(cfg["tenants"])

    email = load(d / "listings_email.json")
    ats = load(d / "listings_ats.json")

    rows, coverage, missing = [], [], []
    for name, src in (("email digests", email), ("employer boards", ats)):
        if src is None:
            missing.append(name)
            continue
        rows += src.get("listings", [])
        if src.get("coverage"):
            coverage.append(f"{name}: {src['coverage']}")
        if src.get("caveat"):
            coverage.append(f"{name}: {src['caveat']}")

    if not rows and len(missing) == 2:
        # Every source is absent — nothing was merged and nothing is known.
        # Writing an empty listings.json here would assert "no jobs today",
        # which is false; the truth is "no source ran today". The portal then
        # falls back to the newest file that does represent a real run.
        print("no listing sources present — not writing listings.json")
        for name in missing:
            print(f"  MISSING: {name}")
        return []

    before = len(rows)
    rows = dedupe(rows)
    rows = collapse_across_sources(rows, aliases)
    merged = before - len(rows)
    ranked = rank(rows, profile.get("job_keywords", []), home="ON", today=today)

    out = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "coverage": " | ".join(coverage) or "no sources present",
        "sources_missing": missing,
        "collapsed_duplicates": merged,
        "listings": ranked,
    }
    (d / "listings.json").write_text(json.dumps(out, indent=2))
    print(f"{before} in -> {len(ranked)} out ({merged} duplicates collapsed)")
    for name in missing:
        print(f"  MISSING: {name}")
    return ranked


if __name__ == "__main__":
    ranked = main()
    print()
    for i, x in enumerate(ranked[:12], 1):
        also = f"  (+{','.join(x['also_on'])})" if x.get("also_on") else ""
        src = (x.get("source") or "").split(":")[0]
        print(f"{i:2}. {x['title'][:44]:44} | {x['company'][:16]:16} | {src:8}{also}")
