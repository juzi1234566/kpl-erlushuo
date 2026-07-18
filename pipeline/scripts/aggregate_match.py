"""跨解说综合评：汇总一场比赛所有解说的观点 → AI 对每队/每人写醒目整体评价。

用更强的模型（默认 deepseek-reasoner）生成，输出 data/insights/_match_{id}.json。

用法：python -m scripts.aggregate_match --match-id 2026071703
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

SYSTEM = """你是资深电竞主编。多位二路解说对同一场 KPL 比赛的观点已经结构化，
现在写【AI 综合评】——读者只看这一块就知道这场比赛谁强谁弱、争议在哪。
写作要求：
- 每段评价 50-90 字：醒目、具体、直给结论；概括各家共识，有分歧就点明分歧
- 禁止「解说认为/XX说」框架；禁止嘲讽和人身攻击，批评客观委婉
- 语言干净有力，不堆黑话
- 只依据给你的观点素材，不编造
输出 JSON：
{
  "headline": "整场一句话定调，≤30字",
  "bp_read": "两队 BP 思路对比，80-140字：各自体系怎么打才占优、谁的 BP 更成功、版本理解差异",
  "pace": "整场节奏解读，80-140字：前中后期各自节奏特征、局势通常在哪个阶段转折、胜负手在哪",
  "overall": "整场综合评，80-140字：比赛质量、最大看点、解说团整体态度",
  "teams": [{"name": "...", "text": "50-90字综合评", "consensus": "一致好评|一致差评|存在分歧|评价中性"}],
  "players": [{"name": "...", "text": "50-90字综合评（含跨局表现与各家分歧）", "consensus": "同上"}],
  "controversy": "最大争议点一句话（没有就空字符串）"
}"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--model", default=os.getenv("AGGREGATE_MODEL") or "deepseek-reasoner")
    args = parser.parse_args()

    from ai.deepseek_client import DeepSeekClient, parse_json_lenient
    from db.supabase_client import SupabaseRest
    from vod_pipeline import _match_meta

    insights_dir = ROOT / "data" / "insights"
    sources = []
    for f in sorted(insights_dir.glob("*.json")):
        if f.name.startswith("_") or f.name.endswith(".orig.json"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if str(d.get("match_id")) != str(args.match_id):
            continue
        core = d.get("series") or d  # 新格式取系列层
        sources.append(
            {
                "解说": d.get("caster"),
                "整场": core.get("overall"),
                "战队": core.get("teams"),
                "选手": core.get("players"),
                "败因": core.get("blame"),
            }
        )
    if len(sources) < 1:
        print("该比赛没有可汇总的解说观点")
        sys.exit(1)

    db = SupabaseRest()
    meta = _match_meta(db, args.match_id)
    user = json.dumps({"比赛信息": meta, "各解说观点": sources}, ensure_ascii=False)

    client = DeepSeekClient(timeout=600.0)
    print(f"综合 {len(sources)} 位解说观点，模型 {args.model} …")
    text, usage = client.chat(system=SYSTEM, user=user, temperature=0.5, model=args.model)
    data = parse_json_lenient(text)
    if not isinstance(data, dict):
        print("综合评输出无效")
        sys.exit(1)

    out = insights_dir / f"_match_{args.match_id}.json"
    payload = {
        "match_id": str(args.match_id),
        "model": args.model,
        "caster_count": len(sources),
        **data,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已生成 {out.name} | tokens {usage.get('prompt_tokens')}+{usage.get('completion_tokens')}")
    print("定调:", data.get("headline"))
    for t in data.get("teams") or []:
        print(f"【{t.get('name')}】{t.get('consensus')} - {str(t.get('text'))[:60]}")


if __name__ == "__main__":
    main()
