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


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _bili_headers(sessdata: str) -> dict:
    headers = {"User-Agent": _UA, "Referer": "https://www.bilibili.com/"}
    if sessdata:
        headers["Cookie"] = f"SESSDATA={sessdata}"
    return headers


def _api_json(url: str, params: dict, sessdata: str) -> dict:
    import httpx

    with httpx.Client(trust_env=False, timeout=30) as cli:  # B站直连，绝不走代理
        resp = cli.get(url, params=params, headers=_bili_headers(sessdata))
        resp.raise_for_status()
        data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"B站 API {url} code={data.get('code')} {data.get('message')}")
    return data["data"]


def _download_one(
    bvid: str,
    out_dir: Path,
    part_key: str,
    *,
    page: Optional[int],
    sessdata: Optional[str],
) -> int:
    """下载单个分P，返回其时长（秒）。

    走 API（view→playurl→CDN 音频流），不碰 www 网页——机房 IP 访问网页会被 412，
    API 与 CDN 不受影响。API 路线失败时回退 yt-dlp（住宅网络可用）。
    """
    sessdata = sessdata or os.getenv("BILI_SESSDATA") or ""
    try:
        return _download_one_api(bvid, out_dir, part_key, page=page, sessdata=sessdata)
    except Exception:
        return _download_one_ytdlp(bvid, out_dir, part_key, page=page, sessdata=sessdata)


def _download_one_api(
    bvid: str,
    out_dir: Path,
    part_key: str,
    *,
    page: Optional[int],
    sessdata: str,
) -> int:
    import subprocess

    import httpx

    view = _api_json(
        "https://api.bilibili.com/x/web-interface/view", {"bvid": bvid}, sessdata
    )
    pages = view.get("pages") or []
    entry = None
    if page:
        entry = next((p for p in pages if p.get("page") == page), None)
    elif pages:
        entry = pages[0]
    if not entry:
        raise RuntimeError(f"{bvid} 找不到分P {page}")
    cid = entry["cid"]
    duration = int(entry.get("duration") or 0)

    play = _api_json(
        "https://api.bilibili.com/x/player/playurl",
        {"bvid": bvid, "cid": cid, "fnval": 16},
        sessdata,
    )
    audios = (play.get("dash") or {}).get("audio") or []
    if not audios:
        raise RuntimeError(f"{bvid} P{page} 无 DASH 音频流")
    best = max(audios, key=lambda a: a.get("bandwidth") or 0)
    urls = [best.get("baseUrl")] + list(best.get("backupUrl") or [])

    m4s_path = out_dir / f"{part_key}.m4s"
    last_err: Exception | None = None
    for u in [u for u in urls if u]:
        try:
            with httpx.Client(trust_env=False, timeout=60) as cli:
                with cli.stream("GET", u, headers=_bili_headers(sessdata)) as resp:
                    resp.raise_for_status()
                    with open(m4s_path, "wb") as f:
                        for chunk in resp.iter_bytes(1 << 20):
                            f.write(chunk)
            last_err = None
            break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    if last_err is not None:
        raise last_err

    wav_path = out_dir / f"{part_key}.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(m4s_path), "-ar", "16000", "-ac", "1", str(wav_path)],
            check=True,
            capture_output=True,
        )
    finally:
        m4s_path.unlink(missing_ok=True)
    return duration


def _download_one_ytdlp(
    bvid: str,
    out_dir: Path,
    part_key: str,
    *,
    page: Optional[int],
    sessdata: str,
) -> int:
    import yt_dlp  # 延迟导入

    url = f"https://www.bilibili.com/video/{bvid}"
    if page:
        url += f"?p={page}"

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
