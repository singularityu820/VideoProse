"""
语义切片模块 (Semantic Chunker)

将长文本切分为 AI 最适处理区间（1200-1500字）。
"""

from typing import Optional

from ..config import get_config
from ..models import Chunk, TranscriptSegment


def semantic_split(
    segments: list[TranscriptSegment],
    target_len: Optional[int] = None,
    max_len: Optional[int] = None,
    context_overlap_ratio: Optional[float] = None,
    min_silence_duration: float = 1.5,
) -> list[Chunk]:
    """
    语义感知切片
    
    将长文本切分为 AI 最适处理区间，遵循以下策略：
    1. 以目标字数为一个"加工单元"
    2. 非硬性切断：寻找最近的静默点或句号
    3. 保留上下文重叠，防止断层
    
    Args:
        segments: 原始转录片段列表
        target_len: 目标字数，默认使用配置
        max_len: 最大字数，默认使用配置
        context_overlap_ratio: 上下文重叠比例，默认使用配置
        min_silence_duration: 最小静默时长（秒）
        
    Returns:
        list[Chunk]: 切片列表
    """
    config = get_config()
    chunking_config = config.chunking
    
    target_len = target_len or chunking_config.target_length
    max_len = max_len or chunking_config.max_length
    context_overlap_ratio = context_overlap_ratio or chunking_config.context_overlap_ratio
    
    if not segments:
        return []
    
    chunks = []
    current_segments: list[TranscriptSegment] = []
    current_length = 0
    chunk_id = 0
    context_prefix = ""
    
    for i, segment in enumerate(segments):
        seg_length = len(segment.text)
        
        # 检查是否需要切分
        if current_length + seg_length > target_len:
            # 寻找最佳切分点
            split_point = _find_split_point(
                segments[max(0, i-5):i+1],  # 往回看 5 个片段
                current_segments,
                min_silence_duration,
            )
            
            if split_point is not None:
                # 在切分点处分割
                chunk_segments = current_segments[:split_point]
                remaining_segments = current_segments[split_point:]
            else:
                # 没有找到好的切分点，直接切
                chunk_segments = current_segments
                remaining_segments = []
            
            if chunk_segments:
                # 创建切片
                chunk = Chunk(
                    chunk_id=chunk_id,
                    segments=chunk_segments,
                    context_prefix=context_prefix,
                )
                chunks.append(chunk)
                chunk_id += 1
                
                # 计算上下文前缀（用于下一个切片）
                chunk_text = chunk.raw_text
                overlap_len = int(len(chunk_text) * context_overlap_ratio)
                context_prefix = chunk_text[-overlap_len:] if overlap_len > 0 else ""
            
            # 重置当前切片
            current_segments = remaining_segments + [segment]
            current_length = sum(len(s.text) for s in current_segments)
        else:
            current_segments.append(segment)
            current_length += seg_length
        
        # 强制切分：如果超过最大长度
        if current_length > max_len:
            chunk = Chunk(
                chunk_id=chunk_id,
                segments=current_segments,
                context_prefix=context_prefix,
            )
            chunks.append(chunk)
            chunk_id += 1
            
            chunk_text = chunk.raw_text
            overlap_len = int(len(chunk_text) * context_overlap_ratio)
            context_prefix = chunk_text[-overlap_len:] if overlap_len > 0 else ""
            
            current_segments = []
            current_length = 0
    
    # 处理剩余内容
    if current_segments:
        chunk = Chunk(
            chunk_id=chunk_id,
            segments=current_segments,
            context_prefix=context_prefix,
        )
        chunks.append(chunk)
    
    return chunks


def _find_split_point(
    recent_segments: list[TranscriptSegment],
    current_segments: list[TranscriptSegment],
    min_silence_duration: float,
) -> Optional[int]:
    """
    寻找最佳切分点
    
    优先级：
    1. 长停顿（>1.5s）
    2. 句末标点
    3. 逻辑转折词
    
    Returns:
        int: 切分点索引（在 current_segments 中），None 表示没有找到
    """
    if len(current_segments) < 2:
        return None
    
    best_point = None
    best_score = 0
    
    for i in range(len(current_segments) - 1, 0, -1):
        segment = current_segments[i - 1]
        next_segment = current_segments[i]
        
        score = 0
        
        # 检查静默时长
        gap = next_segment.start_time - segment.end_time
        if gap >= min_silence_duration:
            score += 10  # 高优先级
        elif gap >= min_silence_duration * 0.5:
            score += 5
        
        # 检查句末标点
        text = segment.text.strip()
        if text.endswith(("。", "！", "？", ".", "!", "?")):
            score += 8
        elif text.endswith(("，", "；", ",", ";")):
            score += 3
        
        # 检查逻辑转折词
        next_text = next_segment.text.strip().lower()
        transition_words = [
            "但是", "然而", "不过", "所以", "因此", "总之",
            "but", "however", "so", "therefore", "thus",
            "首先", "其次", "最后", "另外", "此外",
            "first", "second", "finally", "also", "moreover",
        ]
        for word in transition_words:
            if next_text.startswith(word):
                score += 6
                break
        
        if score > best_score:
            best_score = score
            best_point = i
    
    # 只有当分数足够高时才返回切分点
    return best_point if best_score >= 5 else None


def estimate_chunk_count(
    segments: list[TranscriptSegment],
    target_len: int = 1200,
) -> int:
    """
    估算切片数量
    
    Args:
        segments: 转录片段列表
        target_len: 目标字数
        
    Returns:
        int: 估算的切片数量
    """
    total_length = sum(len(s.text) for s in segments)
    return max(1, (total_length + target_len - 1) // target_len)


def get_chunk_info(chunks: list[Chunk]) -> dict:
    """
    获取切片统计信息
    
    Args:
        chunks: 切片列表
        
    Returns:
        dict: 统计信息
    """
    if not chunks:
        return {
            "count": 0,
            "total_chars": 0,
            "avg_chars": 0,
            "min_chars": 0,
            "max_chars": 0,
        }
    
    char_counts = [c.char_count for c in chunks]
    
    return {
        "count": len(chunks),
        "total_chars": sum(char_counts),
        "avg_chars": sum(char_counts) // len(chunks),
        "min_chars": min(char_counts),
        "max_chars": max(char_counts),
    }
