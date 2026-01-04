"""
转录与对齐模块 (Transcription & Alignment)

将音频转化为带时间轴的文本。
"""

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
    
    from faster_whisper import WhisperModel
    
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
) -> list[TranscriptSegment]:
    """
    语音转文字
    
    调用 Faster-Whisper 模型进行 ASR 转录。
    
    Args:
        audio: 音频文件信息
        model: Whisper 模型名称，默认使用配置文件中的设置
        language: 语言代码，None 表示自动检测
        
    Returns:
        list[TranscriptSegment]: 带时间戳的转录片段列表
    """
    config = get_config()
    whisper_config = config.whisper
    
    # 使用缓存的模型
    whisper_model = get_whisper_model(model)
    
    # 转录
    segments_iter, _info = whisper_model.transcribe(
        audio.file_path,
        language=language or whisper_config.language,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,  # 启用 VAD 过滤静音
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 200,
        },
    )
    
    # 转换为 TranscriptSegment 列表
    segments = []
    for segment in segments_iter:
        segments.append(TranscriptSegment(
            start_time=segment.start,
            end_time=segment.end,
            text=segment.text.strip(),
        ))
    
    return segments


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
