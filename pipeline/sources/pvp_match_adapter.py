"""王者荣耀官方联赛站开放接口适配器。

基座: https://prod.comp.smoba.qq.com/leaguesite/
请求需带 Referer: https://pvp.qq.com/
实测无需签名 / cookie。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://prod.comp.smoba.qq.com/leaguesite"
DEFAULT_HEADERS = {
    "Referer": "https://pvp.qq.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

# 2026 夏季赛（调研时 status=1 进行中）
LEAGUE_SUMMER_2026 = "20260003"


class PvpApiError(RuntimeError):
    pass


class PvpMatchAdapter:
    """官方赛事数据源。后续可在此切换玩加 / scoregg 备源。"""

    name = "pvp_official"

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        raw_dir: Optional[Path] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.timeout = timeout
        self.raw_dir = Path(raw_dir) if raw_dir else None
        self._owns_client = client is None
        self.client = client or httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "PvpMatchAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=15))
    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        code = data.get("code")
        if code not in (0, 200, "0", "200", None):
            raise PvpApiError(f"API code={code} path={path} msg={data.get('message')}")
        return data

    def _payload(self, data: dict[str, Any]) -> Any:
        if "results" in data and data["results"] is not None:
            return data["results"]
        if "data" in data and data["data"] is not None:
            return data["data"]
        return data

    def _maybe_dump(self, kind: str, key: str, obj: Any) -> Optional[Path]:
        if not self.raw_dir:
            return None
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:120]
        path = self.raw_dir / f"{kind}_{safe}.json"
        text = json.dumps(obj, ensure_ascii=False, indent=2)
        path.write_text(text, encoding="utf-8")
        return path

    @staticmethod
    def content_hash(obj: Any) -> str:
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ---------- 公开接口 ----------

    def list_leagues(self) -> list[dict[str, Any]]:
        data = self._get("/leagues/open")
        payload = self._payload(data)
        assert isinstance(payload, list)
        self._maybe_dump("leagues", "all", payload)
        return payload

    def current_league(self, prefer_id: str = LEAGUE_SUMMER_2026) -> Optional[dict[str, Any]]:
        leagues = self.list_leagues()
        for item in leagues:
            if str(item.get("league_id")) == str(prefer_id):
                return item
        # status=1 进行中
        for item in leagues:
            if item.get("status") == 1:
                return item
        return leagues[-1] if leagues else None

    def list_matches(self, league_id: str) -> list[dict[str, Any]]:
        data = self._get("/matches/open", params={"league_id": league_id})
        payload = self._payload(data)
        assert isinstance(payload, list)
        self._maybe_dump("matches", str(league_id), payload)
        return payload

    def list_battles(self, match_id: str) -> list[dict[str, Any]]:
        """对局列表。部分赛季也可从 match.match_battle_video_list 取 battle_id。"""
        data = self._get("/match/battles/open", params={"match_id": match_id})
        payload = self._payload(data)
        if isinstance(payload, dict):
            battles = payload.get("battle_list") or payload.get("battles") or []
        else:
            battles = payload if isinstance(payload, list) else []
        self._maybe_dump("battles", str(match_id), payload)
        return battles

    def get_battle(self, battle_id: str) -> dict[str, Any]:
        data = self._get("/battle/open", params={"battle_id": battle_id})
        payload = self._payload(data)
        assert isinstance(payload, dict)
        self._maybe_dump("battle", str(battle_id), payload)
        return payload

    def settle_list(self, league_id: str, kind: str) -> list[dict[str, Any]]:
        """kind: hero | player | team"""
        if kind not in {"hero", "player", "team"}:
            raise ValueError("kind must be hero|player|team")
        data = self._get(f"/league/{kind}/settle_list/open", params={"league_id": league_id})
        payload = self._payload(data)
        if isinstance(payload, dict):
            items = payload.get("list") or payload.get("results") or []
        else:
            items = payload
        self._maybe_dump(f"settle_{kind}", str(league_id), payload)
        return list(items or [])

    def battle_ids_from_match(self, match: dict[str, Any]) -> list[str]:
        ids: list[str] = []
        for item in match.get("match_battle_video_list") or []:
            bid = item.get("battle_id")
            if bid:
                ids.append(str(bid))
        return ids

    def sleep_politely(self, seconds: float = 0.35) -> None:
        time.sleep(seconds)
