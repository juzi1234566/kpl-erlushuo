"""规则找梗点：比让 AI 从裸数据瞎找靠谱。"""

from __future__ import annotations

from typing import Any


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def extract_match_signals(match: dict[str, Any]) -> list[dict[str, Any]]:
    """系列赛（BO）级信号。"""
    signals: list[dict[str, Any]] = []
    camp1 = match.get("camp1") or {}
    camp2 = match.get("camp2") or {}
    s1 = int(_num(camp1.get("score")))
    s2 = int(_num(camp2.get("score")))
    t1 = camp1.get("team_abbreviation") or camp1.get("team_name") or "A"
    t2 = camp2.get("team_abbreviation") or camp2.get("team_name") or "B"
    bo = int(_num(match.get("bo"), 5))

    if {s1, s2} == {3, 0} or (max(s1, s2) == 3 and min(s1, s2) == 0 and bo >= 5):
        winner = t1 if s1 > s2 else t2
        loser = t2 if s1 > s2 else t1
        signals.append(
            {
                "type": "sweep",
                "severity": "high",
                "summary": f"{winner} 3:0 横扫 {loser}",
                "teams": [t1, t2],
                "score": f"{s1}:{s2}",
            }
        )

    if {s1, s2} == {3, 2}:
        signals.append(
            {
                "type": "full_bo",
                "severity": "medium",
                "summary": f"{t1} vs {t2} 打满五局 {s1}:{s2}",
                "teams": [t1, t2],
                "score": f"{s1}:{s2}",
            }
        )

    # 让二追三：一方先输 0-2 再 3-2 —— 仅有最终比分时无法严格判定，留给 battle 序列补强
    if max(s1, s2) == 3 and min(s1, s2) == 2:
        signals.append(
            {
                "type": "close_series",
                "severity": "medium",
                "summary": f"胶着大战 {t1} {s1}:{s2} {t2}",
                "teams": [t1, t2],
            }
        )

    return signals


def extract_battle_signals(battle: dict[str, Any]) -> list[dict[str, Any]]:
    """单局信号：极端 KDA / 经济碾压 / MVP 高光 / 绝活 ban 等。"""
    signals: list[dict[str, Any]] = []
    camp1 = battle.get("camp1") or {}
    camp2 = battle.get("camp2") or {}
    g1 = _num(camp1.get("gold"))
    g2 = _num(camp2.get("gold"))
    if g1 and g2:
        diff = abs(g1 - g2)
        if diff >= 8000:
            rich = camp1 if g1 > g2 else camp2
            poor = camp2 if g1 > g2 else camp1
            signals.append(
                {
                    "type": "gold_stomp",
                    "severity": "high" if diff >= 12000 else "medium",
                    "summary": (
                        f"{rich.get('team_abbreviation') or rich.get('team_name')} "
                        f"经济领先 {int(diff)} "
                        f"（{int(g1)} vs {int(g2)}）"
                    ),
                    "gold_diff": int(diff),
                }
            )

    for p in battle.get("battle_player_list") or []:
        k = int(_num(p.get("kill_num")))
        d = int(_num(p.get("death_num")))
        a = int(_num(p.get("assist_num")))
        name = p.get("actual_player_name") or p.get("player_name") or "选手"
        hero = p.get("hero_name") or "?"
        if d >= 5 and k == 0:
            signals.append(
                {
                    "type": "extreme_kda",
                    "severity": "high",
                    "summary": f"{name} {hero} {k}/{d}/{a} 超鬼",
                    "player": name,
                    "hero": hero,
                    "kda": f"{k}/{d}/{a}",
                }
            )
        if k >= 8 and d <= 1:
            signals.append(
                {
                    "type": "carry_kda",
                    "severity": "high",
                    "summary": f"{name} {hero} {k}/{d}/{a} 狂暴输出",
                    "player": name,
                    "hero": hero,
                    "kda": f"{k}/{d}/{a}",
                }
            )
        if p.get("is_mvp") in (1, True, "1"):
            score = _num(p.get("mvp_score"))
            if score >= 10:
                signals.append(
                    {
                        "type": "mvp_god",
                        "severity": "medium",
                        "summary": f"MVP {name} {hero} 评分 {score}",
                        "player": name,
                        "hero": hero,
                        "mvp_score": score,
                    }
                )
        rate = _num(p.get("hurt_to_hero_total_rate") or p.get("hurt_total_rate"))
        if rate >= 0.35:
            signals.append(
                {
                    "type": "damage_share",
                    "severity": "medium",
                    "summary": f"{name} {hero} 输出占比 {rate:.0%}",
                    "player": name,
                    "hero": hero,
                    "damage_rate": rate,
                }
            )

    bans = [
        x
        for x in (battle.get("bp_list") or [])
        if x.get("is_ban_or_pick") in (0, "0", False)
    ]
    # 同一英雄被 ban 两次（双方都 ban）——少见，记一下
    ban_names = [str(x.get("hero_name") or "") for x in bans]
    for name in set(ban_names):
        if name and ban_names.count(name) >= 2:
            signals.append(
                {
                    "type": "double_ban",
                    "severity": "medium",
                    "summary": f"{name} 被双边 ban",
                    "hero": name,
                }
            )

    win_camp = battle.get("win_camp")
    k1 = _num(camp1.get("kill_num"))
    k2 = _num(camp2.get("kill_num"))
    if win_camp and abs(k1 - k2) >= 10:
        signals.append(
            {
                "type": "kill_gap",
                "severity": "medium",
                "summary": f"人头差 {int(abs(k1 - k2))}（{int(k1)}:{int(k2)}）",
                "kills": f"{int(k1)}:{int(k2)}",
            }
        )

    # 去重（同 type+summary）
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for s in signals:
        key = f"{s.get('type')}|{s.get('summary')}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)
    return uniq


def rank_signals(signals: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    weight = {"high": 3, "medium": 2, "low": 1}
    return sorted(
        signals,
        key=lambda s: weight.get(str(s.get("severity")), 0),
        reverse=True,
    )[:limit]
