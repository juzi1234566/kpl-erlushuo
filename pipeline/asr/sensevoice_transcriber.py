"""SenseVoice 快速转写后端：VAD 切段 → 分段识别 → cam++ 声纹聚类分说话人。

比 paraformer 管线快 3-5 倍（CPU RTF ~0.2），代价：无热词、错字略多
（由校对层/终审层兜底）。输出与 paraformer 管线相同的 Segment 列表。
"""

from __future__ import annotations

import re
import wave
from pathlib import Path
from typing import Any, Optional

import numpy as np

from asr.funasr_transcriber import Segment

_VAD_MODEL = None
_SV_MODEL = None
_EMB_MODEL = None

# 声纹聚类：余弦相似度阈值（越高分得越细）
CLUSTER_THRESHOLD = 0.60
MAX_SPEAKERS = 8
# 提声纹时每段最多取中间这么长（秒），太短的段跳过声纹直接并入最近说话人
EMB_MAX_SEC = 6.0
EMB_MIN_SEC = 0.8


def _get_vad():
    global _VAD_MODEL
    if _VAD_MODEL is None:
        from funasr import AutoModel

        _VAD_MODEL = AutoModel(model="fsmn-vad", device="cpu", disable_update=True)
    return _VAD_MODEL


def _get_sv():
    global _SV_MODEL
    if _SV_MODEL is None:
        from funasr import AutoModel

        _SV_MODEL = AutoModel(model="iic/SenseVoiceSmall", device="cpu", disable_update=True)
    return _SV_MODEL


def _get_emb():
    global _EMB_MODEL
    if _EMB_MODEL is None:
        from funasr import AutoModel

        _EMB_MODEL = AutoModel(
            model="iic/speech_campplus_sv_zh-cn_16k-common", device="cpu", disable_update=True
        )
    return _EMB_MODEL


_TAG_RE = re.compile(r"<\|[^|]*\|>")


def _clean_text(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        assert wf.getframerate() == 16000 and wf.getnchannels() == 1, "需要 16k 单声道 wav"
        data = wf.readframes(wf.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def _extract_embedding(chunk: np.ndarray) -> Optional[np.ndarray]:
    """cam++ 声纹；段太短返回 None。"""
    if chunk.shape[0] < EMB_MIN_SEC * 16000:
        return None
    if chunk.shape[0] > EMB_MAX_SEC * 16000:
        mid = chunk.shape[0] // 2
        half = int(EMB_MAX_SEC * 16000 / 2)
        chunk = chunk[mid - half : mid + half]
    try:
        res = _get_emb().generate(input=chunk, fs=16000)
        emb = res[0].get("spk_embedding")
        if emb is None:
            return None
        vec = np.asarray(emb, dtype=np.float32).reshape(-1)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else None
    except Exception:  # noqa: BLE001
        return None


def _cluster_speakers(embeddings: list[Optional[np.ndarray]]) -> list[int]:
    """贪心声纹聚类：与最近簇心相似则并入，否则开新簇；None 段继承上一段。"""
    centroids: list[np.ndarray] = []
    counts: list[int] = []
    labels: list[int] = []
    last_label = 0
    for emb in embeddings:
        if emb is None:
            labels.append(last_label if centroids else 0)
            continue
        if not centroids:
            centroids.append(emb.copy())
            counts.append(1)
            labels.append(0)
            last_label = 0
            continue
        sims = [float(np.dot(emb, c) / (np.linalg.norm(c) or 1)) for c in centroids]
        best = int(np.argmax(sims))
        if sims[best] >= CLUSTER_THRESHOLD or len(centroids) >= MAX_SPEAKERS:
            centroids[best] = centroids[best] + (emb - centroids[best]) / (counts[best] + 1)
            counts[best] += 1
            labels.append(best)
            last_label = best
        else:
            centroids.append(emb.copy())
            counts.append(1)
            labels.append(len(centroids) - 1)
            last_label = len(centroids) - 1
    return labels


def transcribe_sensevoice(wav_path: Path) -> list[Segment]:
    """VAD 切段 → SenseVoice 识别 → cam++ 聚类分说话人。"""
    audio = _load_wav(wav_path)

    # 1. VAD 切段（毫秒）
    vad_res = _get_vad().generate(input=str(wav_path))
    spans: list[tuple[int, int]] = [
        (int(s), int(e)) for s, e in (vad_res[0].get("value") or []) if e > s
    ]
    if not spans:
        return []

    # 2. 分段识别（分批喂，控内存）
    sv = _get_sv()
    texts: list[str] = []
    batch: list[np.ndarray] = []
    batch_size = 16
    chunks = [audio[int(s * 16) : int(e * 16)] for s, e in spans]
    for i in range(0, len(chunks), batch_size):
        part = chunks[i : i + batch_size]
        res = sv.generate(input=part, fs=16000, batch_size=len(part))
        texts.extend(_clean_text(r.get("text") or "") for r in res)

    # 3. 声纹聚类
    embeddings = [_extract_embedding(c) for c in chunks]
    labels = _cluster_speakers(embeddings)

    segments = [
        Segment(start_ms=s, end_ms=e, speaker=f"spk{label}", text=text)
        for (s, e), text, label in zip(spans, texts, labels)
        if text
    ]
    return segments
