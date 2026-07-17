"""单视频全链串行处理（验收/手动补跑用）。

用法：
  python -m scripts.process_vod --bvid BV1xxxx            # 下载→转写→分析→入库
  python -m scripts.process_vod --bvid BV1xxxx --step download|transcribe|analyze
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvid", required=True)
    parser.add_argument("--step", choices=["download", "transcribe", "analyze"])
    args = parser.parse_args()

    from vod_pipeline import process_vod_analyze, process_vod_download, process_vod_transcribe

    steps = [args.step] if args.step else ["download", "transcribe", "analyze"]
    for step in steps:
        t0 = time.time()
        print(f"== {step} {args.bvid} ==")
        if step == "download":
            wav = process_vod_download(args.bvid)
            print(f"   音频: {wav} ({wav.stat().st_size // 1024} KB)")
        elif step == "transcribe":
            segments, speaker_map = process_vod_transcribe(args.bvid)
            from collections import Counter

            counts = Counter(s.speaker for s in segments)
            print(f"   {len(segments)} 段 | 说话人: {dict(counts)} | 归属: {speaker_map}")
        elif step == "analyze":
            result = process_vod_analyze(args.bvid)
            print(f"   整体: {result.overall and result.overall.get('sentiment')}")
            print(f"   战队评价 {len(result.teams)} 条 | 选手评价 {len(result.players)} 条")
            print(f"   tokens: {result.prompt_tokens}+{result.completion_tokens}")
        print(f"   耗时 {time.time() - t0:.1f}s")
    print("全部完成。insights 状态为 pending，人工审核后前台可见。")


if __name__ == "__main__":
    main()
