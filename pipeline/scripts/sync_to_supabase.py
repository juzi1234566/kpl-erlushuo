"""把官方赛程 + 种子梗同步进 Supabase。"""

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

from db.supabase_client import SupabaseRest  # noqa: E402
from sources.pvp_match_adapter import LEAGUE_SUMMER_2026, PvpMatchAdapter  # noqa: E402

# 种子梗唯一数据源：web/src/lib/seed-memes.json（与前端共用，勿在此硬编码）
SEED_MEMES_JSON = ROOT.parent / "web" / "src" / "lib" / "seed-memes.json"

# memes 表实际存在的列；JSON 里的 tags 等展示用字段在入库前剔除
MEME_DB_COLUMNS = {
    "slug",
    "title",
    "definition",
    "origin_story",
    "category",
    "hotness",
    "is_ai_assisted",
    "moderation_status",
}


def load_seed_memes() -> list[dict]:
    raw = json.loads(SEED_MEMES_JSON.read_text(encoding="utf-8"))
    rows = []
    for m in raw:
        row = {k: v for k, v in m.items() if k in MEME_DB_COLUMNS}
        row.setdefault("hotness", 50)
        row.setdefault("is_ai_assisted", False)
        row.setdefault("moderation_status", "approved")
        rows.append(row)
    return rows




def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", default=LEAGUE_SUMMER_2026)
    parser.add_argument("--skip-matches", action="store_true")
    parser.add_argument("--memes-only", action="store_true")
    args = parser.parse_args()

    db = SupabaseRest()
    print("Supabase OK:", db.url)

    # memes upsert by slug — table uses uuid id, so we need unique slug
    # PostgREST on_conflict=slug requires unique constraint on slug (we have it)
    seed_memes = load_seed_memes()
    print(f"upsert memes x{len(seed_memes)}")
    # memes table: slug unique — but upsert needs primary key or unique cols
    db.upsert("memes", seed_memes, on_conflict="slug")

    if args.memes_only:
        print("done (memes only)")
        return

    with PvpMatchAdapter(raw_dir=ROOT / "data" / "raw") as api:
        leagues = api.list_leagues()
        league_rows = []
        for x in leagues:
            if str(x.get("league_id")) == str(args.league_id) or x.get("status") == 1:
                league_rows.append(
                    {
                        "id": str(x.get("league_id")),
                        "name": x.get("league_name") or "",
                        "year": x.get("year"),
                        "season": x.get("season"),
                        "status": x.get("status"),
                        "start_time": x.get("start_time") or None,
                        "end_time": x.get("end_time") or None,
                        "icon_url": x.get("league_icon"),
                        "raw": x,
                    }
                )
        if league_rows:
            print(f"upsert leagues x{len(league_rows)}")
            db.upsert("leagues", league_rows, on_conflict="id")

        if args.skip_matches:
            print("done")
            return

        matches = api.list_matches(args.league_id)
        teams: dict[str, dict] = {}
        match_rows = []
        for m in matches:
            c1, c2 = m.get("camp1") or {}, m.get("camp2") or {}
            for c in (c1, c2):
                tid = str(c.get("team_id") or "")
                if tid and tid not in teams:
                    teams[tid] = {
                        "id": tid,
                        "name": c.get("team_name") or tid,
                        "abbreviation": c.get("team_abbreviation"),
                        "icon_url": c.get("team_icon"),
                    }
            match_rows.append(
                {
                    "id": str(m.get("match_id")),
                    "league_id": str(m.get("league_id") or args.league_id),
                    "team1_id": str(c1.get("team_id") or "") or None,
                    "team2_id": str(c2.get("team_id") or "") or None,
                    "score1": c1.get("score"),
                    "score2": c2.get("score"),
                    "bo": m.get("bo"),
                    "win_camp": m.get("win_camp"),
                    "status": m.get("status"),
                    # 未开赛场次时间为空串，timestamptz 列须传 null
                    "start_time": m.get("start_time") or None,
                    "end_time": m.get("end_time") or None,
                    "stage_name": m.get("match_stage_name"),
                    "stage_desc": m.get("match_stage_desc"),
                    "venue": m.get("match_address"),
                }
            )

        if teams:
            print(f"upsert teams x{len(teams)}")
            db.upsert("teams", list(teams.values()), on_conflict="id")

        # chunk matches
        chunk = 50
        for i in range(0, len(match_rows), chunk):
            part = match_rows[i : i + chunk]
            print(f"upsert matches {i+1}-{i+len(part)} / {len(match_rows)}")
            db.upsert("matches", part, on_conflict="id")

    print("DONE sync")


if __name__ == "__main__":
    main()
