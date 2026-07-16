"""拉单局详情 + 打印梗点信号 + mock 生梗。"""

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

from ai.meme_generator import MemeGenerator  # noqa: E402
from signals.meme_signals import extract_battle_signals, rank_signals  # noqa: E402
from sources.pvp_match_adapter import PvpMatchAdapter  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--battle-id", required=True)
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"))
    args = parser.parse_args()

    with PvpMatchAdapter(raw_dir=Path(args.raw_dir)) as api:
        battle = api.get_battle(args.battle_id)

    signals = rank_signals(extract_battle_signals(battle))
    print("=== 梗点信号 ===")
    print(json.dumps(signals, ensure_ascii=False, indent=2))

    camp1 = battle.get("camp1") or {}
    camp2 = battle.get("camp2") or {}
    meta = {
        "battle_id": battle.get("battle_id"),
        "team_a": camp1.get("team_abbreviation") or camp1.get("team_name"),
        "team_b": camp2.get("team_abbreviation") or camp2.get("team_name"),
        "win_camp": battle.get("win_camp"),
        "duration_ms": battle.get("game_duration"),
    }
    result = MemeGenerator().generate(match_meta=meta, signals=signals)
    print("=== 生梗结果 ===")
    print(json.dumps(
        {
            "model": result.model,
            "error": result.error,
            "published": result.published,
            "review_pool": result.review_pool,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
