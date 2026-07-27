"""从已拉到的 battle JSON 汇总 hero_id → 英雄名 映射。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    raw = ROOT / "data" / "raw"
    mapping: dict[str, dict] = {}
    for path in raw.glob("battle_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for p in data.get("battle_player_list") or []:
            hid = str(p.get("hero_id"))
            if hid and hid not in mapping:
                mapping[hid] = {
                    "hero_id": hid,
                    "hero_name": p.get("hero_name"),
                    "hero_icon": p.get("hero_icon"),
                }
        for b in data.get("bp_list") or []:
            hid = str(b.get("hero_id"))
            if hid and hid not in mapping:
                mapping[hid] = {
                    "hero_id": hid,
                    "hero_name": b.get("hero_name"),
                    "hero_icon": b.get("hero_icon"),
                }
    out = ROOT / "data" / "hero_id_map.json"
    out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"heroes={len(mapping)} -> {out}")


if __name__ == "__main__":
    main()
