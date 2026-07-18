"""SenseVoice 后端验证：用 P1 音频跑全链，与 paraformer 已有结果对比归属一致性。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> None:
    from asr.funasr_transcriber import load_transcript
    from asr.sensevoice_transcriber import transcribe_sensevoice
    from asr.speaker_attribution import attribute_speakers

    wav = ROOT / "data" / "audio" / "BV1TcNd6UEV6_p1-1.wav"
    ref_path = ROOT / "data" / "transcripts" / "BV1TcNd6UEV6_p1-1.json"

    t0 = time.time()
    print("SenseVoice 全链开始…", flush=True)
    segments = transcribe_sensevoice(wav)
    elapsed = time.time() - t0
    dur = 2032
    print(f"转写+声纹完成: {len(segments)} 段, 耗时 {elapsed:.0f}s (RTF {elapsed/dur:.2f})", flush=True)

    attribution = attribute_speakers(segments, wav)
    up_spks = [k for k, v in attribution.mapping.items() if v == "up"]
    print(f"归属: up={up_spks} 置信 {attribution.confidence:.2f}", flush=True)
    share = attribution.detail.get("duration_share") or {}
    print("时长占比 top3:", dict(sorted(share.items(), key=lambda x: -x[1])[:3]), flush=True)

    # 与 paraformer 基准对比：按时间重叠计算 UP 段一致率
    ref = load_transcript(ref_path)
    import json

    ref_meta = json.loads(ref_path.read_text(encoding="utf-8")).get("meta") or {}
    ref_map = ref_meta.get("speaker_map") or {}
    ref_up = [(s.start_ms, s.end_ms) for s in ref if ref_map.get(s.speaker) == "up"]
    sv_up = [(s.start_ms, s.end_ms) for s in segments if attribution.mapping.get(s.speaker) == "up"]

    def total(spans):
        return sum(e - s for s, e in spans)

    def overlap(a, b):
        out = 0
        for s1, e1 in a:
            for s2, e2 in b:
                out += max(0, min(e1, e2) - max(s1, s2))
        return out

    inter = overlap(ref_up, sv_up)
    ref_t, sv_t = total(ref_up), total(sv_up)
    print(f"UP 时长: paraformer {ref_t//1000}s | sensevoice {sv_t//1000}s", flush=True)
    if ref_t and sv_t:
        print(f"重叠率: 召回 {inter/ref_t:.0%} / 精确 {inter/sv_t:.0%}", flush=True)

    # 文本抽样
    ups = [s for s in segments if attribution.mapping.get(s.speaker) == "up"]
    for s in ups[30:34]:
        print(f"  [{s.start_ms//60000}:{s.start_ms%60000//1000:02d}] {s.text[:44]}", flush=True)
    print("VALIDATE_DONE", flush=True)


if __name__ == "__main__":
    main()
