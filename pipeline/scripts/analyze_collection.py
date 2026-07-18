"""合集型二路视频处理：指定 bvid + 分P范围 + 主播名 + 比赛，跑完整分析链。

用法：
  # 本地验证（不写库，结果落 data/insights/）：
  python -m scripts.analyze_collection --bvid BV1TcNd6UEV6 --pages 1-5 --caster 可温 \
      --up-name kpl二路 --mid 333332650 --match-id 2026071703

  # 迁移 0002 执行后加 --ingest 写入 vod_sources + commentary_insights
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvid", required=True)
    parser.add_argument("--pages", required=True, help="如 1-5 或 3,4")
    parser.add_argument("--caster", required=True, help="主播名（展示用）")
    parser.add_argument("--up-name", default="", help="B站UP账号名")
    parser.add_argument("--mid", type=int, default=None)
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--ingest", action="store_true", help="写入 Supabase（需迁移 0002）")
    args = parser.parse_args()
    pages = parse_pages(args.pages)

    from asr.funasr_transcriber import save_transcript, transcribe
    from asr.speaker_attribution import attribute_speakers
    from db.supabase_client import SupabaseRest
    from media.audio_downloader import audio_key, download_audio
    from vod_pipeline import _match_meta, build_insight_rows
    from ai.insight_extractor import InsightExtractor

    key = audio_key(args.bvid, pages)
    audio_dir = ROOT / "data" / "audio"
    transcript_path = ROOT / "data" / "transcripts" / f"{key}.json"
    insights_path = ROOT / "data" / "insights" / f"{key}.json"

    # 1. 下载
    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] 下载 {args.bvid} P{pages[0]}-P{pages[-1]} …", flush=True)
    wav = download_audio(args.bvid, audio_dir, pages=pages)
    print(f"[{time.strftime('%H:%M:%S')}] 音频就绪 {wav.name} ({wav.stat().st_size // 1024 // 1024} MB) 耗时 {time.time()-t0:.0f}s", flush=True)

    # 2. 转写 + 归属
    t0 = time.time()
    if transcript_path.exists():
        from asr.funasr_transcriber import load_transcript

        segments = load_transcript(transcript_path)
        print(f"[{time.strftime('%H:%M:%S')}] 复用已有转写 {len(segments)} 段", flush=True)
    else:
        print(f"[{time.strftime('%H:%M:%S')}] 转写中（约 0.7x 实时）…", flush=True)
        segments = transcribe(wav)
        print(f"[{time.strftime('%H:%M:%S')}] 转写完成 {len(segments)} 段 耗时 {time.time()-t0:.0f}s", flush=True)

    attribution = attribute_speakers(segments, wav)
    save_transcript(
        transcript_path,
        segments,
        {
            "speaker_map": attribution.mapping,
            "attribution_confidence": attribution.confidence,
            "attribution_detail": attribution.detail,
            "caster": args.caster,
        },
    )
    up_spk = [k for k, v in attribution.mapping.items() if v == "up"]
    print(f"[{time.strftime('%H:%M:%S')}] 归属 {attribution.mapping} 置信 {attribution.confidence:.2f}", flush=True)

    # 3. AI 观点提取
    db = SupabaseRest()
    meta = _match_meta(db, args.match_id)
    meta["caster"] = args.caster
    print(f"[{time.strftime('%H:%M:%S')}] 比赛: {meta.get('team_a')} {meta.get('score')} {meta.get('team_b')}，DeepSeek 分析中…", flush=True)
    t0 = time.time()
    extractor = InsightExtractor()
    result = extractor.extract(segments=segments, speaker_map=attribution.mapping, match_meta=meta)
    if result.error:
        print(f"分析失败: {result.error}", flush=True)
        sys.exit(1)
    print(
        f"[{time.strftime('%H:%M:%S')}] 分析完成 耗时 {time.time()-t0:.0f}s | "
        f"整体:{result.overall and result.overall.get('sentiment')} 战队:{len(result.teams)} 选手:{len(result.players)} "
        f"| tokens {result.prompt_tokens}+{result.completion_tokens}",
        flush=True,
    )

    # 4. 落盘 / 入库
    insights_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bvid": args.bvid,
        "pages": pages,
        "caster": args.caster,
        "match_id": args.match_id,
        "overall": result.overall,
        "teams": result.teams,
        "players": result.players,
        "model": result.model,
    }
    insights_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果已存 {insights_path}", flush=True)

    if args.ingest:
        vod_row = {
            "bvid": args.bvid,
            "page_start": pages[0],
            "page_end": pages[-1],
            "caster_name": args.caster,
            "title": f"{args.caster} 二路解说",
            "up_name": args.caster,  # 展示用主播名
            "mid": args.mid,
            "match_id": args.match_id,
            "match_confidence": 1.0,
            "match_method": "manual",
            "needs_review": False,
            "audio_status": "done",
            "audio_ref": str(wav.relative_to(ROOT)),
            "transcript_status": "done",
            "transcript_ref": str(transcript_path.relative_to(ROOT)),
            "analysis_status": "done",
        }
        db.upsert("vod_sources", [vod_row], on_conflict="bvid,page_start")
        rows = db.select("vod_sources", f"select=id&bvid=eq.{args.bvid}&page_start=eq.{pages[0]}")
        vod_id = rows[0]["id"]
        insight_rows = build_insight_rows(result, vod_id=vod_id, match_id=args.match_id, model=result.model)
        if insight_rows:
            db.upsert("commentary_insights", insight_rows, on_conflict="vod_id,subject_type,subject_name")
        print(f"已入库 vod={vod_id} insights x{len(insight_rows)}（状态 pending，审核后前台可见）", flush=True)

    # 预览
    if result.overall:
        print("\n【整体】", result.overall.get("sentiment"), "-", result.overall.get("summary"), flush=True)
    for t in result.teams:
        print(f"【{t.get('name')}】{t.get('sentiment')} - {str(t.get('summary'))[:60]}", flush=True)
    for p in result.players[:5]:
        print(f"【{p.get('name')}】{p.get('sentiment')} - {str(p.get('summary'))[:60]}", flush=True)
    print("E2E_DONE", flush=True)


if __name__ == "__main__":
    main()
