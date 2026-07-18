"""视频标题 → 比赛匹配：从二路视频标题识别对阵双方与日期，猜测对应场次。

规则：
1. 标题恰好命中 2 支战队（按别名表），否则进待定池
2. 日期优先取标题（7月16日 / 7.16 等），否则用发布时间前 0-2 天窗口
3. 在已完赛场次中找对阵+时间窗匹配；唯一命中 confidence 0.9
4. confidence < 0.8 → needs_review，不自动进下游
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

# team_id → 别名（全大写比较；中文原样）。手工维护，新赛季换队时更新。
TEAM_ALIASES: dict[str, list[str]] = {
    "10016": ["佛山DRG", "DRG"],
    "10017": ["广州TTG", "TTG"],
    "10003": ["北京WB", "WB", "北京wb", "诸葛wb"],
    "10006": ["武汉eStarPro", "ESTAR", "ES", "武汉ES", "E星", "estar"],
    "10001": ["重庆狼队", "狼队", "WOLVES", "重庆狼"],
    "10005": ["KSG", "苏州KSG"],
    "10910": ["WST", "无锡WST"],
    "10018": ["济南RW侠", "RW侠", "RW", "厄运小姐"],
    "10010": ["西安WE", "WE"],
    "10028": ["长沙TES.A", "TES.A", "TESA", "长沙TES"],
    "10031": ["杭州LGD.NBW", "LGD.NBW", "LGD", "LGD大鹅"],
    "10009": ["上海RNG.M", "RNG.M", "RNGM", "RNG"],
    "10002": ["上海EDG.M", "EDG.M", "EDGM", "EDG"],
    "10020": ["北京JDG", "JDG"],
    "12202": ["SYG", "山东SYG"],
    "10027": ["成都AG超玩会", "AG超玩会", "AG", "超玩会", "成都AG"],
    "10007": ["南通Hero久竞", "HERO久竞", "HERO", "久竞", "hero"],
    "10008": ["深圳DYG", "DYG"],
}

# 长别名优先匹配，避免 "WB" 抢先命中 "北京WB" 之类
_ALIAS_INDEX: list[tuple[str, str]] = sorted(
    ((alias.upper(), tid) for tid, aliases in TEAM_ALIASES.items() for alias in aliases),
    key=lambda x: -len(x[0]),
)

_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]"),
    re.compile(r"(\d{1,2})[.\-/](\d{1,2})(?![.\-/\d])"),
]


@dataclass
class MatchGuess:
    match_id: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"
    teams_found: list[str] = field(default_factory=list)  # team_id 列表
    note: str = ""


def find_teams_in_title(title: str) -> list[str]:
    """返回标题中命中的 team_id（去重、按出现位置排序）。"""
    upper = title.upper()
    hits: dict[str, int] = {}
    consumed: list[tuple[int, int]] = []
    for alias, tid in _ALIAS_INDEX:
        start = 0
        while True:
            idx = upper.find(alias, start)
            if idx < 0:
                break
            span = (idx, idx + len(alias))
            # 与更长别名的已占位置重叠则跳过（"北京WB" 占了就别再算 "WB"）
            if any(not (span[1] <= s or span[0] >= e) for s, e in consumed):
                start = idx + 1
                continue
            consumed.append(span)
            if tid not in hits or idx < hits[tid]:
                hits[tid] = idx
            start = idx + len(alias)
    return [tid for tid, _ in sorted(hits.items(), key=lambda kv: kv[1])]


def extract_title_date(title: str, ref_year: int) -> Optional[datetime]:
    for pat in _DATE_PATTERNS:
        m = pat.search(title)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                try:
                    return datetime(ref_year, month, day)
                except ValueError:
                    return None
    return None


def _parse_ts(value: Any) -> Optional[datetime]:
    """matches.start_time → 北京时间 naive datetime。

    注意：官方接口给的就是北京时间字面量，入库时被打上了 +00:00 后缀——
    所以这里按【字面量】读取，绝不做时区换算（fmtTime 同理）。
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))  # 本机即东八区
    s = str(value)
    if s.isdigit():
        return datetime.fromtimestamp(int(s))
    s = s.replace("Z", "").split("+")[0]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def guess_match(
    title: str,
    pubdate: datetime,
    matches: list[dict[str, Any]],
) -> MatchGuess:
    """matches：需含 id / team1_id / team2_id / status / start_time。"""
    teams = find_teams_in_title(title)
    if len(teams) != 2:
        return MatchGuess(
            teams_found=teams,
            note=f"标题命中 {len(teams)} 支战队，需恰好 2 支",
        )

    pair = frozenset(teams)
    title_date = extract_title_date(title, pubdate.year)
    if title_date:
        window = (title_date - timedelta(hours=6), title_date + timedelta(hours=30))
        method_hint = "title_teams_date"
    else:
        # 二路视频一般当天或 1-2 天内发布
        window = (pubdate - timedelta(days=2, hours=12), pubdate + timedelta(hours=6))
        method_hint = "title_teams_pubdate"

    hits: list[tuple[datetime, dict[str, Any]]] = []
    for m in matches:
        if m.get("status") != 2:  # 只匹配已完赛
            continue
        if frozenset([str(m.get("team1_id")), str(m.get("team2_id"))]) != {str(t) for t in pair}:
            continue
        st = _parse_ts(m.get("start_time"))
        if st is None:
            continue
        if window[0] <= st <= window[1]:
            hits.append((st, m))

    if not hits:
        return MatchGuess(teams_found=teams, note="对阵命中但时间窗内无完赛场次")
    if len(hits) == 1:
        return MatchGuess(
            match_id=str(hits[0][1]["id"]),
            confidence=0.9,
            method=method_hint,
            teams_found=teams,
        )
    # 同窗多场（罕见）：取时间最近发布时间的，降置信
    hits.sort(key=lambda x: abs((x[0] - pubdate).total_seconds()))
    return MatchGuess(
        match_id=str(hits[0][1]["id"]),
        confidence=0.6,
        method=method_hint + "_ambiguous",
        teams_found=teams,
        note=f"时间窗内 {len(hits)} 场同对阵，取最近",
    )
