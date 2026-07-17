"""说话人归属：判定哪个 speaker 是 UP主（人声主体），哪个是背景官方解说。

启发式加权（按可靠性）：
1. 说话时长占比（主信号）：二路视频里 UP 几乎全程说话
2. 平均响度 RMS（次信号）：UP 麦克风人声显著响于透出来的官方解说
3. 词面线索（校验信号）：只用于冲突时降置信
人工覆盖（up_profiles.speaker_hint）优先于一切。
"""

from __future__ import annotations

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from asr.funasr_transcriber import Segment

# UP主 口头禅 / 直播腔
UP_HINTS = ["三连", "关注", "直播间", "兄弟们", "家人们", "点个赞", "投币", "我觉得", "我个人"]
# 官方解说腔
OFFICIAL_HINTS = ["让我们", "欢迎回到", "本局比赛", "恭喜", "拿下这一局", "为我们带来"]


@dataclass
class AttributionResult:
    mapping: dict[str, str] = field(default_factory=dict)  # spk0 → up/official/other
    confidence: float = 1.0
    needs_review: bool = False
    detail: dict = field(default_factory=dict)


def _duration_share(segments: list[Segment]) -> dict[str, float]:
    total: dict[str, float] = {}
    for s in segments:
        total[s.speaker] = total.get(s.speaker, 0.0) + max(0, s.end_ms - s.start_ms)
    grand = sum(total.values()) or 1.0
    return {k: v / grand for k, v in total.items()}


def _rms_by_speaker(segments: list[Segment], wav_path: Path) -> dict[str, float]:
    """各 speaker 时间段的平均 RMS（16bit 单声道 wav）。"""
    import numpy as np

    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        for s in segments:
            start = min(int(s.start_ms / 1000 * rate), n_frames)
            length = min(int((s.end_ms - s.start_ms) / 1000 * rate), n_frames - start)
            if length <= 0:
                continue
            wf.setpos(start)
            raw = wf.readframes(length)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
            if samples.size == 0:
                continue
            rms = float(np.sqrt(np.mean(samples**2)))
            sums[s.speaker] = sums.get(s.speaker, 0.0) + rms * samples.size
            counts[s.speaker] = counts.get(s.speaker, 0) + samples.size
    return {k: sums[k] / counts[k] for k in sums if counts.get(k)}


def _keyword_score(segments: list[Segment]) -> dict[str, float]:
    """正分偏 UP，负分偏官方。"""
    scores: dict[str, float] = {}
    for s in segments:
        delta = 0.0
        for w in UP_HINTS:
            if w in s.text:
                delta += 1.0
        for w in OFFICIAL_HINTS:
            if w in s.text:
                delta -= 1.0
        if delta:
            scores[s.speaker] = scores.get(s.speaker, 0.0) + delta
    return scores


def attribute_speakers(
    segments: list[Segment],
    wav_path: Optional[Path] = None,
    hint: Optional[dict] = None,
) -> AttributionResult:
    if not segments:
        return AttributionResult(needs_review=True, confidence=0.0)

    speakers = sorted({s.speaker for s in segments})
    # 人工覆盖优先
    if hint and hint.get("strategy") == "manual" and hint.get("spk") in speakers:
        mapping = {spk: ("up" if spk == hint["spk"] else "other") for spk in speakers}
        return AttributionResult(mapping=mapping, confidence=1.0, detail={"method": "manual"})

    shares = _duration_share(segments)
    ranked = sorted(shares.items(), key=lambda kv: -kv[1])
    top_spk, top_share = ranked[0]
    detail: dict = {"duration_share": shares, "method": "duration"}
    confidence = 0.9
    up_spk = top_spk

    # 时长信号不显著（第一二名接近）→ 用响度在【时长前二】中定夺
    # 只比前二：防止某个时长占比极低但响（如片头音乐/采样噪声）的说话人被误判
    if len(ranked) > 1 and top_share - ranked[1][1] < 0.1:
        top2 = {ranked[0][0], ranked[1][0]}
        if wav_path and wav_path.exists():
            rms = _rms_by_speaker(segments, wav_path)
            detail["rms"] = rms
            detail["method"] = "duration+rms(top2)"
            candidates = {k: v for k, v in rms.items() if k in top2}
            if candidates:
                up_spk = max(candidates.items(), key=lambda kv: kv[1])[0]
                confidence = 0.75
        else:
            confidence = 0.6

    # 词面校验：若与判定冲突则降置信进人审
    kw = _keyword_score(segments)
    detail["keyword_score"] = kw
    if kw:
        kw_best = max(kw.items(), key=lambda kv: kv[1])
        if kw_best[1] >= 3 and kw_best[0] != up_spk:
            confidence = min(confidence, 0.5)
            detail["keyword_conflict"] = True

    mapping = {}
    for spk in speakers:
        if spk == up_spk:
            mapping[spk] = "up"
        elif kw.get(spk, 0) < -2:
            mapping[spk] = "official"
        else:
            mapping[spk] = "other"

    return AttributionResult(
        mapping=mapping,
        confidence=confidence,
        needs_review=confidence < 0.7,
        detail=detail,
    )
