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


def audio_key(bvid: str, pages: Optional[list[int]] = None) -> str:
    """音频文件名主键：单P直接 bvid；多P带页码范围。"""
    if not pages:
        return bvid
    return f"{bvid}_p{min(pages)}-{max(pages)}"


def download_audio(
    bvid: str,
    out_dir: Path,
    *,
    pages: Optional[list[int]] = None,
    max_duration_s: int = MAX_DURATION_S_DEFAULT,
    sessdata: Optional[str] = None,
) -> Path:
    """下载并转码，返回 wav 路径。

    pages：合集视频里要取的分P页码（如 [1,2,3,4,5]），多页会按顺序拼接为一个 wav。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    key = audio_key(bvid, pages)
    wav_path = out_dir / f"{key}.wav"
    if wav_path.exists() and wav_path.stat().st_size > 0:
        return wav_path

    page_list = pages or [None]  # None = 整条（单P视频）
    part_paths: list[Path] = []
    total_duration = 0
    for p in page_list:
        part_key = f"{bvid}_part{p}" if p else bvid
        part_wav = out_dir / f"{part_key}.wav"
        if not (part_wav.exists() and part_wav.stat().st_size > 0):
            duration = _download_one(bvid, out_dir, part_key, page=p, sessdata=sessdata)
            total_duration += duration
            if total_duration > max_duration_s:
                raise SkipVideo(f"{key} 累计时长超过上限 {max_duration_s}s")
        if not part_wav.exists():
            raise RuntimeError(f"{bvid} P{p} 下载后未找到 wav")
        part_paths.append(part_wav)

    if len(part_paths) == 1:
        if part_paths[0] != wav_path:
            part_paths[0].rename(wav_path)
        return wav_path

    _concat_wavs(part_paths, wav_path)
    for p in part_paths:
        p.unlink(missing_ok=True)
    return wav_path


def _download_one(
    bvid: str,
    out_dir: Path,
    part_key: str,
    *,
    page: Optional[int],
    sessdata: Optional[str],
) -> int:
    """下载单个分P，返回其时长（秒）。"""
    import yt_dlp  # 延迟导入

    url = f"https://www.bilibili.com/video/{bvid}"
    if page:
        url += f"?p={page}"
    sessdata = sessdata or os.getenv("BILI_SESSDATA") or ""

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / f"{part_key}.%(ext)s"),
        "proxy": "",  # B站直连，绝不走代理
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        # FunASR 需要 16k 单声道
        "postprocessor_args": {"extractaudio": ["-ar", "16000", "-ac", "1"]},
    }
    if sessdata:
        ydl_opts["http_headers"] = {"Cookie": f"SESSDATA={sessdata}"}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return int(info.get("duration") or 0)


def _concat_wavs(parts: list[Path], out: Path) -> None:
    """ffmpeg concat 多段 wav（同为 16k 单声道，无需重采样）。"""
    import subprocess

    list_file = out.with_suffix(".txt")
    list_file.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in parts),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)],
            check=True,
            capture_output=True,
        )
    finally:
        list_file.unlink(missing_ok=True)
