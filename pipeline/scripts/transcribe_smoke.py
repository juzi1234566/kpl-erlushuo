"""ASR 全链冒烟：对已下载的真实人声 wav 跑 转写+说话人分离+归属。

用法：python -m scripts.transcribe_smoke [--bvid BV13PKV6zEUB]
输出进度写 stdout（配合重定向到日志观察）。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvid", default="BV13PKV6zEUB")
    args = parser.parse_args()

    wav = ROOT / "data" / "audio" / f"{args.bvid}.wav"
    out = ROOT / "data" / "transcripts" / f"{args.bvid}.json"
    print(f"[{time.strftime('%H:%M:%S')}] 输入: {wav} ({wav.stat().st_size // 1024 // 1024} MB)", flush=True)

    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] 加载模型（首次会下载，几分钟）…", flush=True)
    from asr.funasr_transcriber import save_transcript, transcribe

    segments = transcribe(wav)
    print(f"[{time.strftime('%H:%M:%S')}] 转写完成: {len(segments)} 段，耗时 {time.time()-t0:.0f}s", flush=True)

    from collections import Counter

    counts = Counter(s.speaker for s in segments)
    print("说话人分布:", dict(counts), flush=True)

    from asr.speaker_attribution import attribute_speakers

    attribution = attribute_speakers(segments, wav)
    print("归属:", attribution.mapping, "置信度:", round(attribution.confidence, 2), flush=True)

    save_transcript(
        out,
        segments,
        {
            "speaker_map": attribution.mapping,
            "attribution_confidence": attribution.confidence,
            "attribution_detail": attribution.detail,
        },
    )
    print("样例（前 5 段）:", flush=True)
    for s in segments[:5]:
        print(f"  [{s.start_ms}-{s.end_ms}] {s.speaker}: {s.text[:40]}", flush=True)
    print("SMOKE_DONE", flush=True)


if __name__ == "__main__":
    main()
