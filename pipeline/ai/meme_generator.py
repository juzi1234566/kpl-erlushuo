"""生梗管线：规则信号 + few-shot → 多候选 → 自评 → 产出。

未配置 DEEPSEEK_API_KEY 时走本地 mock，方便 Phase 0 验收结构。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from dotenv import load_dotenv

from ai.deepseek_client import DeepSeekClient, parse_json_lenient

load_dotenv()

BOT_PERSONA = """你是「梗局」站内官方 AI 角色「AI串子bot」。
风格：懂 KPL 黑话、贱一点但不过线、短句有画面感。
硬性禁区：人身攻击、家人、赌博、地域黑、造谣转会、色情政治。
你必须把自己当 AI，禁止伪装成真实网友。"""

OUTPUT_SCHEMA = """严格输出 JSON 数组，长度=6，每项：
{
  "kind": "meme_card" | "ai_recap" | "one_liner",
  "title": "≤20字标题",
  "body": "1-4句正文",
  "tags": ["标签1","标签2"],
  "risk": 0-10,
  "humor": 0-10,
  "relevance": 0-10
}
不要 Markdown，不要代码块。"""

FEW_SHOTS = [
    {
        "signals": [{"type": "sweep", "summary": "WB 3:0 横扫 eStar"}],
        "sample": {
            "kind": "one_liner",
            "title": "三比零说明书",
            "body": "eStar 今天不是来打比赛的，是来给 WB 送赛后采访素材的。",
            "tags": ["横扫", "WB"],
            "risk": 2,
            "humor": 7,
            "relevance": 9,
        },
    },
    {
        "signals": [{"type": "extreme_kda", "summary": "某某 0/8/2 超鬼"}],
        "sample": {
            "kind": "meme_card",
            "title": "经济在线，人也在泉水",
            "body": "KDA 0/8/2：不是不会玩，是在用生命做数据可视化。",
            "tags": ["超鬼", "KDA"],
            "risk": 3,
            "humor": 8,
            "relevance": 9,
        },
    },
]


@dataclass
class GenerationResult:
    candidates: list[dict[str, Any]] = field(default_factory=list)
    published: list[dict[str, Any]] = field(default_factory=list)
    review_pool: list[dict[str, Any]] = field(default_factory=list)
    model: str = "mock"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_text: str = ""
    error: Optional[str] = None


class MemeGenerator:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        risk_threshold: float = 6.5,
        auto_publish_top: int = 2,
    ) -> None:
        self.client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model, timeout=90.0)
        self.api_key = self.client.api_key
        self.base_url = self.client.base_url
        self.model = self.client.model
        self.risk_threshold = risk_threshold
        self.auto_publish_top = auto_publish_top

    def build_prompt(
        self,
        *,
        match_meta: dict[str, Any],
        signals: list[dict[str, Any]],
        related_memes: Optional[list[str]] = None,
    ) -> str:
        related = related_memes or []
        parts = [
            BOT_PERSONA,
            "【比赛信息】",
            json.dumps(match_meta, ensure_ascii=False),
            "【梗点信号（规则引擎产出，优先写这些）】",
            json.dumps(signals, ensure_ascii=False),
            "【站内关联梗词条】",
            json.dumps(related, ensure_ascii=False),
            "【few-shot】",
            json.dumps(FEW_SHOTS, ensure_ascii=False),
            OUTPUT_SCHEMA,
        ]
        return "\n\n".join(parts)

    def generate(
        self,
        *,
        match_meta: dict[str, Any],
        signals: list[dict[str, Any]],
        related_memes: Optional[list[str]] = None,
    ) -> GenerationResult:
        prompt = self.build_prompt(
            match_meta=match_meta,
            signals=signals,
            related_memes=related_memes,
        )
        if not self.api_key:
            return self._mock(match_meta, signals)

        try:
            raw, usage = self._chat(prompt)
            candidates = self._parse_candidates(raw)
            candidates = self._self_score_filter(candidates)
            published, pool = self._split(candidates)
            return GenerationResult(
                candidates=candidates,
                published=published,
                review_pool=pool,
                model=self.model,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                raw_text=raw,
            )
        except Exception as exc:  # noqa: BLE001
            return GenerationResult(error=str(exc), model=self.model)

    def _chat(self, prompt: str) -> tuple[str, dict[str, Any]]:
        return self.client.chat(
            system="你是 KPL 玩梗文案助手，只输出合法 JSON。",
            user=prompt,
            temperature=0.9,
        )

    def _parse_candidates(self, text: str) -> list[dict[str, Any]]:
        data = parse_json_lenient(text)
        if data is None:
            return []
        if isinstance(data, dict):
            data = data.get("items") or data.get("candidates") or [data]
        return [x for x in data if isinstance(x, dict)]

    def _self_score_filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        for item in items:
            risk = float(item.get("risk") or 0)
            if risk > self.risk_threshold:
                item["dropped"] = True
                item["drop_reason"] = "risk_threshold"
                continue
            humor = float(item.get("humor") or 0)
            rel = float(item.get("relevance") or 0)
            item["score"] = humor * 0.55 + rel * 0.45 - risk * 0.2
            item["dropped"] = False
            kept.append(item)
        kept.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
        return kept

    def _split(self, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        top = items[: self.auto_publish_top]
        rest = items[self.auto_publish_top :]
        return top, rest

    def _mock(self, match_meta: dict[str, Any], signals: list[dict[str, Any]]) -> GenerationResult:
        t1 = match_meta.get("team_a") or "A队"
        t2 = match_meta.get("team_b") or "B队"
        sig = signals[0]["summary"] if signals else f"{t1} vs {t2}"
        candidates = [
            {
                "kind": "ai_recap",
                "title": f"{t1} vs {t2} 赛后速递",
                "body": f"【AI生成】本场关键词：{sig}。数据说话，串点免费。",
                "tags": ["战报", "AI"],
                "risk": 1,
                "humor": 5,
                "relevance": 8,
                "score": 6.5,
                "dropped": False,
            },
            {
                "kind": "meme_card",
                "title": "今日串点",
                "body": f"【AI生成】{sig}——评论区已经准备好键盘了。",
                "tags": ["梗卡", "AI"],
                "risk": 2,
                "humor": 7,
                "relevance": 8,
                "score": 7.1,
                "dropped": False,
            },
            {
                "kind": "one_liner",
                "title": "一句话",
                "body": f"【AI生成】看完 {t1} 和 {t2}，只想说：赛程组有点东西。",
                "tags": ["一句话"],
                "risk": 1,
                "humor": 6,
                "relevance": 7,
                "score": 6.2,
                "dropped": False,
            },
        ]
        candidates = self._self_score_filter(candidates)
        pub, pool = self._split(candidates)
        return GenerationResult(
            candidates=candidates,
            published=pub,
            review_pool=pool,
            model="mock-local",
            raw_text=json.dumps(candidates, ensure_ascii=False),
        )
