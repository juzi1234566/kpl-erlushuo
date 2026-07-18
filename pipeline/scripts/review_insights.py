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
    # 大文件分块终审：逐局 + 系列层各审一次，避免超出输出上限
    if isinstance(payload.get("games"), list) and len(payload["games"]) > 1:
        fixes: list[str] = []
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        reviewed = dict(payload)
        new_games = []
        for g in payload["games"]:
            sub = {"games": [g]}
            r, fx, u = extractor.review_payload(payload=sub, match_meta=meta, roster=roster)
            usage["prompt_tokens"] += u["prompt_tokens"]
            usage["completion_tokens"] += u["completion_tokens"]
            new_games.append((r.get("games") or [g])[0])
            fixes.extend(f"第{g.get('game_no')}局: {x}" for x in fx)
        reviewed["games"] = new_games
        if payload.get("series"):
            sub = {"series": payload["series"]}
            r, fx, u = extractor.review_payload(payload=sub, match_meta=meta, roster=roster)
            usage["prompt_tokens"] += u["prompt_tokens"]
            usage["completion_tokens"] += u["completion_tokens"]
            reviewed["series"] = r.get("series") or payload["series"]
            fixes.extend(f"系列层: {x}" for x in fx)
    else:
        reviewed, fixes, usage = extractor.review_payload(payload=payload, match_meta=meta, roster=roster)

    # 金句质检：错字修正/劣质删除（宁缺毋滥）
    from ai.insight_extractor import ESPORTS_TERMS

    glossary = sorted(
        {p["player"] for p in roster} | {p["team"] for p in roster} | set(ESPORTS_TERMS)
    )
    qc_stats = [0, 0]
    containers = reviewed.get("games") if isinstance(reviewed.get("games"), list) else [reviewed]
    for g in containers:
        gq = g.get("golden_quotes") or []
        if gq:
            kept, _ = extractor.qc_golden_quotes(gq, glossary)
            qc_stats[0] += len(gq)
            qc_stats[1] += len(kept)
            g["golden_quotes"] = kept
    if qc_stats[0]:
        fixes.append(f"金句质检：{qc_stats[0]} 条 → 保留 {qc_stats[1]} 条")

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
