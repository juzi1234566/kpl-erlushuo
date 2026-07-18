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

# 电竞常用词（ASR 高频错认对象），校对与热词共用
ESPORTS_TERMS = [
    "零封", "被零封", "让一追二", "让二追三", "团灭", "抢龙", "偷家", "大龙", "暴君",
    "主宰", "先知主宰", "兵线", "高地", "水晶", "闪现", "名刀", "金身", "复活甲",
    "破军", "逐日", "红buff", "蓝buff", "一血", "五杀", "经济差", "打野", "中路",
    "对抗路", "发育路", "游走", "开团", "拉扯", "换血", "越塔",
]

POLISH_SYSTEM = """你是电竞视频转写校对员。给你的引用来自语音识别，含同音/近音错字。
只做【最小还原修正】：
- 只修明显的同音错字与识别错误（例：KS级→KSG、被零住→被零封、大师命→大司命）
- 人名/队名/英雄名对齐给定词表
- 不改语序、不增删内容、不润色；拿不准的保持原样
输出 JSON：{"quotes": ["修正后文本", ...]}，数组长度与输入一致、顺序一致。"""

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

REDUCE_SYSTEM = """你是资深电竞编辑，把二路解说的观点整理成「一眼能看完」的赛评卡片。读者刷手机，
没人看大段文字——所有内容都要拆成短要点，重点前置。
写作铁律：
1. 【禁止叙述框架】不要写「解说认为」「可温说」「他表示」这类第三人称转述——
   直接把观点当结论说出来（例：写「大司命后期无敌，AG 就等这一手」，
   不写「可温认为大司命后期无敌」）。原话放 quote 字段让它自己说话。
2. 【短】每条要点一句话、≤40字、信息前置；headline/verdict 是钩子，≤25字。
3. 【说人话】用解说的原词，别自己堆黑话；转述只做串联，不添油加醋。
4. 【爆点优先】预测按最终比分判定「应验/打脸」——判定备注必须与真实比分一致，不许编。
5. 【安全】转述不得辱骂/人身攻击；每板块 risk 自评 0-10，辱骂/造谣/隐私打高分。
6. quote 原样保留原话，不要改写。
只输出合法 JSON，不要 Markdown。"""

REDUCE_USER_TEMPLATE = """【比赛信息】（含最终比分，预测应验/打脸判定必须以此为准）
{match_meta}

【选手名单】
{roster}

【候选素材】（同一位解说的完整视频分块提取）
{candidates}

输出 JSON（没聊到的板块给 null，不要编造）：
{{
  "bp": {{
    "headline": "BP结论一句话钩子，≤25字",
    "rating": 教练BP打分1-5,
    "points": ["要点，≤40字，直接下结论", "3-6条"],
    "predictions": [{{"text": "预测原话", "start_ms": 0, "verdict": "应验" | "打脸" | "未验证",
                     "note": "≤20字，须与真实比分一致"}}],
    "risk": 0-10
  }},
  "flow": {{
    "early": "前期一句话，≤50字",
    "mid": "中期一句话，≤50字",
    "late": "后期与结局一句话，≤50字",
    "turning_points": [{{"desc": "转折点，≤30字", "quote": {{"text": "...", "start_ms": 0}}}}],
    "risk": 0-10
  }},
  "overall": {{"sentiment": "好评|差评|中立|复杂", "rating": 1-5,
              "headline": "整场一句话总结，≤25字",
              "points": ["看点/结论，≤40字", "2-4条"], "risk": 0-10}},
  "teams": [{{"name": "...", "sentiment": "...", "rating": 1-5,
             "verdict": "一句话结论，≤30字",
             "points": ["要点，≤40字", "2-4条"],
             "quotes": [{{"text": "...", "start_ms": 0}}], "risk": 0-10}}],
  "players": [{{"name": "...", "sentiment": "...", "rating": 1-5,
               "verdict": "一句话结论，≤30字",
               "points": ["前期/后期/关键时刻各自表现，≤40字", "2-4条"],
               "highlight": "高光，≤25字，没有留空", "lowlight": "低谷，≤25字，没有留空",
               "quotes": [最多2条], "risk": 0-10}}],
  "blame": {{"headline": "锅在谁，一句话，≤25字",
            "main": [{{"name": "背锅对象", "reason": "锅因，≤30字"}}], "risk": 0-10}},
  "golden_quotes": [{{"text": "金句原话", "start_ms": 0, "context": "场景，≤15字"}}],
  "risk": 整体0-10
}}"""


SERIES_SYSTEM = """你是资深电竞编辑。同一位解说对一场 BO5 每局的分析已经整理好，
现在汇总成【整场系列赛】总评。写作铁律与单局一致：
- 禁止「解说认为/他说」叙述框架，观点直接陈述
- 全部拆短要点：headline/verdict ≤25-30字，points 每条 ≤40字
- 选手总评要体现【跨局变化】（如：前两局拉胯，决胜局爆发）
- 整场评分综合各局，不是简单平均——决胜局表现权重更高
- risk 自评 0-10
只输出合法 JSON，不要 Markdown。"""

SERIES_USER_TEMPLATE = """【比赛信息】（最终比分为准）
{match_meta}

【选手名单】
{roster}

【各局分析】（该解说逐局的结构化观点，按局序排列）
{games}

输出 JSON：
{{
  "overall": {{"sentiment": "好评|差评|中立|复杂", "rating": 1-5,
              "headline": "整场一句话总结，≤25字",
              "points": ["整场看点/结论，≤40字", "2-5条"], "risk": 0-10}},
  "games_brief": [{{"game_no": 1, "one_line": "该局一句话，≤30字，含胜负走向"}}],
  "teams": [{{"name": "...", "sentiment": "...", "rating": 1-5,
             "verdict": "整场一句话，≤30字", "points": ["≤40字", "2-3条"], "risk": 0-10}}],
  "players": [{{"name": "...", "sentiment": "...", "rating": 1-5,
               "verdict": "整场一句话，≤30字",
               "points": ["跨局表现变化，≤40字", "2-4条"], "risk": 0-10}}],
  "blame": {{"headline": "整场的锅在谁，≤25字",
            "main": [{{"name": "...", "reason": "≤30字"}}], "risk": 0-10}},
  "risk": 0-10
}}"""


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
            self._polish_quotes(result, match_meta, roster)
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

    def _collect_quote_refs(self, result: InsightResult) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for group in (result.teams, result.players):
            for item in group:
                refs.extend(q for q in (item.get("quotes") or []) if isinstance(q, dict))
        if result.bp:
            refs.extend(q for q in (result.bp.get("predictions") or []) if isinstance(q, dict))
        if result.flow:
            for tp in result.flow.get("turning_points") or []:
                if isinstance(tp, dict) and isinstance(tp.get("quote"), dict):
                    refs.append(tp["quote"])
        refs.extend(q for q in result.golden_quotes if isinstance(q, dict))
        return [q for q in refs if q.get("text")]

    def _polish_quotes(
        self,
        result: InsightResult,
        match_meta: dict[str, Any],
        roster: list[dict[str, Any]],
    ) -> None:
        """引用最小还原校对：修同音错字，人名/术语对齐词表。失败则静默保留原文。"""
        refs = self._collect_quote_refs(result)
        if not refs:
            return
        glossary = sorted(
            {
                *(p.get("player") or "" for p in roster),
                *(p.get("team") or "" for p in roster),
                *(h for p in roster for h in (p.get("heroes") or [])),
                *ESPORTS_TERMS,
                str(match_meta.get("team_a") or ""),
                str(match_meta.get("team_b") or ""),
            }
            - {""}
        )
        payload = {"词表": glossary, "quotes": [q["text"] for q in refs]}
        try:
            text, usage = self.client.chat(
                system=POLISH_SYSTEM,
                user=json.dumps(payload, ensure_ascii=False),
                temperature=0.1,
            )
            result.prompt_tokens += int(usage.get("prompt_tokens") or 0)
            result.completion_tokens += int(usage.get("completion_tokens") or 0)
            data = parse_json_lenient(text)
            fixed = (data or {}).get("quotes") if isinstance(data, dict) else None
            if isinstance(fixed, list) and len(fixed) == len(refs):
                for q, new_text in zip(refs, fixed):
                    if isinstance(new_text, str) and new_text.strip():
                        # 长度暴涨说明被改写而非校对，弃用
                        if len(new_text) <= len(q["text"]) * 1.5:
                            q["raw_text"] = q["text"]
                            q["text"] = new_text.strip()
        except Exception:  # noqa: BLE001
            pass

    def _risk_filter(self, result: InsightResult) -> None:
        result.teams = [t for t in result.teams if float(t.get("risk") or 0) <= RISK_THRESHOLD]
        result.players = [p for p in result.players if float(p.get("risk") or 0) <= RISK_THRESHOLD]
        for attr in ("overall", "bp", "flow", "blame"):
            section = getattr(result, attr)
            if section and float(section.get("risk") or 0) > RISK_THRESHOLD:
                setattr(result, attr, None)

    # ---------- 系列赛汇总 ----------

    def aggregate_series(
        self,
        *,
        game_payloads: list[dict[str, Any]],
        match_meta: dict[str, Any],
        roster: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[Optional[dict[str, Any]], dict[str, int]]:
        """各局分析 → 整场系列赛总评。返回 (series dict 或 None, usage)。"""
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0}
        if not game_payloads:
            return None, usage_total
        user = SERIES_USER_TEMPLATE.format(
            match_meta=json.dumps(match_meta, ensure_ascii=False),
            roster=json.dumps(roster or [], ensure_ascii=False),
            games=json.dumps(game_payloads, ensure_ascii=False),
        )
        text, usage = self.client.chat(system=SERIES_SYSTEM, user=user, temperature=0.5)
        usage_total["prompt_tokens"] = int(usage.get("prompt_tokens") or 0)
        usage_total["completion_tokens"] = int(usage.get("completion_tokens") or 0)
        data = parse_json_lenient(text)
        if not isinstance(data, dict):
            return None, usage_total
        # 系列赛层风控
        for key in ("overall", "blame"):
            sec = data.get(key)
            if isinstance(sec, dict) and float(sec.get("risk") or 0) > RISK_THRESHOLD:
                data[key] = None
        data["teams"] = [t for t in (data.get("teams") or []) if isinstance(t, dict) and float(t.get("risk") or 0) <= RISK_THRESHOLD]
        data["players"] = [p for p in (data.get("players") or []) if isinstance(p, dict) and float(p.get("risk") or 0) <= RISK_THRESHOLD]
        return data, usage_total
