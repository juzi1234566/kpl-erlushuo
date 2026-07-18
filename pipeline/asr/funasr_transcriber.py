"""FunASR 转写 + 说话人分离封装。

模型组合：paraformer-zh（ASR）+ fsmn-vad（断句）+ ct-punc（标点）+ cam++（说话人）
- CPU 运行；模型进程内单例懒加载（首次加载约 1-2 分钟）
- 幂等：输出 JSON 已存在直接加载返回
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class Segment:
    start_ms: int
    end_ms: int
    speaker: str  # 'spk0' / 'spk1' ...
    text: str


_MODEL = None  # 进程内单例


def _get_model():
    global _MODEL
    if _MODEL is None:
        from funasr import AutoModel

        _MODEL = AutoModel(
            model="paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            spk_model="cam++",
            device="cpu",
            disable_update=True,
        )
    return _MODEL


def transcribe(
    wav_path: Path,
    out_path: Optional[Path] = None,
    *,
    hotword: str = "",
) -> list[Segment]:
    """转写整段音频，返回带说话人标签的分句列表。

    引擎由环境变量 ASR_ENGINE 控制：
    - paraformer（默认）：质量最好，支持热词，CPU RTF ~0.7
    - sensevoice：快 3-5 倍（RTF ~0.2），无热词，配 cam++ 声纹聚类分说话人
    """
    if out_path and out_path.exists():
        return load_transcript(out_path)

    import os

    if (os.getenv("ASR_ENGINE") or "").lower() == "sensevoice":
        from asr.sensevoice_transcriber import transcribe_sensevoice

        segments = transcribe_sensevoice(wav_path)
        if out_path:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps({"segments": [asdict(s) for s in segments]}, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        return segments

    model = _get_model()
    result = model.generate(
        input=str(wav_path),
        batch_size_s=300,
        hotword=hotword,
    )
    segments = _parse_result(result)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {"segments": [asdict(s) for s in segments]},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    return segments


def _parse_result(result: Any) -> list[Segment]:
    """FunASR 输出 → Segment 列表。带 spk 时用 sentence_info。"""
    segments: list[Segment] = []
    for item in result or []:
        sentences = item.get("sentence_info") or []
        if sentences:
            for s in sentences:
                segments.append(
                    Segment(
                        start_ms=int(s.get("start") or 0),
                        end_ms=int(s.get("end") or 0),
                        speaker=f"spk{s.get('spk', 0)}",
                        text=(s.get("text") or "").strip(),
                    )
                )
        elif item.get("text"):
            # 无说话人信息的兜底（不应发生，但别丢数据）
            segments.append(
                Segment(start_ms=0, end_ms=0, speaker="spk0", text=item["text"].strip())
            )
    return [s for s in segments if s.text]


def load_transcript(path: Path) -> list[Segment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Segment(**s) for s in data.get("segments", [])]


def save_transcript(path: Path, segments: list[Segment], meta: Optional[dict] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"segments": [asdict(s) for s in segments]}
    if meta:
        payload["meta"] = meta
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
