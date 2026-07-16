"""把官方赛程 + 种子梗同步进 Supabase。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db.supabase_client import SupabaseRest  # noqa: E402
from sources.pvp_match_adapter import LEAGUE_SUMMER_2026, PvpMatchAdapter  # noqa: E402

SEED_MEMES = [
    {
        "slug": "san-bi-ling",
        "title": "三比零",
        "definition": "系列赛 3:0 横扫，常用来形容一边倒或「来都来了不如体面点」。",
        "origin_story": "KPL 常规赛/季后赛高频比分叙事，评论区模板句。",
        "category": "赛果",
        "hotness": 80,
        "is_ai_assisted": False,
        "moderation_status": "approved",
    },
    {
        "slug": "chao-gui",
        "title": "超鬼",
        "definition": "对线/团战表现极差，KDA 难看到离谱时的统称。",
        "origin_story": "观众弹幕与虎扑串子常用黑话，后被解说偶尔玩梗引用。",
        "category": "选手",
        "hotness": 90,
        "is_ai_assisted": False,
        "moderation_status": "approved",
    },
    {
        "slug": "jue-huo",
        "title": "绝活",
        "definition": "选手招牌英雄或独特理解，ban 掉等于砍半条命。",
        "origin_story": "BP 环节「绝活被 ban」是赛后复盘与玩梗的经典入口。",
        "category": "BP",
        "hotness": 85,
        "is_ai_assisted": False,
        "moderation_status": "approved",
    },
    {
        "slug": "rang-er-zhui-san",
        "title": "让二追三",
        "definition": "先落后 0-2，再连下三局 3-2 翻盘。",
        "origin_story": "戏剧性系列赛叙事，二路解说最爱的剧本之一。",
        "category": "赛果",
        "hotness": 88,
        "is_ai_assisted": False,
        "moderation_status": "approved",
    },
    {
        "slug": "ai-chuan-zi-bot",
        "title": "AI串子bot",
        "definition": "本站官方 AI 角色：明确标注 AI，只负责赛后整活，不装真人。",
        "origin_story": "为合规与产品差异化设计的 bot 人设，替代「假用户暖场」。",
        "category": "站务",
        "hotness": 70,
        "is_ai_assisted": True,
        "moderation_status": "approved",
    },
    {
        "slug": "sai-hou-huang-jin-30fen",
        "title": "赛后黄金 30 分钟",
        "definition": "比赛刚结束时梗的产出与传播效率最高的时间窗。",
        "origin_story": "垂直社区运营共识；本产品把自动化生梗对准这个窗口。",
        "category": "站务",
        "hotness": 75,
        "is_ai_assisted": True,
        "moderation_status": "approved",
    },
]


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
    print(f"upsert memes x{len(SEED_MEMES)}")
    # memes table: slug unique — but upsert needs primary key or unique cols
    db.upsert("memes", SEED_MEMES, on_conflict="slug")

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
                        "start_time": x.get("start_time"),
                        "end_time": x.get("end_time"),
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
                    "start_time": m.get("start_time"),
                    "end_time": m.get("end_time"),
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
