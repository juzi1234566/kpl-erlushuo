"""云端监听器：盯住 kpl二路 的空间，新二路合集视频一出现立即全链处理。

- 每 POLL_MINUTES 分钟拉一次投稿列表（带风控退避）
- 标题过滤（须含「二路」，排除第一视角等）→ 匹配已完赛场次
- 新视频 → 逐主播全链（转写/分析/终审/质检/综合评/战绩/上云）
- 状态存 data/watcher_state.json，幂等可随时重启

用法（服务器上由 systemd 常驻）：python -m scripts.watcher
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

CONFIG_PATH = ROOT / "config" / "casters.json"
STATE_PATH = ROOT / "data" / "watcher_state.json"
PYTHON = sys.executable

POLL_MINUTES = 10
MATCH_REFRESH_MINUTES = 60
BACKOFF_MINUTES = 30  # B站风控后的退避


def ts() -> str:
    return time.strftime("%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"processed_bvids": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def run_step(args: list[str]) -> bool:
    log(f"  $ {' '.join(args)}")
    proc = subprocess.run([PYTHON, "-m", *args], cwd=str(ROOT))
    return proc.returncode == 0


def main() -> None:
    from scripts.night_batch import parse_caster_groups  # 复用分P解析

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    mid = int(cfg["collection_up_mid"])
    must = cfg.get("video_must_contain") or []
    exclude = cfg.get("video_exclude") or []
    wanted = cfg.get("casters") or []
    max_casters = int(cfg.get("max_casters_per_match") or 6)
    max_games = int(cfg.get("max_games_per_caster") or 5)

    state = load_state()
    matches: list[dict] = []
    matches_at = 0.0

    log(f"监听启动 mid={mid} 每 {POLL_MINUTES} 分钟一轮")
    while True:
        try:
            from db.supabase_client import SupabaseRest
            from signals.vod_matcher import guess_match
            from sources.bilibili_adapter import BilibiliAdapter

            # 赛程缓存（每小时刷新一次，先 sync 再读）
            if time.time() - matches_at > MATCH_REFRESH_MINUTES * 60:
                run_step(["scripts.sync_to_supabase", "--skip-matches"])  # 联赛信息
                run_step(["scripts.sync_to_supabase"])  # 赛程
                db = SupabaseRest()
                matches = db.select(
                    "matches", "select=id,team1_id,team2_id,status,start_time&limit=500"
                )
                matches_at = time.time()
                log(f"赛程刷新：{sum(1 for m in matches if m.get('status') == 2)} 场完赛")

            with BilibiliAdapter(raw_dir=ROOT / "data" / "raw") as api:
                videos = api.list_up_videos(mid, page_size=15)

                for v in videos:
                    bvid = v.get("bvid")
                    title = v.get("title") or ""
                    if not bvid or bvid in state["processed_bvids"]:
                        continue
                    if must and not any(k in title for k in must):
                        continue
                    if any(k in title for k in exclude):
                        continue
                    pub = datetime.fromtimestamp(int(v.get("created") or 0))
                    g = guess_match(title, pub, matches)
                    if not g.match_id or g.confidence < 0.8:
                        continue

                    log(f"🆕 新视频 {bvid} → 比赛 {g.match_id} | {title[:40]}")
                    api.sleep_politely()
                    view = api.get_view(bvid)
                    groups = parse_caster_groups(view.get("pages") or [])
                    ordered = [c for c in wanted if c in groups]
                    ordered += [c for c in groups if c not in ordered]
                    ordered = ordered[:max_casters]
                    log(f"  主播: {ordered}（合集共 {len(groups)} 位）")

                    run_step(["scripts.fetch_game_stats", "--match-id", g.match_id])
                    for caster in ordered:
                        pages = groups[caster][:max_games]
                        run_step(
                            [
                                "scripts.analyze_collection",
                                "--bvid", bvid,
                                "--pages", ",".join(map(str, pages)),
                                "--caster", caster,
                                "--up-name", cfg.get("collection_up_name") or "",
                                "--mid", str(mid),
                                "--match-id", g.match_id,
                            ]
                        )
                    run_step(["scripts.review_insights", "--all"])
                    run_step(["scripts.aggregate_match", "--match-id", g.match_id])
                    run_step(["scripts.ingest_insights", "--match-id", g.match_id])

                    state["processed_bvids"].append(bvid)
                    state["processed_bvids"] = state["processed_bvids"][-200:]
                    save_state(state)
                    log(f"✅ {bvid} 处理完成并已上云")

            time.sleep(POLL_MINUTES * 60)
        except KeyboardInterrupt:
            log("手动停止")
            break
        except Exception as exc:  # noqa: BLE001
            log(f"⚠️ 本轮异常（{exc}），{BACKOFF_MINUTES} 分钟后重试")
            time.sleep(BACKOFF_MINUTES * 60)


if __name__ == "__main__":
    main()
