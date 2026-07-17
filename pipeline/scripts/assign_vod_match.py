"""待定池人工指派：把视频绑定到比赛并触发下载。

用法：
  python -m scripts.assign_vod_match --list                     # 看待定池
  python -m scripts.assign_vod_match --bvid BVxxx --match-id 2026061701
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db.supabase_client import SupabaseRest  # noqa: E402
from worker import LocalJobQueue  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--bvid")
    parser.add_argument("--match-id")
    args = parser.parse_args()

    db = SupabaseRest()

    if args.list or not (args.bvid and args.match_id):
        rows = db.select(
            "vod_sources",
            "select=bvid,title,up_name,pubdate,match_id,match_confidence&needs_review=eq.true&order=pubdate.desc&limit=50",
        )
        if not rows:
            print("待定池为空")
        for r in rows:
            print(f"{r['bvid']} | {r.get('up_name')} | {(r.get('title') or '')[:50]} | 猜测={r.get('match_id')} conf={r.get('match_confidence')}")
        if not (args.bvid and args.match_id):
            return

    db.upsert(
        "vod_sources",
        [
            {
                "bvid": args.bvid,
                "match_id": args.match_id,
                "match_confidence": 1.0,
                "match_method": "manual",
                "needs_review": False,
            }
        ],
        on_conflict="bvid",
    )
    queue = LocalJobQueue(ROOT / "data" / "jobs.json")
    queue.enqueue(
        {
            "id": str(uuid.uuid4()),
            "kind": "vod_download",
            "bvid": args.bvid,
            "status": "pending",
            "attempts": 0,
            "created_at": datetime.now().isoformat(),
        }
    )
    print(f"已指派 {args.bvid} → {args.match_id}，下载任务已入队")


if __name__ == "__main__":
    main()
