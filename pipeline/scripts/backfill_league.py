"""批量回填某赛季赛程；可选拉取已完赛对局详情（限速）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sources.pvp_match_adapter import LEAGUE_SUMMER_2026, PvpMatchAdapter  # noqa: E402
from signals.meme_signals import (  # noqa: E402
    extract_battle_signals,
    extract_match_signals,
    rank_signals,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", default=LEAGUE_SUMMER_2026)
    parser.add_argument("--out", default=str(ROOT / "data" / "raw"))
    parser.add_argument("--fetch-battles", type=int, default=0, help="最多拉 N 场已完赛的全部小局详情")
    parser.add_argument("--with-signals", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with PvpMatchAdapter(raw_dir=out) as api:
        league = api.current_league(args.league_id)
        print("league:", json.dumps(league, ensure_ascii=False))
        matches = api.list_matches(args.league_id)
        summary = {
            "league_id": args.league_id,
            "match_count": len(matches),
            "finished": sum(1 for m in matches if m.get("status") == 2),
            "matches": [
                {
                    "match_id": m.get("match_id"),
                    "status": m.get("status"),
                    "start_time": m.get("start_time"),
                    "score": f"{(m.get('camp1') or {}).get('score')}:{(m.get('camp2') or {}).get('score')}",
                    "teams": [
                        (m.get("camp1") or {}).get("team_name"),
                        (m.get("camp2") or {}).get("team_name"),
                    ],
                    "battle_ids": api.battle_ids_from_match(m),
                    "signals": extract_match_signals(m) if args.with_signals else [],
                }
                for m in matches
            ],
        }
        summary_path = out / f"summary_{args.league_id}.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {summary_path} matches={len(matches)}")

        if args.fetch_battles > 0:
            finished = [m for m in matches if m.get("status") == 2][: args.fetch_battles]
            all_signals: list[dict] = []
            for m in finished:
                for bid in api.battle_ids_from_match(m):
                    battle = api.get_battle(bid)
                    if args.with_signals:
                        sigs = rank_signals(extract_match_signals(m) + extract_battle_signals(battle))
                        all_signals.append({"match_id": m.get("match_id"), "battle_id": bid, "signals": sigs})
                    api.sleep_politely(0.4)
            if all_signals:
                sig_path = out / f"signals_sample_{args.league_id}.json"
                sig_path.write_text(json.dumps(all_signals, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"wrote {sig_path}")


if __name__ == "__main__":
    main()
