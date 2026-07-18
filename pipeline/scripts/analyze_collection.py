"""合集型二路视频处理：逐局分析 + 系列赛汇总。

BO5 每局对应一个分P：每局单独 下载→转写→分析，再由 AI 汇总整场。

用法：
  python -m scripts.analyze_collection --bvid BV1TcNd6UEV6 --pages 1-5 --caster 可温 \
      --up-name kpl二路 --mid 333332650 --match-id 2026071703
  可选：--ingest（迁移后入库）--force-transcribe（重跑转写）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def parse_pages(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def ts() -> str:
    return time.strftime("%H:%M:%S")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvid", required=True)
    parser.add_argument("--pages", required=True, help="如 1-5：每个分P是一局，逐局分析")
    parser.add_argument("--caster", required=True)
    parser.add_argument("--up-name", default="")
    parser.add_argument("--mid", type=int, default=None)
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--force-transcribe", action="store_true")
    args = parser.parse_args()
    pages = parse_pages(args.pages)

    from asr.funasr_transcriber import load_transcript, save_transcript, transcribe
    from asr.speaker_attribution import attribute_speakers
    from db.supabase_client import SupabaseRest
    from media.audio_downloader import audio_key, download_audio
    from vod_pipeline import _match_meta, match_roster_and_hotwords
    from ai.insight_extractor import InsightExtractor

    audio_dir = ROOT / "data" / "audio"
    db = SupabaseRest()
    meta = _match_meta(db, args.match_id)
    meta["caster"] = args.caster
    roster, hotword = match_roster_and_hotwords(args.match_id)
    print(f"[{ts()}] 比赛 {meta.get('team_a')} {meta.get('score')} {meta.get('team_b')} | 名单 {len(roster)} 人 | 热词 {len(hotword.split())} 个", flush=True)

    extractor = InsightExtractor()
    games: list[dict] = []
    total_tokens = [0, 0]

    # ---------- 逐局 ----------
    for game_no, page in enumerate(pages, start=1):
        key = audio_key(args.bvid, [page])
        transcript_path = ROOT / "data" / "transcripts" / f"{key}.json"
        print(f"[{ts()}] ══ 第{game_no}局（P{page}）══", flush=True)

        t0 = time.time()
        wav = download_audio(args.bvid, audio_dir, pages=[page])
        print(f"[{ts()}]   音频 {wav.name} ({wav.stat().st_size // 1024 // 1024} MB)", flush=True)

        if args.force_transcribe and transcript_path.exists():
            transcript_path.unlink()
        if transcript_path.exists():
            segments = load_transcript(transcript_path)
            print(f"[{ts()}]   复用转写 {len(segments)} 段", flush=True)
        else:
            t0 = time.time()
            segments = transcribe(wav, hotword=hotword)
            print(f"[{ts()}]   转写完成 {len(segments)} 段 耗时 {time.time()-t0:.0f}s", flush=True)

        attribution = attribute_speakers(segments, wav)
        save_transcript(
            transcript_path,
            segments,
            {
                "speaker_map": attribution.mapping,
                "attribution_confidence": attribution.confidence,
                "caster": args.caster,
                "game_no": game_no,
            },
        )
        print(f"[{ts()}]   归属置信 {attribution.confidence:.2f}", flush=True)

        game_meta = {**meta, "game_no": game_no, "说明": f"本转写只覆盖第{game_no}局（系列赛共打{meta.get('score')}）"}
        t0 = time.time()
        result = extractor.extract(
            segments=segments,
            speaker_map=attribution.mapping,
            match_meta=game_meta,
            roster=roster,
        )
        total_tokens[0] += result.prompt_tokens
        total_tokens[1] += result.completion_tokens
        if result.error:
            print(f"[{ts()}]   第{game_no}局分析失败: {result.error}", flush=True)
            continue
        print(
            f"[{ts()}]   分析完成 耗时 {time.time()-t0:.0f}s | 选手 {len(result.players)} 金句 {len(result.golden_quotes)}",
            flush=True,
        )
        games.append(
            {
                "game_no": game_no,
                "page": page,
                "bp": result.bp,
                "flow": result.flow,
                "overall": result.overall,
                "teams": result.teams,
                "players": result.players,
                "blame": result.blame,
                "golden_quotes": result.golden_quotes,
            }
        )

    if not games:
        print("没有任何一局分析成功", flush=True)
        sys.exit(1)

    # ---------- 系列赛汇总 ----------
    print(f"[{ts()}] ══ 系列赛汇总（{len(games)} 局）══", flush=True)
    slim_games = [
        {
            "game_no": g["game_no"],
            "overall": g["overall"],
            "teams": g["teams"],
            "players": g["players"],
            "blame": g["blame"],
        }
        for g in games
    ]
    series, usage = extractor.aggregate_series(
        game_payloads=slim_games, match_meta=meta, roster=roster
    )
    total_tokens[0] += usage["prompt_tokens"]
    total_tokens[1] += usage["completion_tokens"]
    if series:
        ov = series.get("overall") or {}
        print(f"[{ts()}]   整场: {ov.get('sentiment')} - {ov.get('headline')}", flush=True)
        for p in (series.get("players") or [])[:8]:
            print(f"   【{p.get('name')}】{p.get('sentiment')} ★{p.get('rating')} - {p.get('verdict')}", flush=True)
    else:
        print(f"[{ts()}]   汇总失败（保留分局结果）", flush=True)

    # ---------- 终审 ----------
    payload = {
        "bvid": args.bvid,
        "pages": pages,
        "caster": args.caster,
        "match_id": args.match_id,
        "games": games,
        "series": series,
        "model": extractor.client.model,
    }
    print(f"[{ts()}] ══ 终审 ══", flush=True)
    payload, fixes, usage = extractor.review_payload(payload=payload, match_meta=meta, roster=roster)
    total_tokens[0] += usage["prompt_tokens"]
    total_tokens[1] += usage["completion_tokens"]
    for f in fixes[:10]:
        print(f"   修订: {f}", flush=True)

    # ---------- 落盘 ----------
    out = ROOT / "data" / "insights" / f"{audio_key(args.bvid, pages)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{ts()}] 结果已存 {out} | tokens {total_tokens[0]}+{total_tokens[1]}", flush=True)
    print("E2E_DONE", flush=True)


if __name__ == "__main__":
    main()
