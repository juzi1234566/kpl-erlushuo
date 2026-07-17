"""B站空间投稿 adapter：拉取指定 UP主 的投稿列表与视频信息。

- 走直连（trust_env=False），绝不使用代理（B站国内直连最快最稳）
- /x/space/wbi/arc/search 需要 wbi 签名；mixin key 当天缓存
- 可选 BILI_SESSDATA（浏览器 cookie）兜底风控
- 仿 pvp_match_adapter 模板：retry / raw 落盘 / 上下文管理 / 礼貌限速
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
import urllib.parse
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

API_BASE = "https://api.bilibili.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

# wbi 签名的固定打乱表（B站前端硬编码，社区维护）
_MIXIN_KEY_TABLE = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


class BiliApiError(RuntimeError):
    pass


class BilibiliAdapter:
    name = "bilibili_space"

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        raw_dir: Optional[Path] = None,
        sessdata: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.raw_dir = Path(raw_dir) if raw_dir else None
        if self.raw_dir:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
        cookies = {}
        sessdata = sessdata or os.getenv("BILI_SESSDATA") or ""
        if sessdata:
            cookies["SESSDATA"] = sessdata
        self._owns_client = client is None
        # trust_env=False：绝不吃系统/环境代理，B站必须直连
        self.client = client or httpx.Client(
            timeout=timeout,
            headers=DEFAULT_HEADERS,
            cookies=cookies,
            trust_env=False,
            follow_redirects=True,
        )
        self._mixin_key: Optional[str] = None
        self._mixin_key_date: Optional[str] = None
        self._warmed = False

    # ---------- 生命周期 ----------

    def __enter__(self) -> "BilibiliAdapter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    # ---------- 基础请求 ----------

    def _warm_cookies(self) -> None:
        """首访主站拿 buvid3 等 cookie，降低 -352 风控概率。"""
        if self._warmed:
            return
        try:
            self.client.get("https://www.bilibili.com/")
        except httpx.HTTPError:
            pass
        self._warmed = True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._warm_cookies()
        resp = self.client.get(f"{API_BASE}{path}", params=params)
        resp.raise_for_status()
        data = resp.json()
        code = data.get("code")
        if code != 0:
            raise BiliApiError(f"{path} code={code} message={data.get('message')}")
        return data.get("data") or {}

    @staticmethod
    def sleep_politely(base: float = 2.0, jitter: float = 3.0) -> None:
        time.sleep(base + random.random() * jitter)

    # ---------- wbi 签名 ----------

    def _get_mixin_key(self) -> str:
        today = time.strftime("%Y-%m-%d")
        if self._mixin_key and self._mixin_key_date == today:
            return self._mixin_key
        self._warm_cookies()
        resp = self.client.get(f"{API_BASE}/x/web-interface/nav")
        resp.raise_for_status()
        wbi_img = (resp.json().get("data") or {}).get("wbi_img") or {}
        img_key = (wbi_img.get("img_url") or "").rsplit("/", 1)[-1].split(".")[0]
        sub_key = (wbi_img.get("sub_url") or "").rsplit("/", 1)[-1].split(".")[0]
        if not img_key or not sub_key:
            raise BiliApiError("未取到 wbi img_key/sub_key")
        raw = img_key + sub_key
        self._mixin_key = "".join(raw[i] for i in _MIXIN_KEY_TABLE)[:32]
        self._mixin_key_date = today
        return self._mixin_key

    def _wbi_sign(self, params: dict[str, Any]) -> dict[str, Any]:
        mixin_key = self._get_mixin_key()
        signed = dict(params)
        signed["wts"] = int(time.time())
        # 参数值过滤特殊字符（B站规则）
        query_items = []
        for k in sorted(signed.keys()):
            v = "".join(c for c in str(signed[k]) if c not in "!'()*")
            query_items.append((k, v))
        query = urllib.parse.urlencode(query_items)
        signed["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
        return signed

    # ---------- raw 落盘 ----------

    def _maybe_dump(self, kind: str, key: str, obj: Any) -> Optional[Path]:
        if not self.raw_dir:
            return None
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(key))[:120]
        path = self.raw_dir / f"{kind}_{safe}.json"
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    @staticmethod
    def content_hash(obj: Any) -> str:
        blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    # ---------- 公开接口 ----------

    def list_up_videos(self, mid: int, *, page: int = 1, page_size: int = 30) -> list[dict[str, Any]]:
        """UP主 空间投稿列表（新→旧）。返回 [{bvid,title,created,length,pic,...}]"""
        params = self._wbi_sign(
            {
                "mid": mid,
                "pn": page,
                "ps": page_size,
                "order": "pubdate",
                "platform": "web",
                "web_location": "1550101",
            }
        )
        data = self._get("/x/space/wbi/arc/search", params)
        vlist = ((data.get("list") or {}).get("vlist")) or []
        self._maybe_dump("bili_space", f"{mid}_p{page}", vlist)
        return vlist

    def get_view(self, bvid: str) -> dict[str, Any]:
        """视频详情：aid/cid/duration/pages/pubdate/pic 等。"""
        data = self._get("/x/web-interface/view", {"bvid": bvid})
        self._maybe_dump("bili_view", bvid, data)
        return data
