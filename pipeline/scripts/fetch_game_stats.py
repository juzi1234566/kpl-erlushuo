"""抓取比赛每局的官方战绩数据（英雄/KDA/经济/输出/BP/MVP）。

产出：data/insights/_stats_{match_id}.json；配好密钥时同步 upsert 云端 match_game_stats。

用法：python -m scripts.fetch_game_stats --match-id 2026071703
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def build_game(b: dict, game_no: int) -> dict:
    camps = {1: b.get("camp1") or {}, 2: b.get("camp2") or {}}
    win_camp = b.get("win_camp")

    bans, picks = [], []
    for x in b.get("bp_list") or []:
        entry = {
            "camp": x.get("camp"),
            "hero": x.get("hero_name"),
            "icon": x.get("hero_icon"),
        }
        (picks if x.get("is_ban_or_pick") else bans).append(entry)

    players = []
    for p in b.get("battle_player_list") or []:
        players.append(
            {
                "camp": p.get("camp"),
                "team": p.get("team_name"),
                "player": p.get("player_name"),
                "hero": p.get("hero_name"),
                "hero_icon": p.get("hero_icon"),
                "position": p.get("position"),
                "k": p.get("kill_num"),
                "d": p.get("death_num"),
                "a": p.get("assist_num"),
                "gold": p.get("gold"),
                "hurt_rate": p.get("hurt_total_rate"),
                "be_hurt_rate": p.get("be_hurt_total_rate"),
                "participation": p.get("participation_rate"),
                "mvp": bool(p.get("is_mvp")),
                "lose_mvp": bool(p.get("is_lose_mvp")),
            }
        )
    players.sort(key=lambda x: (x.get("camp") or 0, x.get("position") or 0))

    return {
        "game_no": game_no,
        "battle_id": b.get("battle_id"),
        "duration_s": int((b.get("game_duration") or 0) / 1000),
        "win_camp": win_camp,
        "teams": {
            str(c): {
                "team_id": camps[c].get("team_id"),
                "name": camps[c].get("team_name"),
                "icon": camps[c].get("team_icon"),
                "kills": camps[c].get("kill_num"),
                "win": bool(camps[c].get("is_win")),
            }
            for c in (1, 2)
        },
        "bans": bans,
        "picks": picks,
        "players": players,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()

    from sources.pvp_match_adapter import PvpMatchAdapter

    games = []
    with PvpMatchAdapter(raw_dir=ROOT / "data" / "raw") as api:
        battles = api.list_battles(str(args.match_id))
        for bt in battles:
            bid = bt.get("battle_id")
            if not bid:
                continue
            b = api.get_battle(str(bid))
            seq = int(bt.get("battle_seq") or b.get("battle_seq") or len(games) + 1)
            games.append(build_game(b, seq))
            api.sleep_politely()
    games.sort(key=lambda g: g["game_no"])

    out = ROOT / "data" / "insights" / f"_stats_{args.match_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"match_id": str(args.match_id), "games": games}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已存 {out.name}：{len(games)} 局")

    if not args.no_upload:
        try:
            from db.supabase_client import SupabaseRest

            db = SupabaseRest()
            db.upsert(
                "match_game_stats",
                [{"match_id": str(args.match_id), "game_no": g["game_no"], "payload": g} for g in games],
                on_conflict="match_id,game_no",
            )
            print("云端已同步")
        except Exception as exc:  # noqa: BLE001
            print(f"云端未同步（{exc}）——本地文件可用")


if __name__ == "__main__":
    main()
