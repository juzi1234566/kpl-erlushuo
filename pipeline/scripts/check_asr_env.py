"""ASR 环境自检：依赖导入 + 合成样音转写冒烟。

用法：python -m scripts.check_asr_env [--full]
  默认只查导入；--full 会下载模型并跑 5 秒静音样本（首次约需数分钟下载模型）
"""

from __future__ import annotations

import argparse
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_imports() -> bool:
    ok = True
    for mod in ("torch", "torchaudio", "funasr", "yt_dlp", "numpy"):
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "?")
            print(f"  {mod:<12} ✅ {ver}")
        except ImportError as exc:
            print(f"  {mod:<12} ❌ {exc}")
            ok = False
    if shutil.which("ffmpeg"):
        print("  ffmpeg       ✅")
    else:
        print("  ffmpeg       ❌ 未在 PATH 中")
        ok = False
    import torch

    print(f"  torch device  cpu（cuda={'可用' if torch.cuda.is_available() else '不可用，符合预期'}）")
    return ok


def smoke_transcribe() -> None:
    """生成 5 秒 440Hz 音 + 静音的样本，跑一遍模型管线（验证模型可下载可推理）。"""
    import numpy as np

    sample = ROOT / "data" / "audio" / "_smoke.wav"
    sample.parent.mkdir(parents=True, exist_ok=True)
    rate = 16000
    t = np.linspace(0, 5, rate * 5, endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 8000).astype(np.int16)
    with wave.open(str(sample), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(tone.tobytes())

    from asr.funasr_transcriber import transcribe

    print("  模型加载中（首次会从 modelscope 下载，几分钟）…")
    segments = transcribe(sample)
    print(f"  转写完成：{len(segments)} 段（纯音样本预期 0 段，管线可用）")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    print("依赖检查：")
    if not check_imports():
        print("依赖不全：torch 需先装 CPU 轮子：")
        print("  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu")
        print("  pip install funasr modelscope yt-dlp numpy")
        sys.exit(1)
    if args.full:
        smoke_transcribe()
    print("ASR 环境检查通过")


if __name__ == "__main__":
    main()
