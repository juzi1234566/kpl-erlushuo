"""Phase 0：官方接口 smoke test。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sources.pvp_match_adapter import LEAGUE_SUMMER_2026, PvpMatchAdapter  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leagues", action="store_true")
    parser.add_argument("--league-id", default=LEAGUE_SUMMER_2026)
    parser.add_argument("--matches", action="store_true")
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"))
    args = parser.parse_args()

    with PvpMatchAdapter(raw_dir=Path(args.raw_dir)) as api:
        if args.leagues:
            leagues = api.list_leagues()
            active = [x for x in leagues if x.get("status") == 1]
            print(f"leagues={len(leagues)} active={len(active)}")
            for x in active or leagues[-3:]:
                print(
                    f"  {x.get('league_id')} status={x.get('status')} {x.get('league_name')}"
                )
        if args.matches:
            matches = api.list_matches(args.league_id)
            finished = [m for m in matches if m.get("status") == 2]
            print(f"matches={len(matches)} finished={len(finished)}")
            for m in matches[:3]:
                c1, c2 = m.get("camp1") or {}, m.get("camp2") or {}
                print(
                    f"  {m.get('match_id')} {c1.get('team_abbreviation')} "
                    f"{c1.get('score')}:{c2.get('score')} {c2.get('team_abbreviation')} "
                    f"status={m.get('status')}"
                )


if __name__ == "__main__":
    main()
