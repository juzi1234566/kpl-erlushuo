"""二路解说观点提取：带说话人标签的转写稿 → 详细结构化赛评。

产出维度（按观赛爽点设计）：
- BP 点评：双方教练禁选思路好坏、阵容强弱判断、赛前预测（含应验/打脸判定）
- 局势叙事：前期/中期/后期怎么发展、转折点在哪
- 战队与选手：全过程详细评价（不是一句话总结），高光与低谷
- 分锅：这把输在谁，解说怎么分锅
- 金句：值得单独拿出来的整活/毒奶/暴论原话

流程：map 分块提取候选 → reduce 归并成长文 → 风控过滤 → quote 回源校验。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from ai.deepseek_client import DeepSeekClient, parse_json_lenient
from asr.funasr_transcriber import Segment

CHUNK_CHARS = 6000
CHUNK_OVERLAP = 300
RISK_THRESHOLD = 6.0

MAP_SYSTEM = """你是电竞解说内容分析师。你收到王者荣耀职业比赛（KPL）二路解说的转写片段。
提取以下几类内容（宁多勿漏，reduce 阶段会归并）：
1. bp——BP/选人阶段的点评：ban 了什么放了什么、教练思路好坏、阵容强弱判断
2. prediction——胜负/局势预测：「这把稳了」「赢不了」之类的判断性发言
3. team_eval——对某支战队的评价（运营、团战、节奏）
4. player_eval——对某位选手的评价（操作、状态、决策、失误）
5. turning_point——关键转折点的点评（抢龙、团战、偷家等改变局势的时刻）
6. golden_quote——金句/整活/暴论/毒奶，单独听都有意思的原话
忽略：单纯的实况复述、与比赛无关的闲聊、广告口播。
只输出合法 JSON，不要 Markdown。"""

MAP_USER_TEMPLATE = """【比赛信息】
{match_meta}

【选手名单】（含本场所用英雄。转写是语音识别产物，人名/英雄名常有同音错字——
必须纠正对齐到名单；解说常用英雄名代指选手，请按名单换算成选手名）
{roster}

【转写片段】（格式：[毫秒时间戳] 文本）
{chunk}

输出 JSON 数组，每项：
{{
  "kind": "bp" | "prediction" | "team_eval" | "player_eval" | "turning_point" | "golden_quote",
  "subject": "涉及的战队或选手名（对齐名单；无明确对象填空字符串）",
  "point": "内容概括，保留细节",
  "quote": {{"text": "解说原话（转写原文的连续子串，15-80字）", "start_ms": 对应时间戳}}
}}
没有可提取内容就输出 []。"""

REDUCE_SYSTEM = """你是资深电竞编辑，给玩梗社区写「二路解说观点」赛评长文。读者是老观众，想看的是：
BP 谁亏了、局势怎么翻的、每个人从头到尾打得怎么样、锅是谁的、解说说了什么骚话。
写作要求：
- 详细、具体、有信息量：写清楚"什么时间发生了什么、解说怎么评的"，不许一句话敷衍
- 语言鲜活口语化，可以用电竞黑话（下饭、拉胯、carry、天秀），但转述不得辱骂/人身攻击
- 预测类内容要根据最终比分判定「应验」还是「打脸」——毒奶和预言家时刻是最大爆点，别放过
- quote 原样保留原话文本，不要改写
- 每个板块的 risk 自评 0-10：辱骂/造谣/隐私打高分
只输出合法 JSON，不要 Markdown。"""

REDUCE_USER_TEMPLATE = """【比赛信息】（含最终比分，用于判定预测应验/打脸）
{match_meta}

【选手名单】
{roster}

【候选素材】（同一位解说的完整视频分块提取）
{candidates}

输出 JSON（字数要求是底线不是上限，素材足够就写满）：
{{
  "bp": {{
    "summary": "BP与阵容点评，≥120字：双方 ban/pick 思路、哪边教练做得好、阵容强弱与体系判断",
    "rating": 教练BP整体打分1-5,
    "predictions": [{{"text": "预测原话", "start_ms": 0, "verdict": "应验" | "打脸" | "未验证", "note": "一句话说明"}}],
    "risk": 0-10
  }},
  "flow": {{
    "early": "前期局势，≥60字：对线/野区节奏、谁占优、解说怎么看",
    "mid": "中期局势，≥60字：资源团、节奏变化",
    "late": "后期与结局，≥60字：决胜团、怎么赢/输的",
    "turning_points": [{{"desc": "转折点描述", "quote": {{"text": "...", "start_ms": 0}}}}],
    "risk": 0-10
  }},
  "overall": {{"sentiment": "好评|差评|中立|复杂", "rating": 1-5,
              "summary": "整场观感总评，≥150字：这场比赛值不值得看、解说整体态度、最大看点"}},
  "teams": [{{"name": "...", "sentiment": "...", "rating": 1-5,
             "summary": "≥100字：这支队伍从BP到结束的整体表现、体系发挥、问题在哪",
             "quotes": [{{"text": "...", "start_ms": 0}}], "risk": 0-10}}],
  "players": [{{"name": "...", "sentiment": "...", "rating": 1-5,
               "summary": "≥100字全过程评价：前期表现→中后期变化→关键时刻的作为，引用解说的具体判断",
               "highlight": "本场高光（没有就空字符串）", "lowlight": "本场低谷（没有就空字符串）",
               "quotes": [最多3条], "risk": 0-10}}],
  "blame": {{"summary": "分锅分析，≥80字：这把（或劣势局）解说认为主要责任在谁、为什么",
            "main": [{{"name": "背锅对象", "reason": "锅的内容"}}], "risk": 0-10}},
  "golden_quotes": [{{"text": "金句原话", "start_ms": 0, "context": "什么场景下说的"}}],
  "risk": 整体0-10
}}
提示：素材里没有的板块（如没聊BP）对应字段给 null，不要编造。"""


@dataclass
class InsightResult:
    overall: Optional[dict[str, Any]] = None
    bp: Optional[dict[str, Any]] = None
    flow: Optional[dict[str, Any]] = None
    blame: Optional[dict[str, Any]] = None
    golden_quotes: list[dict[str, Any]] = field(default_factory=list)
    teams: list[dict[str, Any]] = field(default_factory=list)
    players: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_map_outputs: list[str] = field(default_factory=list)
    raw_reduce_output: str = ""
    error: Optional[str] = None


class InsightExtractor:
    def __init__(self, client: Optional[DeepSeekClient] = None) -> None:
        self.client = client or DeepSeekClient(timeout=300.0)

    # ---------- 主入口 ----------

    def extract(
        self,
        *,
        segments: list[Segment],
        speaker_map: dict[str, str],
        match_meta: dict[str, Any],
        roster: Optional[list[dict[str, Any]]] = None,
    ) -> InsightResult:
        up_segments = [s for s in segments if speaker_map.get(s.speaker) == "up"]
        if not up_segments:
            return InsightResult(error="没有归属为 UP主 的发言段")
        if not self.client.configured:
            return InsightResult(error="DEEPSEEK_API_KEY 未配置")

        result = InsightResult(model=self.client.model)
        roster = roster or []
        try:
            candidates = self._map_phase(up_segments, match_meta, roster, result)
            if not candidates:
                result.error = "未提取到评价性内容"
                return result
            self._reduce_phase(candidates, match_meta, roster, result)
            self._verify_quotes(result, up_segments)
            self._risk_filter(result)
        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)
        return result

    # ---------- map ----------

    def _chunks(self, segments: list[Segment]) -> list[str]:
        lines = [f"[{s.start_ms}] {s.text}" for s in segments]
        chunks: list[str] = []
        cur: list[str] = []
        size = 0
        for line in lines:
            cur.append(line)
            size += len(line)
            if size >= CHUNK_CHARS:
                chunks.append("\n".join(cur))
                tail: list[str] = []
                tail_size = 0
                for prev in reversed(cur):
                    tail_size += len(prev)
                    tail.insert(0, prev)
                    if tail_size >= CHUNK_OVERLAP:
                        break
                cur = tail
                size = tail_size
        if cur:
            chunks.append("\n".join(cur))
        return chunks

    def _map_phase(
        self,
        segments: list[Segment],
        match_meta: dict[str, Any],
        roster: list[dict[str, Any]],
        result: InsightResult,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for chunk in self._chunks(segments):
            user = MAP_USER_TEMPLATE.format(
                match_meta=json.dumps(match_meta, ensure_ascii=False),
                roster=json.dumps(roster, ensure_ascii=False),
                chunk=chunk,
            )
            text, usage = self.client.chat(system=MAP_SYSTEM, user=user, temperature=0.3)
            result.raw_map_outputs.append(text)
            result.prompt_tokens += int(usage.get("prompt_tokens") or 0)
            result.completion_tokens += int(usage.get("completion_tokens") or 0)
            data = parse_json_lenient(text)
            if isinstance(data, list):
                candidates.extend(x for x in data if isinstance(x, dict))
        return candidates

    # ---------- reduce ----------

    def _reduce_phase(
        self,
        candidates: list[dict[str, Any]],
        match_meta: dict[str, Any],
        roster: list[dict[str, Any]],
        result: InsightResult,
    ) -> None:
        user = REDUCE_USER_TEMPLATE.format(
            match_meta=json.dumps(match_meta, ensure_ascii=False),
            roster=json.dumps(roster, ensure_ascii=False),
            candidates=json.dumps(candidates, ensure_ascii=False),
        )
        text, usage = self.client.chat(system=REDUCE_SYSTEM, user=user, temperature=0.5)
        result.raw_reduce_output = text
        result.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        result.completion_tokens += int(usage.get("completion_tokens") or 0)
        data = parse_json_lenient(text)
        if not isinstance(data, dict):
            raise ValueError("reduce 输出不是 JSON 对象")

        def as_dict(v: Any) -> Optional[dict[str, Any]]:
            return v if isinstance(v, dict) else None

        result.overall = as_dict(data.get("overall"))
        result.bp = as_dict(data.get("bp"))
        result.flow = as_dict(data.get("flow"))
        result.blame = as_dict(data.get("blame"))
        result.golden_quotes = [x for x in (data.get("golden_quotes") or []) if isinstance(x, dict)]
        result.teams = [x for x in (data.get("teams") or []) if isinstance(x, dict)]
        result.players = [x for x in (data.get("players") or []) if isinstance(x, dict)]
        if result.overall is not None:
            result.overall.setdefault("risk", data.get("risk") or 0)

    # ---------- 校验与风控 ----------

    def _verify_quotes(self, result: InsightResult, segments: list[Segment]) -> None:
        """所有 quote 回转写子串定位：命中用该段 start_ms，未命中丢弃。"""

        def locate(text: str) -> Optional[int]:
            probe = str(text).strip().replace(" ", "")[:30]
            if not probe:
                return None
            for s in segments:
                if probe in s.text.replace(" ", ""):
                    return s.start_ms
            short = probe[:12]
            for s in segments:
                if short and short in s.text.replace(" ", ""):
                    return s.start_ms
            return None

        def verify_list(quotes: Any) -> list[dict[str, Any]]:
            verified = []
            for q in quotes or []:
                if not isinstance(q, dict) or not q.get("text"):
                    continue
                ms = locate(q["text"])
                if ms is not None:
                    q2 = dict(q)
                    q2["start_ms"] = ms
                    q2["speaker"] = "up"
                    verified.append(q2)
            return verified

        for group in (result.teams, result.players):
            for item in group:
                item["quotes"] = verify_list(item.get("quotes"))
        if result.bp:
            result.bp["predictions"] = verify_list(result.bp.get("predictions"))
        if result.flow:
            for tp in result.flow.get("turning_points") or []:
                if isinstance(tp, dict) and isinstance(tp.get("quote"), dict):
                    ok = verify_list([tp["quote"]])
                    tp["quote"] = ok[0] if ok else None
        result.golden_quotes = verify_list(result.golden_quotes)

    def _risk_filter(self, result: InsightResult) -> None:
        result.teams = [t for t in result.teams if float(t.get("risk") or 0) <= RISK_THRESHOLD]
        result.players = [p for p in result.players if float(p.get("risk") or 0) <= RISK_THRESHOLD]
        for attr in ("overall", "bp", "flow", "blame"):
            section = getattr(result, attr)
            if section and float(section.get("risk") or 0) > RISK_THRESHOLD:
                setattr(result, attr, None)
