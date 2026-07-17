"""扫描信任 UP主 的新投稿 → 匹配比赛 → 入库 vod_sources → 达标者入队下载。

用法：
  python -m scripts.scan_up_videos                 # 扫全部 enabled UP
  python -m scripts.scan_up_videos --mid 12345     # 只扫一个（可未入库，用于试跑）
  python -m scripts.scan_up_videos --dry-run       # 只打印不落库
  python -m scripts.scan_up_videos --since-days 7  # 只看最近 N 天投稿（默认 7）
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db.supabase_client import SupabaseRest  # noqa: E402
from signals.vod_matcher import guess_match  # noqa: E402
from sources.bilibili_adapter import BilibiliAdapter  # noqa: E402
from worker import LocalJobQueue  # noqa: E402

CONFIDENCE_AUTO = 0.8  # 达到该置信度才自动进下游


def scan_one_up(
    api: BilibiliAdapter,
    db: SupabaseRest,
    queue: LocalJobQueue,
    *,
    mid: int,
    up_name: str,
    scan_keyword: str | None,
    matches: list[dict],
    known_bvids: set[str],
    since: datetime,
    dry_run: bool,
) -> int:
    videos = api.list_up_videos(mid, page_size=30)
    new_count = 0
    for v in videos:
        bvid = v.get("bvid")
        title = v.get("title") or ""
        pubdate = datetime.fromtimestamp(int(v.get("created") or 0))
        if pubdate < since:
            continue
        if not bvid or bvid in known_bvids:
            continue
        if scan_keyword and scan_keyword not in title:
            continue

        guess = guess_match(title, pubdate, matches)
        auto = guess.match_id is not None and guess.confidence >= CONFIDENCE_AUTO
        print(
            f"  [{'自动' if auto else '待定'}] {bvid} | {title[:44]} "
            f"| match={guess.match_id} conf={guess.confidence:.2f} {guess.note}"
        )
        if dry_run:
            continue

        # 详情补 aid/cid/duration（单 P 取第一 P）
        api.sleep_politely()
        view = api.get_view(bvid)
        pages = view.get("pages") or []
        row = {
            "bvid": bvid,
            "title": title,
            "up_name": up_name,
            "mid": mid,
            "aid": view.get("aid"),
            "cid": (pages[0].get("cid") if pages else view.get("cid")),
            "pubdate": pubdate.isoformat(),
            "duration_s": view.get("duration"),
            "cover_url": view.get("pic"),
            "match_id": guess.match_id,
            "match_confidence": guess.confidence,
            "match_method": guess.method,
            "needs_review": not auto,
            "subtitle_status": "pending",
        }
        if len(pages) > 1:
            # MVP 只处理单 P
            row["audio_status"] = "skipped"
            row["last_error"] = f"多P视频（{len(pages)}P），MVP 暂不处理"
        db.upsert("vod_sources", [row], on_conflict="bvid")
        known_bvids.add(bvid)
        new_count += 1

        if auto and len(pages) <= 1:
            queue.enqueue(
                {
                    "id": str(uuid.uuid4()),
                    "kind": "vod_download",
                    "bvid": bvid,
                    "status": "pending",
                    "attempts": 0,
                    "created_at": datetime.now().isoformat(),
                }
            )
    return new_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mid", type=int, help="只扫这个 UP（可未入 up_profiles）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since-days", type=int, default=7)
    args = parser.parse_args()

    db = SupabaseRest()
    queue = LocalJobQueue(ROOT / "data" / "jobs.json")
    since = datetime.now() - timedelta(days=args.since_days)

    if args.mid:
        ups = [{"mid": args.mid, "name": f"mid:{args.mid}", "scan_keyword": None}]
    else:
        ups = db.select("up_profiles", "select=mid,name,scan_keyword&enabled=eq.true")
    if not ups:
        print("up_profiles 为空：先在 Supabase 里插入信任 UP，或用 --mid 试跑")
        return

    matches = db.select("matches", "select=id,team1_id,team2_id,status,start_time&limit=500")
    existing = db.select("vod_sources", "select=bvid&limit=2000")
    known_bvids = {r["bvid"] for r in existing}
    print(f"UP 数：{len(ups)} | 已收录视频：{len(known_bvids)} | 完赛可匹配：{sum(1 for m in matches if m.get('status') == 2)}")

    total = 0
    with BilibiliAdapter(raw_dir=ROOT / "data" / "raw") as api:
        for up in ups:
            print(f"扫描 UP：{up['name']} (mid={up['mid']})")
            try:
                total += scan_one_up(
                    api,
                    db,
                    queue,
                    mid=int(up["mid"]),
                    up_name=up["name"],
                    scan_keyword=up.get("scan_keyword"),
                    matches=matches,
                    known_bvids=known_bvids,
                    since=since,
                    dry_run=args.dry_run,
                )
                if not args.dry_run and not args.mid:
                    db.upsert(
                        "up_profiles",
                        [{"mid": up["mid"], "name": up["name"], "last_scan_at": datetime.now().isoformat()}],
                        on_conflict="mid",
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"  UP {up['mid']} 扫描失败：{exc}")
            api.sleep_politely()

    print(f"新收录 {total} 条{'（dry-run 未落库）' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
