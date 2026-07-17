"""Supabase REST 最小客户端（仅 service_role，供管线写入）。"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


class SupabaseRest:
    def __init__(
        self,
        url: Optional[str] = None,
        service_key: Optional[str] = None,
    ) -> None:
        self.url = (url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
        if not self.url or not self.key:
            raise RuntimeError(
                "缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY，请写入 pipeline/.env"
            )
        self.rest = f"{self.url}/rest/v1"
        # Supabase 出网需走本机代理（B站等国内源不走），见 OUTBOUND_PROXY
        self.proxy = os.getenv("OUTBOUND_PROXY") or None
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        }

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> Any:
        if not rows:
            return []
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
        # PostgREST upsert
        with httpx.Client(timeout=60.0, proxy=self.proxy) as client:
            resp = client.post(
                f"{self.rest}/{table}",
                headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
                params={"on_conflict": on_conflict},
                json=rows if len(rows) > 1 else rows[0] if False else rows,
            )
            # always send array
            if resp.status_code >= 400:
                # retry as array explicitly
                resp = client.post(
                    f"{self.rest}/{table}",
                    headers={**headers},
                    params={"on_conflict": on_conflict},
                    json=rows,
                )
            if resp.status_code >= 400:
                raise RuntimeError(f"upsert {table} failed: {resp.status_code} {resp.text[:500]}")
            return resp.text

    def select(self, table: str, query: str = "select=*") -> Any:
        with httpx.Client(timeout=30.0, proxy=self.proxy) as client:
            resp = client.get(
                f"{self.rest}/{table}?{query}",
                headers=self.headers,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"select {table} failed: {resp.status_code} {resp.text[:500]}")
            return resp.json()

    @staticmethod
    def configured() -> bool:
        return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
