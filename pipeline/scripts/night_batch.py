"""夜班批处理：一条命令处理当天全部完赛比赛的二路观点。

流程：刷新赛程 → 找当天完赛 → 定位合集视频 → 解析主播分P分组
  → 逐主播全链（转写用 SenseVoice 快速引擎）→ 终审 → 综合评

用法：
  python -m scripts.night_batch                 # 处理今天完赛
  python -m scripts.night_batch --date 2026-07-17
  python -m scripts.night_batch --match-id 2026071703   # 只处理指定场
  python -m scripts.night_batch --dry-run       # 只列计划不执行

睡前跑（Windows）：
  cd C:\\Users\\18413\\Desktop\\kpl-meme\\pipeline
  .venv\\Scripts\\python.exe -m scripts.night_batch
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

CONFIG_PATH = ROOT / "config" / "casters.json"
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")

_PART_RE = re.compile(r"^(.+?)\s*(\d+)$")


def ts() -> str:
    return time.strftime("%H:%M:%S")


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def parse_caster_groups(pages: list[dict]) -> dict[str, list[int]]:
    """分P标题「可温 1」→ {主播: [页码...]（按局序）}"""
    groups: dict[str, list[tuple[int, int]]] = {}
    for p in pages:
        m = _PART_RE.match((p.get("part") or "").strip())
        if not m:
            continue
        caster, game_no = m.group(1).strip(), int(m.group(2))
        groups.setdefault(caster, []).append((game_no, p["page"]))
    return {
        caster: [page for _, page in sorted(items)]
        for caster, items in groups.items()
    }


def run_step(args: list[str], log: Path) -> bool:
    """跑子命令，输出追加到日志。"""
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n===== {ts()} {' '.join(args)} =====\n")
        f.flush()
        proc = subprocess.run(
            [PYTHON, "-m", *args],
            cwd=str(ROOT),
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
        )
    return proc.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD，默认今天（北京时间）")
    parser.add_argument("--match-id", help="只处理这一场")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--engine", default="paraformer", choices=["paraformer", "sensevoice"])
    args = parser.parse_args()

    import os

    os.environ["ASR_ENGINE"] = args.engine

    cfg = load_config()
    log = ROOT / "data" / f"night_{time.strftime('%Y%m%d')}.log"
    print(f"[{ts()}] 夜班开始 | 引擎 {args.engine} | 日志 {log.name}", flush=True)

    from db.supabase_client import SupabaseRest
    from signals.vod_matcher import _parse_ts, guess_match
    from sources.bilibili_adapter import BilibiliAdapter

    # 1. 刷新赛程
    if not args.dry_run:
        print(f"[{ts()}] 刷新赛程…", flush=True)
        run_step(["scripts.sync_to_supabase"], log)

    db = SupabaseRest()
    matches = db.select("matches", "select=id,team1_id,team2_id,score1,score2,status,start_time&limit=500")

    # 2. 目标场次
    if args.match_id:
        targets = [m for m in matches if str(m["id"]) == str(args.match_id)]
    else:
        day = args.date or datetime.now().strftime("%Y-%m-%d")
        targets = []
        for m in matches:
            if m.get("status") != 2:
                continue
            st = _parse_ts(m.get("start_time"))
            if st and st.strftime("%Y-%m-%d") == day:
                targets.append(m)
    print(f"[{ts()}] 待处理完赛场次: {[m['id'] for m in targets]}", flush=True)
    if not targets:
        print("没有目标场次，收工", flush=True)
        return

    # 3. 逐场处理
    mid = int(cfg["collection_up_mid"])
    wanted = cfg.get("casters") or []
    max_casters = int(cfg.get("max_casters_per_match") or 6)
    max_games = int(cfg.get("max_games_per_caster") or 5)

    with BilibiliAdapter(raw_dir=ROOT / "data" / "raw") as api:
        try:
            videos = api.list_up_videos(mid, page_size=30)
        except Exception as exc:  # noqa: BLE001
            # B站风控（412）兜底：用最近一次成功的缓存列表
            cache = ROOT / "data" / "raw" / f"bili_space_{mid}_p1.json"
            if cache.exists():
                videos = json.loads(cache.read_text(encoding="utf-8"))
                print(f"[{ts()}] 空间接口失败（{exc}），使用缓存列表 {len(videos)} 条", flush=True)
            else:
                print(f"[{ts()}] 空间接口失败且无缓存：{exc}", flush=True)
                print("提示：浏览器登录 B站 后把 SESSDATA 填入 pipeline/.env 可大幅降低风控概率", flush=True)
                return

        for m in targets:
            match_id = str(m["id"])
            print(f"[{ts()}] ── 比赛 {match_id} ──", flush=True)

            # 定位该场的合集视频
            hit = None
            for v in videos:
                pub = datetime.fromtimestamp(int(v.get("created") or 0))
                g = guess_match(v.get("title") or "", pub, matches)
                if g.match_id == match_id and g.confidence >= 0.8:
                    hit = v
                    break
            if not hit:
                print(f"[{ts()}]   未找到对应合集视频，跳过", flush=True)
                continue
            bvid = hit["bvid"]
            print(f"[{ts()}]   视频 {bvid} | {hit.get('title', '')[:40]}", flush=True)

            api.sleep_politely()
            view = api.get_view(bvid)
            groups = parse_caster_groups(view.get("pages") or [])
            # 优先配置名单顺序，缺了就按合集顺序补足
            ordered = [c for c in wanted if c in groups]
            ordered += [c for c in groups if c not in ordered]
            ordered = ordered[:max_casters]
            print(f"[{ts()}]   主播: {ordered}（合集共 {len(groups)} 位）", flush=True)

            if args.dry_run:
                continue

            # 逐主播全链
            for caster in ordered:
                pages = groups[caster][:max_games]
                pages_arg = ",".join(str(p) for p in pages)
                print(f"[{ts()}]   ▶ {caster} P{pages_arg}", flush=True)
                ok = run_step(
                    [
                        "scripts.analyze_collection",
                        "--bvid", bvid,
                        "--pages", pages_arg,
                        "--caster", caster,
                        "--up-name", cfg.get("collection_up_name") or "",
                        "--mid", str(mid),
                        "--match-id", match_id,
                    ],
                    log,
                )
                print(f"[{ts()}]     {'✅' if ok else '❌ 失败，详见日志'}", flush=True)

            # 官方战绩
            print(f'[{ts()}]   官方战绩…', flush=True)
            run_step(['scripts.fetch_game_stats', '--match-id', match_id], log)

            # 终审 + 综合评 + 上云
            print(f"[{ts()}]   终审…", flush=True)
            run_step(["scripts.review_insights", "--all"], log)
            print(f"[{ts()}]   综合评…", flush=True)
            run_step(["scripts.aggregate_match", "--match-id", match_id], log)
            print(f"[{ts()}]   上云…", flush=True)
            run_step(["scripts.ingest_insights", "--match-id", match_id], log)
            print(f"[{ts()}]   比赛 {match_id} 完成", flush=True)

    print(f"[{ts()}] NIGHT_BATCH_DONE", flush=True)


if __name__ == "__main__":
    main()
