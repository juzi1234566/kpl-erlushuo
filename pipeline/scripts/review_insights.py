"""对已生成的赛评 JSON 做 AI 终审（事实核对+文字修订），原地更新并备份。

用法：
  python -m scripts.review_insights --file data/insights/BV1TcNd6UEV6_p1-5.json
  python -m scripts.review_insights --all          # 审 data/insights 下全部
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def review_one(path: Path) -> None:
    from ai.insight_extractor import InsightExtractor
    from db.supabase_client import SupabaseRest
    from vod_pipeline import _match_meta, match_roster_and_hotwords

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("_reviewed"):
        print(f"{path.name}: 已终审过，跳过")
        return
    db = SupabaseRest()
    meta = _match_meta(db, str(payload["match_id"]))
    meta["caster"] = payload.get("caster")
    roster, _ = match_roster_and_hotwords(str(payload["match_id"]))

    extractor = InsightExtractor()
    reviewed, fixes, usage = extractor.review_payload(payload=payload, match_meta=meta, roster=roster)
    reviewed["_reviewed"] = True

    backup = path.with_suffix(".orig.json")
    if not backup.exists():
        shutil.copy(path, backup)
    path.write_text(json.dumps(reviewed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name}: 终审完成，修订 {len(fixes)} 处 | tokens {usage['prompt_tokens']}+{usage['completion_tokens']}")
    for f in fixes[:12]:
        print(f"  - {f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        files = sorted((ROOT / "data" / "insights").glob("*.json"))
        files = [f for f in files if not f.name.endswith(".orig.json")]
    elif args.file:
        files = [ROOT / args.file if not Path(args.file).is_absolute() else Path(args.file)]
    else:
        parser.error("需要 --file 或 --all")
        return

    for f in files:
        try:
            review_one(f)
        except Exception as exc:  # noqa: BLE001
            print(f"{f.name}: 终审失败 {exc}")


if __name__ == "__main__":
    main()
