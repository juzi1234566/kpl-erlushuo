"""观点数据上云：本地 insights JSON → Supabase（vod_sources + commentary_insights + match_aggregates）。

- 幂等：vod 按 (bvid,page_start) upsert；行按 (vod_id,game_no,subject_type,subject_name) upsert
- 默认 status=approved（内容已过校对+终审+质检三层 AI 审）；--pending 改为人工审

用法：
  python -m scripts.ingest_insights --all
  python -m scripts.ingest_insights --match-id 2026071703
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

INSIGHTS_DIR = ROOT / "data" / "insights"


def clamp_rating(v: Any) -> Optional[int]:
    try:
        return max(1, min(5, int(v)))
    except (TypeError, ValueError):
        return None


def section_rows(d: dict, *, vod_id: str, match_id: str, game_no: int, status: str) -> list[dict]:
    """一份（系列层或单局）结构 → commentary_insights 行。与前端 sectionRows 同构。"""
    rows: list[dict] = []

    def add(subject_type: str, subject_name: str, item: Optional[dict], extra: dict) -> None:
        if not item:
            return
        summary = (
            item.get("headline") or item.get("verdict") or item.get("summary")
            or (item.get("points") or [""])[0] or ""
        )
        quotes = item.get("quotes") or []
        if not summary and not quotes:
            return
        sentiment = item.get("sentiment")
        if sentiment not in ("好评", "差评", "中立", "复杂"):
            sentiment = "中立"
        rows.append(
            {
                "vod_id": vod_id,
                "match_id": match_id,
                "game_no": game_no,
                "subject_type": subject_type,
                "subject_name": subject_name,
                "sentiment": sentiment,
                "rating": clamp_rating(item.get("rating")),
                "summary": str(summary)[:2000],
                "quotes": quotes,
                "extra": extra,
                "ai_risk": item.get("risk"),
                "status": status,
            }
        )

    if d.get("bp"):
        add("bp", "BP与阵容", d["bp"], {
            "headline": d["bp"].get("headline") or "",
            "points": d["bp"].get("points") or [],
            "predictions": d["bp"].get("predictions") or [],
        })
    if d.get("flow"):
        flow = d["flow"]
        flow_summary = "\n".join(
            f"【{label}】{flow.get(key)}"
            for key, label in (("early", "前期"), ("mid", "中期"), ("late", "后期"))
            if flow.get(key)
        )
        add("flow", "局势走向", {**flow, "summary": flow_summary}, {
            "turning_points": flow.get("turning_points") or [],
        })
    if d.get("overall"):
        add("overall", "整场比赛", d["overall"], {
            "headline": d["overall"].get("headline") or "",
            "points": d["overall"].get("points") or [],
            "games_brief": d.get("games_brief") or [],
        })
    for t in d.get("teams") or []:
        name = (t.get("name") or "").strip()
        if name:
            add("team", name, t, {"verdict": t.get("verdict") or "", "points": t.get("points") or []})
    for p in d.get("players") or []:
        name = (p.get("name") or "").strip()
        if name:
            add("player", name, p, {
                "verdict": p.get("verdict") or "",
                "points": p.get("points") or [],
                "highlight": p.get("highlight") or "",
                "lowlight": p.get("lowlight") or "",
            })
    if d.get("blame"):
        add("blame", "赛后复盘", {**d["blame"], "summary": d["blame"].get("headline")}, {
            "headline": d["blame"].get("headline") or "",
            "main": d["blame"].get("main") or [],
        })
    if d.get("golden_quotes"):
        add("golden", "金句时刻", {
            "summary": "金句", "sentiment": "中立", "quotes": d["golden_quotes"],
        }, {})
    return rows


def ingest_file(db, path: Path, *, status: str) -> int:
    d = json.loads(path.read_text(encoding="utf-8"))
    match_id = str(d["match_id"])
    pages = d.get("pages") or [1]

    vod_row = {
        "bvid": d["bvid"],
        "page_start": pages[0],
        "page_end": pages[-1],
        "caster_name": d.get("caster"),
        "up_name": d.get("caster"),
        "title": f"{d.get('caster')} 二路解说",
        "match_id": match_id,
        "match_confidence": 1.0,
        "match_method": "manual",
        "needs_review": False,
        "audio_status": "done",
        "transcript_status": "done",
        "analysis_status": "done",
    }
    db.upsert("vod_sources", [vod_row], on_conflict="bvid,page_start")
    got = db.select("vod_sources", f"select=id&bvid=eq.{d['bvid']}&page_start=eq.{pages[0]}")
    vod_id = got[0]["id"]

    rows: list[dict] = []
    if isinstance(d.get("games"), list):
        series = d.get("series") or {}
        rows += section_rows(
            {**series, "games_brief": series.get("games_brief")},
            vod_id=vod_id, match_id=match_id, game_no=0, status=status,
        )
        for g in d["games"]:
            g_rows = section_rows(g, vod_id=vod_id, match_id=match_id, game_no=int(g.get("game_no") or 1), status=status)
            # 记录该局分P页码，前端跳转用
            for r in g_rows:
                r["extra"] = {**r["extra"], "page": g.get("page")}
            rows += g_rows
    else:
        # 旧格式：单局既当系列层也当第 1 局
        rows += section_rows(d, vod_id=vod_id, match_id=match_id, game_no=0, status=status)
        rows += section_rows(d, vod_id=vod_id, match_id=match_id, game_no=1, status=status)

    for i in range(0, len(rows), 50):
        db.upsert("commentary_insights", rows[i : i + 50], on_conflict="vod_id,game_no,subject_type,subject_name")
    return len(rows)


def ingest_aggregate(db, match_id: str) -> bool:
    p = INSIGHTS_DIR / f"_match_{match_id}.json"
    if not p.exists():
        return False
    d = json.loads(p.read_text(encoding="utf-8"))
    db.upsert(
        "match_aggregates",
        [
            {
                "match_id": match_id,
                "payload": {k: v for k, v in d.items() if k not in ("match_id", "model", "caster_count")},
                "model": d.get("model"),
                "caster_count": d.get("caster_count"),
            }
        ],
        on_conflict="match_id",
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--match-id")
    parser.add_argument("--pending", action="store_true", help="入库为待审状态（默认直接上架）")
    args = parser.parse_args()
    status = "pending" if args.pending else "approved"

    from db.supabase_client import SupabaseRest

    db = SupabaseRest()
    files = sorted(
        f for f in INSIGHTS_DIR.glob("*.json")
        if not f.name.startswith("_") and not f.name.endswith(".orig.json")
    )
    match_ids: set[str] = set()
    total = 0
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        mid = str(d.get("match_id"))
        if args.match_id and mid != str(args.match_id):
            continue
        n = ingest_file(db, f, status=status)
        match_ids.add(mid)
        total += n
        print(f"{f.name}: {n} 行 ✅")

    for mid in sorted(match_ids):
        if ingest_aggregate(db, mid):
            print(f"综合评 {mid} ✅")
    print(f"完成：{len(match_ids)} 场比赛 / {total} 行观点（状态 {status}）")


if __name__ == "__main__":
    main()
