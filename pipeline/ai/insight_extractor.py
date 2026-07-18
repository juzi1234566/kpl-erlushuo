"""二路解说观点提取：带说话人标签的转写稿 → 结构化评价 JSON。

流程：
1. 只保留 UP主 的发言段（官方解说的观点不属于该 UP）
2. 长转写 map-reduce：分块提取候选观点 → 归并去重成最终结论
3. 风控：risk>阈值 的条目丢弃（不引用辱骂原话，只允许转述批评）
4. quote 时间戳校正：AI 给的原话回转写稿子串定位，定位失败即丢弃
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

MAP_SYSTEM = """你是电竞解说内容分析助手。你收到王者荣耀职业比赛（KPL）二路解说的转写片段。
任务：只提取【评价性】言论——对某支战队/某位选手打得好坏、决策对错、状态起伏的评价。
忽略：单纯的实况复述（谁杀了谁、推了塔）、与比赛无关的闲聊、广告口播。
只输出合法 JSON，不要 Markdown。"""

MAP_USER_TEMPLATE = """【比赛信息】
{match_meta}

【选手名单】（含本场所用英雄。转写是语音识别产物，人名/英雄名常有同音错字——
如「小雨/小野」实为「小屿」、「中意」实为「钟意」——必须纠正对齐到名单；
解说也常用英雄名代指选手，请按名单里的英雄归属换算成选手名）
{roster}

【转写片段】（格式：[毫秒时间戳] 文本）
{chunk}

输出 JSON 数组，每项：
{{
  "subject_type": "team" | "player",
  "subject_name": "战队或选手名（对齐到比赛信息/名单）",
  "sentiment": "好评" | "差评" | "中立" | "复杂",
  "point": "一句话概括这个评价",
  "quote": {{"text": "解说原话（必须是转写原文的连续子串，20-60字）", "start_ms": 对应时间戳}}
}}
没有评价性内容就输出 []。"""

REDUCE_SYSTEM = """你是电竞内容编辑。把同一位解说对一场比赛的零散评价候选，归并成最终结论。
要求：
- 同一对象的多条候选合并；矛盾的评价用 sentiment="复杂" 并在 summary 里说明前后变化
- summary 是转述，语气克制：可以保留批评，但不得出现辱骂、人身攻击、家人相关内容
- 每个对象保留 1-3 条最有代表性的 quote（原样保留，不要改写 quote 文本）
- risk 自评：0-10，出现辱骂/造谣/隐私内容打高分
只输出合法 JSON，不要 Markdown。"""

REDUCE_USER_TEMPLATE = """【比赛信息】
{match_meta}

【候选观点】（来自同一位解说的完整视频，已分块提取）
{candidates}

输出 JSON：
{{
  "overall": {{"sentiment": "好评|差评|中立|复杂", "summary": "对整场比赛的总体观感，1-3句", "rating": 1-5}},
  "teams": [{{"name": "...", "sentiment": "...", "rating": 1-5, "summary": "1-3句转述", "risk": 0-10,
             "quotes": [{{"text": "...", "start_ms": 0}}]}}],
  "players": [同 teams 结构],
  "risk": 整体风险 0-10
}}"""


@dataclass
class InsightResult:
    overall: Optional[dict[str, Any]] = None
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
        self.client = client or DeepSeekClient(timeout=180.0)

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
        try:
            candidates = self._map_phase(up_segments, match_meta, roster or [], result)
            if not candidates:
                result.error = "未提取到评价性内容"
                return result
            self._reduce_phase(candidates, match_meta, result)
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
                # 重叠：保留尾部若干行进入下一块
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
        roster: list[str],
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
        result: InsightResult,
    ) -> None:
        user = REDUCE_USER_TEMPLATE.format(
            match_meta=json.dumps(match_meta, ensure_ascii=False),
            candidates=json.dumps(candidates, ensure_ascii=False),
        )
        text, usage = self.client.chat(system=REDUCE_SYSTEM, user=user, temperature=0.3)
        result.raw_reduce_output = text
        result.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        result.completion_tokens += int(usage.get("completion_tokens") or 0)
        data = parse_json_lenient(text)
        if not isinstance(data, dict):
            raise ValueError("reduce 输出不是 JSON 对象")
        result.overall = data.get("overall") if isinstance(data.get("overall"), dict) else None
        result.teams = [x for x in (data.get("teams") or []) if isinstance(x, dict)]
        result.players = [x for x in (data.get("players") or []) if isinstance(x, dict)]
        if result.overall is not None:
            result.overall.setdefault("risk", data.get("risk") or 0)

    # ---------- 校验与风控 ----------

    def _verify_quotes(self, result: InsightResult, segments: list[Segment]) -> None:
        """quote 回转写子串定位：命中则用该段 start_ms，未命中丢弃。"""

        def locate(text: str) -> Optional[int]:
            probe = text.strip().replace(" ", "")[:30]
            if not probe:
                return None
            for s in segments:
                if probe in s.text.replace(" ", ""):
                    return s.start_ms
            # 放宽：取前 12 字再试
            short = probe[:12]
            for s in segments:
                if short and short in s.text.replace(" ", ""):
                    return s.start_ms
            return None

        for group in (result.teams, result.players):
            for item in group:
                verified = []
                for q in item.get("quotes") or []:
                    if not isinstance(q, dict) or not q.get("text"):
                        continue
                    ms = locate(str(q["text"]))
                    if ms is not None:
                        verified.append({"text": q["text"], "start_ms": ms, "speaker": "up"})
                item["quotes"] = verified

    def _risk_filter(self, result: InsightResult) -> None:
        result.teams = [t for t in result.teams if float(t.get("risk") or 0) <= RISK_THRESHOLD]
        result.players = [p for p in result.players if float(p.get("risk") or 0) <= RISK_THRESHOLD]
        if result.overall and float(result.overall.get("risk") or 0) > RISK_THRESHOLD:
            result.overall = None
