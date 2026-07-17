"""DeepSeek 最小客户端：chat 调用 + 宽容 JSON 解析。

供 meme_generator 与 insight_extractor 共用。
出网走 OUTBOUND_PROXY（本机代理），未设置则直连。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


class DeepSeekClient:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
        self.timeout = timeout
        self.proxy = os.getenv("OUTBOUND_PROXY") or None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.7,
    ) -> tuple[str, dict[str, Any]]:
        """返回 (文本, usage)。失败抛异常，由调用方决定重试。"""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        with httpx.Client(timeout=self.timeout, proxy=self.proxy) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return text, usage


def parse_json_lenient(text: str) -> Any:
    """宽容解析模型输出：剥 ```json 包裹，失败回退提取首个 JSON 数组/对象。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for pattern in (r"\[.*\]", r"\{.*\}"):
            m = re.search(pattern, text, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    continue
    return None
