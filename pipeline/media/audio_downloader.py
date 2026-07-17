"""B站视频音频下载：yt-dlp 取 bestaudio → ffmpeg 转 16kHz 单声道 wav。

- B站直连，显式禁用代理
- 幂等：目标 wav 已存在直接返回
- 超长视频（默认 >3h）跳过
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

MAX_DURATION_S_DEFAULT = 3 * 3600


class SkipVideo(RuntimeError):
    """视频不适合处理（超长/多P等），非失败。"""


def download_audio(
    bvid: str,
    out_dir: Path,
    *,
    max_duration_s: int = MAX_DURATION_S_DEFAULT,
    sessdata: Optional[str] = None,
) -> Path:
    """下载并转码，返回 wav 路径。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / f"{bvid}.wav"
    if wav_path.exists() and wav_path.stat().st_size > 0:
        return wav_path

    import yt_dlp  # 延迟导入：只有真正下载才需要

    url = f"https://www.bilibili.com/video/{bvid}"
    sessdata = sessdata or os.getenv("BILI_SESSDATA") or ""
    tmp_tpl = str(out_dir / f"{bvid}.%(ext)s")

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": tmp_tpl,
        "proxy": "",  # B站直连，绝不走代理
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
        # FunASR 需要 16k 单声道
        "postprocessor_args": {"extractaudio": ["-ar", "16000", "-ac", "1"]},
    }
    if sessdata:
        ydl_opts["http_headers"] = {"Cookie": f"SESSDATA={sessdata}"}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        duration = int(info.get("duration") or 0)
        if duration > max_duration_s:
            raise SkipVideo(f"{bvid} 时长 {duration}s 超过上限 {max_duration_s}s")
        ydl.download([url])

    if not wav_path.exists():
        # yt-dlp 可能按 info 的标题落名，兜底找同 bvid 前缀的 wav
        candidates = list(out_dir.glob(f"{bvid}*.wav"))
        if candidates:
            candidates[0].rename(wav_path)
    if not wav_path.exists():
        raise RuntimeError(f"{bvid} 下载后未找到 wav 输出")
    return wav_path
