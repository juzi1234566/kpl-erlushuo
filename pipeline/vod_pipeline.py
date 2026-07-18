"""二路视频处理链：下载 → 转写+说话人归属 → AI 观点提取 → 入库。

三个环节各自幂等，供 worker 派发或 scripts/process_vod.py 串行调用。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from ai.insight_extractor import InsightExtractor, InsightResult  # noqa: E402
from asr.funasr_transcriber import Segment, load_transcript, save_transcript, transcribe  # noqa: E402
from asr.speaker_attribution import attribute_speakers  # noqa: E402
from db.supabase_client import SupabaseRest  # noqa: E402
from media.audio_downloader import SkipVideo, download_audio  # noqa: E402
from signals.vod_matcher import TEAM_ALIASES  # noqa: E402

AUDIO_DIR = ROOT / "data" / "audio"
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"


# ---------- 公共 ----------

def _get_vod(db: SupabaseRest, bvid: str) -> dict[str, Any]:
    rows = db.select("vod_sources", f"select=*&bvid=eq.{bvid}")
    if not rows:
        raise RuntimeError(f"vod_sources 中不存在 {bvid}")
    return rows[0]


def _set_vod(db: SupabaseRest, bvid: str, **fields: Any) -> None:
    db.upsert("vod_sources", [{"bvid": bvid, **fields}], on_conflict="bvid")


def _match_meta(db: SupabaseRest, match_id: str) -> dict[str, Any]:
    rows = db.select(
        "matches",
        f"select=id,team1_id,team2_id,score1,score2,start_time,stage_desc&id=eq.{match_id}",
    )
    if not rows:
        return {"match_id": match_id}
    m = rows[0]
    team_ids = [str(m.get("team1_id")), str(m.get("team2_id"))]
    names = {}
    for tid in team_ids:
        aliases = TEAM_ALIASES.get(tid)
        names[tid] = aliases[0] if aliases else tid
    return {
        "match_id": match_id,
        "team_a": names[team_ids[0]],
        "team_b": names[team_ids[1]],
        "score": f"{m.get('score1')}:{m.get('score2')}",
        "stage": m.get("stage_desc"),
        "start_time": m.get("start_time"),
    }


def match_roster_and_hotwords(match_id: str) -> tuple[list[dict[str, Any]], str]:
    """从官方对局数据取本场选手名单与热词表。

    返回 (roster, hotword)：
    - roster: [{"team": 队名, "player": 选手名, "heroes": [本场用过的英雄]}]
    - hotword: 空格分隔的热词串（选手/战队/英雄），喂给 SeaCo-Paraformer
    """
    from sources.pvp_match_adapter import PvpMatchAdapter

    players: dict[str, dict[str, Any]] = {}
    teams: set[str] = set()
    heroes: set[str] = set()
    with PvpMatchAdapter(raw_dir=ROOT / "data" / "raw") as api:
        battles = api.list_battles(str(match_id))
        for bt in battles:
            bid = bt.get("battle_id")
            if not bid:
                continue
            b = api.get_battle(str(bid))
            for p in b.get("battle_player_list") or []:
                name = (p.get("player_name") or "").strip()
                if not name:
                    continue
                team = (p.get("team_name") or "").strip()
                hero = (p.get("hero_name") or "").strip()
                teams.add(team)
                if hero:
                    heroes.add(hero)
                entry = players.setdefault(name, {"team": team, "player": name, "heroes": set()})
                if hero:
                    entry["heroes"].add(hero)
            api.sleep_politely()

    from ai.insight_extractor import ESPORTS_TERMS

    roster = [
        {"team": v["team"], "player": v["player"], "heroes": sorted(v["heroes"])}
        for v in players.values()
    ]
    hot_terms = sorted({*players.keys(), *teams, *heroes, *ESPORTS_TERMS})
    return roster, " ".join(t for t in hot_terms if t)


# ---------- 环节一：下载 ----------

def process_vod_download(bvid: str, db: Optional[SupabaseRest] = None) -> Path:
    db = db or SupabaseRest()
    try:
        wav = download_audio(bvid, AUDIO_DIR)
    except SkipVideo as exc:
        _set_vod(db, bvid, audio_status="skipped", last_error=str(exc))
        raise
    except Exception as exc:  # noqa: BLE001
        _set_vod(db, bvid, audio_status="failed", last_error=str(exc))
        raise
    _set_vod(db, bvid, audio_status="done", audio_ref=str(wav.relative_to(ROOT)), last_error=None)
    return wav


# ---------- 环节二：转写 + 归属 ----------

def process_vod_transcribe(bvid: str, db: Optional[SupabaseRest] = None) -> tuple[list[Segment], dict[str, str]]:
    db = db or SupabaseRest()
    wav = AUDIO_DIR / f"{bvid}.wav"
    if not wav.exists():
        raise RuntimeError(f"{bvid} 音频不存在，先跑下载环节")
    out = TRANSCRIPT_DIR / f"{bvid}.json"

    try:
        if out.exists():
            data = json.loads(out.read_text(encoding="utf-8"))
            segments = [Segment(**s) for s in data["segments"]]
            speaker_map = (data.get("meta") or {}).get("speaker_map")
            if speaker_map:
                return segments, speaker_map
        else:
            segments = transcribe(wav)

        # 说话人归属（人工覆盖：up_profiles.speaker_hint）
        vod = _get_vod(db, bvid)
        hint = None
        if vod.get("mid"):
            ups = db.select("up_profiles", f"select=speaker_hint&mid=eq.{vod['mid']}")
            hint = (ups[0].get("speaker_hint") if ups else None) or None
        attribution = attribute_speakers(segments, wav, hint)
        meta = {
            "speaker_map": attribution.mapping,
            "attribution_confidence": attribution.confidence,
            "attribution_detail": attribution.detail,
            "generated_at": datetime.now().isoformat(),
        }
        save_transcript(out, segments, meta)

        fields: dict[str, Any] = {
            "transcript_status": "done",
            "transcript_ref": str(out.relative_to(ROOT)),
            "last_error": None,
        }
        if attribution.needs_review:
            fields["needs_review"] = True
            fields["last_error"] = f"说话人归属置信度低（{attribution.confidence:.2f}），请人工确认"
        _set_vod(db, bvid, **fields)
        return segments, attribution.mapping
    except Exception as exc:  # noqa: BLE001
        _set_vod(db, bvid, transcript_status="failed", last_error=str(exc))
        raise


# ---------- 环节三：分析 + 入库 ----------

def process_vod_analyze(bvid: str, db: Optional[SupabaseRest] = None) -> InsightResult:
    db = db or SupabaseRest()
    vod = _get_vod(db, bvid)
    match_id = vod.get("match_id")
    if not match_id:
        raise RuntimeError(f"{bvid} 未绑定比赛，先指派 match_id")

    out = TRANSCRIPT_DIR / f"{bvid}.json"
    if not out.exists():
        raise RuntimeError(f"{bvid} 转写不存在，先跑转写环节")
    data = json.loads(out.read_text(encoding="utf-8"))
    segments = [Segment(**s) for s in data["segments"]]
    speaker_map = (data.get("meta") or {}).get("speaker_map") or {}

    meta = _match_meta(db, str(match_id))
    extractor = InsightExtractor()
    try:
        result = extractor.extract(segments=segments, speaker_map=speaker_map, match_meta=meta)
        if result.error:
            raise RuntimeError(result.error)
        rows = build_insight_rows(result, vod_id=vod["id"], match_id=str(match_id), model=result.model)
        if rows:
            db.upsert("commentary_insights", rows, on_conflict="vod_id,subject_type,subject_name")
        # 审计
        db.upsert(
            "ai_generations",
            [
                {
                    "model": result.model,
                    "prompt": f"insight_extract {bvid} ({len(segments)} segs)",
                    "response": result.raw_reduce_output[:8000],
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "publish_target": "commentary_insights",
                }
            ],
            on_conflict="id",
        )
        _set_vod(db, bvid, analysis_status="done", last_error=None)
        return result
    except Exception as exc:  # noqa: BLE001
        _set_vod(db, bvid, analysis_status="failed", last_error=str(exc))
        raise


def build_insight_rows(
    result: InsightResult,
    *,
    vod_id: str,
    match_id: str,
    model: str,
) -> list[dict[str, Any]]:
    """InsightResult → commentary_insights 行。subject_id 对齐战队别名表。"""
    alias_to_tid = {a.upper(): tid for tid, aliases in TEAM_ALIASES.items() for a in aliases}
    rows: list[dict[str, Any]] = []

    def clamp_rating(v: Any) -> Optional[int]:
        try:
            return max(1, min(5, int(v)))
        except (TypeError, ValueError):
            return None

    def add(
        subject_type: str,
        name: str,
        item: dict[str, Any],
        subject_id: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        sentiment = item.get("sentiment")
        if sentiment not in ("好评", "差评", "中立", "复杂"):
            sentiment = "中立"
        summary = (item.get("summary") or "").strip()
        if not summary:
            return
        rows.append(
            {
                "vod_id": vod_id,
                "match_id": match_id,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "subject_name": name,
                "sentiment": sentiment,
                "rating": clamp_rating(item.get("rating")),
                "summary": summary[:2000],
                "quotes": item.get("quotes") or [],
                "extra": extra or {},
                "ai_risk": item.get("risk"),
                "model": model,
                "status": "pending",
            }
        )

    def summary_of(item: dict[str, Any]) -> str:
        """headline/verdict + 要点拼接为 summary 落库（展示层优先用 extra 里的结构化字段）。"""
        head = (item.get("headline") or item.get("verdict") or item.get("summary") or "").strip()
        points = [str(x).strip() for x in (item.get("points") or []) if str(x).strip()]
        return "\n".join(x for x in [head, *points] if x)

    if result.bp:
        add(
            "bp",
            "BP与阵容",
            {**result.bp, "summary": summary_of(result.bp)},
            extra={
                "headline": result.bp.get("headline") or "",
                "points": result.bp.get("points") or [],
                "predictions": result.bp.get("predictions") or [],
            },
        )
    if result.flow:
        flow_summary = "\n".join(
            f"【{label}】{result.flow.get(key)}"
            for key, label in (("early", "前期"), ("mid", "中期"), ("late", "后期"))
            if result.flow.get(key)
        )
        add(
            "flow",
            "局势走向",
            {**result.flow, "summary": flow_summary},
            extra={"turning_points": result.flow.get("turning_points") or []},
        )
    if result.overall:
        add(
            "overall",
            "整场比赛",
            {**result.overall, "summary": summary_of(result.overall)},
            extra={
                "headline": result.overall.get("headline") or "",
                "points": result.overall.get("points") or [],
            },
        )
    for t in result.teams:
        name = (t.get("name") or "").strip()
        if name:
            add(
                "team",
                name,
                {**t, "summary": summary_of(t)},
                subject_id=alias_to_tid.get(name.upper()),
                extra={"verdict": t.get("verdict") or "", "points": t.get("points") or []},
            )
    for p in result.players:
        name = (p.get("name") or "").strip()
        if name:
            add(
                "player",
                name,
                {**p, "summary": summary_of(p)},
                extra={
                    "verdict": p.get("verdict") or "",
                    "points": p.get("points") or [],
                    "highlight": p.get("highlight") or "",
                    "lowlight": p.get("lowlight") or "",
                },
            )
    if result.blame:
        add(
            "blame",
            "赛后分锅",
            {**result.blame, "summary": summary_of(result.blame)},
            extra={"headline": result.blame.get("headline") or "", "main": result.blame.get("main") or []},
        )
    if result.golden_quotes:
        add(
            "golden",
            "金句时刻",
            {"summary": "本场解说金句", "sentiment": "中立", "quotes": result.golden_quotes},
        )
    return rows
