"""generation_jobs 队列消费者骨架。

Phase 0：本地轮询 JSON 文件队列（不依赖 Redis）。
接入 Supabase 后改为读 generation_jobs 表（service_role）。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ai.meme_generator import MemeGenerator
from signals.meme_signals import extract_battle_signals, extract_match_signals, rank_signals
from sources.pvp_match_adapter import PvpMatchAdapter


class LocalJobQueue:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, jobs: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

    def enqueue(self, job: dict[str, Any]) -> None:
        jobs = self.load()
        jobs.append(job)
        self.save(jobs)

    def claim_pending(self) -> list[dict[str, Any]]:
        jobs = self.load()
        pending = [j for j in jobs if j.get("status") == "pending"]
        return pending

    def update(self, job_id: str, **fields: Any) -> None:
        jobs = self.load()
        for j in jobs:
            if j.get("id") == job_id:
                j.update(fields)
        self.save(jobs)


def process_meme_card_job(job: dict[str, Any], raw_dir: Path) -> dict[str, Any]:
    match = job.get("match") or {}
    battle_id = job.get("battle_id")
    with PvpMatchAdapter(raw_dir=raw_dir) as api:
        battle = api.get_battle(str(battle_id)) if battle_id else {}
    signals = rank_signals(extract_match_signals(match) + extract_battle_signals(battle))
    camp1 = match.get("camp1") or {}
    camp2 = match.get("camp2") or {}
    meta = {
        "match_id": match.get("match_id"),
        "team_a": camp1.get("team_abbreviation") or camp1.get("team_name"),
        "team_b": camp2.get("team_abbreviation") or camp2.get("team_name"),
        "score": f"{camp1.get('score')}:{camp2.get('score')}",
        "stage": match.get("match_stage_desc"),
    }
    gen = MemeGenerator()
    result = gen.generate(match_meta=meta, signals=signals)
    return {
        "signals": signals,
        "published": result.published,
        "review_pool": result.review_pool,
        "model": result.model,
        "error": result.error,
    }


def run_once(queue_path: Path, raw_dir: Path) -> int:
    q = LocalJobQueue(queue_path)
    pending = q.claim_pending()
    done = 0
    for job in pending:
        q.update(job["id"], status="running", attempts=int(job.get("attempts") or 0) + 1)
        try:
            out = process_meme_card_job(job, raw_dir)
            status = "failed" if out.get("error") else "done"
            q.update(job["id"], status=status, result=out)
            done += 1
        except Exception as exc:  # noqa: BLE001
            q.update(job["id"], status="failed", error=str(exc))
    return done


def main() -> None:
    root = Path(__file__).resolve().parent
    queue = root / "data" / "jobs.json"
    raw = root / "data" / "raw"
    print(f"worker watching {queue}")
    while True:
        n = run_once(queue, raw)
        if n:
            print(f"processed {n} jobs")
        time.sleep(5)


if __name__ == "__main__":
    main()
