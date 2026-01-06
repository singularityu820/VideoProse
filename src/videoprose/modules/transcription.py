"""Transcription & alignment utilities."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..config import get_config
from ..models import AudioFile, TranscriptSegment

# 全局模型缓存
_whisper_model = None
_whisper_model_name = None


def get_whisper_model(model_name: Optional[str] = None):
    """获取或加载 Whisper 模型（带缓存）"""
    global _whisper_model, _whisper_model_name
    
    from faster_whisper import WhisperModel  # type: ignore
    
    config = get_config()
    whisper_config = config.whisper
    target_model = model_name or whisper_config.model
    
    # 如果模型已加载且是同一个，直接返回
    if _whisper_model is not None and _whisper_model_name == target_model:
        return _whisper_model
    
    # 按顺序尝试不同 compute_type，避免 float16 在不支持的设备上失败
    compute_candidates = [whisper_config.compute_type, "int8", "float32"]
    seen = set()
    ordered_candidates = []
    for c in compute_candidates:
        if c and c not in seen:
            ordered_candidates.append(c)
            seen.add(c)
    
    last_error = None
    for compute_type in ordered_candidates:
        try:
            print(f"正在加载 Whisper 模型: {target_model} (device={whisper_config.device}, compute_type={compute_type})...")
            _whisper_model = WhisperModel(
                target_model,
                device=whisper_config.device,
                compute_type=compute_type,
            )
            _whisper_model_name = target_model
            print(f"Whisper 模型加载完成: {target_model} (compute_type={compute_type})")
            return _whisper_model
        except Exception as e:  # noqa: BLE001
            last_error = e
            print(f"⚠ Whisper 模型加载失败，compute_type={compute_type}: {e}")
            continue
    
    raise RuntimeError(f"Whisper 模型加载失败（尝试 {ordered_candidates}）：{last_error}")


def preload_whisper_model():
    """预加载 Whisper 模型（在服务启动时调用）"""
    try:
        get_whisper_model()
        return True
    except Exception as e:
        print(f"预加载 Whisper 模型失败: {e}")
        return False


def speech_to_text(
    audio: AudioFile,
    model: Optional[str] = None,
    language: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    prefer_fast: bool = False,
) -> list[TranscriptSegment]:
    """语音转文字，支持 Whisper 与 Qwen ASR，长音频可自动加速"""
    config = get_config()
    asr_provider = (provider or config.asr_provider or "whisper").lower()

    if asr_provider == "qwen":
        return _transcribe_with_qwen(
            audio,
            model=model or config.qwen_asr.model,
            api_key=api_key or config.qwen_asr.api_key,
            base_url=base_url or config.qwen_asr.base_url,
            language=language,
            chunk_on_long=config.qwen_asr.chunk_on_long,
            max_chunk_seconds=config.qwen_asr.max_chunk_seconds,
        )

    whisper_config = config.whisper
    fast_enabled = prefer_fast or (
        audio.duration and audio.duration / 60.0 >= whisper_config.fast_threshold_minutes
    )
    whisper_model_name = (
        whisper_config.fast_model if (fast_enabled and whisper_config.fast_model) else (model or whisper_config.model)
    )
    whisper_model = get_whisper_model(whisper_model_name)

    beam_size = whisper_config.fast_beam_size if fast_enabled else 5
    word_timestamps = whisper_config.fast_word_timestamps if fast_enabled else True

    segments_iter, _info = whisper_model.transcribe(
        audio.file_path,
        language=language or whisper_config.language,
        beam_size=beam_size,
        word_timestamps=word_timestamps,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 200,
        },
    )

    segments = []
    for segment in segments_iter:
        segments.append(TranscriptSegment(
            start_time=segment.start,
            end_time=segment.end,
            text=segment.text.strip(),
        ))

    return segments


def _transcribe_with_qwen(
    audio: AudioFile,
    model: str,
    api_key: Optional[str],
    base_url: Optional[str] = None,
    language: Optional[str] = None,
    chunk_on_long: bool = True,
    max_chunk_seconds: int = 280,
) -> list[TranscriptSegment]:
    """使用 Qwen ASR；长音频可分段串行转写"""
    if not api_key:
        raise RuntimeError("使用 Qwen ASR 需要配置 DASHSCOPE_API_KEY 或在请求中提供 asrApiKey")

    if chunk_on_long and audio.duration and audio.duration > max_chunk_seconds:
        return _transcribe_qwen_chunked(
            audio,
            model=model,
            api_key=api_key,
            base_url=base_url,
            language=language,
            max_chunk_seconds=max_chunk_seconds,
        )

    return _transcribe_qwen_single(
        audio_path=Path(audio.file_path),
        duration=audio.duration,
        model=model,
        api_key=api_key,
        base_url=base_url,
        language=language,
    )


def _transcribe_qwen_single(
    audio_path: Path,
    duration: float,
    model: str,
    api_key: str,
    base_url: Optional[str],
    language: Optional[str],
) -> list[TranscriptSegment]:
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model=model,
            file=f,
            language=language,
            response_format="verbose_json",
        )

    verbose_segments = _extract_qwen_segments(response)
    if verbose_segments:
        return verbose_segments

    final_text = getattr(response, "text", None) or (response.get("text") if isinstance(response, dict) else None)
    if final_text:
        return [
            TranscriptSegment(
                start_time=0.0,
                end_time=duration or 0.0,
                text=str(final_text).strip(),
            )
        ]

    raise RuntimeError("Qwen ASR 未返回任何转录结果")


def _extract_qwen_segments(response: object) -> list[TranscriptSegment]:
    """提取 Qwen ASR 段落结果"""
    raw_segments = getattr(response, "segments", None)
    if raw_segments is None and hasattr(response, "json"):
        raw_segments = response.json().get("segments")

    segments: list[TranscriptSegment] = []
    if not raw_segments:
        return segments

    for seg in raw_segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        segments.append(TranscriptSegment(
            start_time=start,
            end_time=end,
            text=text,
        ))

    return segments


def _transcribe_qwen_chunked(
    audio: AudioFile,
    model: str,
    api_key: str,
    base_url: Optional[str],
    language: Optional[str],
    max_chunk_seconds: int,
) -> list[TranscriptSegment]:
    """将长音频分段后串行调用 Qwen ASR"""
    temp_dir = tempfile.mkdtemp()
    try:
        chunk_paths = _split_audio_to_chunks(Path(audio.file_path), Path(temp_dir), max_chunk_seconds)
        offsets = _probe_chunk_durations(chunk_paths)
        segments: list[TranscriptSegment] = []

        for idx, chunk_path in enumerate(chunk_paths):
            chunk_duration = offsets[idx]
            chunk_segments = _transcribe_qwen_single(
                audio_path=chunk_path,
                duration=chunk_duration,
                model=model,
                api_key=api_key,
                base_url=base_url,
                language=language,
            )

            start_offset = sum(offsets[:idx])
            for seg in chunk_segments:
                segments.append(
                    TranscriptSegment(
                        start_time=seg.start_time + start_offset,
                        end_time=seg.end_time + start_offset,
                        text=seg.text,
                    )
                )

        return segments
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _split_audio_to_chunks(source: Path, out_dir: Path, max_chunk_seconds: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "chunk_%03d.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-f",
        "segment",
        "-segment_time",
        str(max_chunk_seconds),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(pattern),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频分段失败: {result.stderr.decode('utf-8', errors='replace')}")

    return sorted(out_dir.glob("chunk_*.wav"))


def _probe_chunk_durations(paths: list[Path]) -> list[float]:
    durations: list[float] = []
    for p in paths:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(p),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            durations.append(0.0)
            continue
        try:
            durations.append(float(result.stdout.decode().strip()))
        except ValueError:
            durations.append(0.0)
    return durations


def merge_short_segments(
    segments: list[TranscriptSegment],
    min_duration: float = 1.0,
    max_gap: float = 0.5,
) -> list[TranscriptSegment]:
    """
    合并过短的片段
    
    将时长过短或间隔过小的连续片段合并，提高后续处理效率。
    
    Args:
        segments: 原始转录片段列表
        min_duration: 最小片段时长（秒）
        max_gap: 允许合并的最大间隔（秒）
        
    Returns:
        list[TranscriptSegment]: 合并后的片段列表
    """
    if not segments:
        return []
    
    merged = []
    current = segments[0]
    
    for next_seg in segments[1:]:
        gap = next_seg.start_time - current.end_time
        
        # 如果间隔小于阈值，或当前片段太短，则合并
        if gap <= max_gap or current.duration < min_duration:
            current = TranscriptSegment(
                start_time=current.start_time,
                end_time=next_seg.end_time,
                text=f"{current.text} {next_seg.text}",
            )
        else:
            merged.append(current)
            current = next_seg
    
    merged.append(current)
    return merged


def detect_silences(
    segments: list[TranscriptSegment],
    min_silence: float = 1.5,
) -> list[float]:
    """
    检测静默点
    
    找出转录中的长停顿位置，用于语义切分。
    
    Args:
        segments: 转录片段列表
        min_silence: 最小静默时长（秒）
        
    Returns:
        list[float]: 静默点的时间戳列表（取停顿中点）
    """
    silences = []
    
    for i in range(len(segments) - 1):
        gap = segments[i + 1].start_time - segments[i].end_time
        if gap >= min_silence:
            # 取停顿的中点作为切分点
            silence_point = segments[i].end_time + gap / 2
            silences.append(silence_point)
    
    return silences


def get_full_transcript(segments: list[TranscriptSegment]) -> str:
    """
    获取完整的转录文本
    
    Args:
        segments: 转录片段列表
        
    Returns:
        str: 合并后的完整文本
    """
    return " ".join(seg.text for seg in segments)
