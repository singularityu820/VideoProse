"""
文本提纯引擎 (Refinement Engine)

去口语化、翻译、保留情绪。
这是项目的核心 Prompt 逻辑。
"""

from typing import Optional

from ..llm import get_llm_client
from ..models import Chunk, KnowledgeBase, ProcessedChunk


REFINEMENT_SYSTEM_PROMPT = """你是一位专业的文字编辑，擅长将口语化的演讲内容转化为流畅、有深度的书面文章。

## 你的任务

将口语化的视频转录文本改写为具有深度阅读感的书面文章，同时保持原作者的语感和情绪。

## 核心原则

### 1. 清理层
- 移除填充词：呃、嗯、那个、就是、然后、对吧、你知道吗
- 删除重复表达和口语冗余
- 但保留有意义的语气词（如强调、惊叹）

### 2. 转换层
- 将破碎的短句重组为逻辑连贯的长短句结合
- 添加必要的连接词和过渡句
- 确保段落结构清晰

### 3. 情绪层（关键！）
- 识别并保留原文中的修辞手法（比喻、反问、夸张）
- 保持作者的弦外之音：
  - 如果作者在质疑，请保留质疑的力度，而非单纯陈述事实
  - 如果作者在讽刺，请保留讽刺的锋芒
  - 如果作者在热情推荐，请保留那份热忱
- 不要让文章变得"干硬"、"没有灵魂"

## 输出要求

- 使用 Markdown 格式
- 适当使用**加粗**标注重点
- 长段落请分段，便于阅读
- 不要添加原文没有的观点或信息
"""


REFINEMENT_USER_PROMPT = """## 术语表

{glossary}

## 上下文

{context}

## 演讲者风格

{style}

## 待处理文本

{text}

## 处理要求

1. 遵循术语表中的翻译标准
2. 本段内容在视频的位置：{position}
3. 改写后请在文末用一句话总结本段核心内容（用于下一段的上下文衔接）

## 输出格式

先输出改写后的正文内容，然后换行输出：
【本段摘要】一句话总结
"""


def refine_segment(
    current_chunk: Chunk,
    context_summary: str,
    kb: KnowledgeBase,
    position_info: Optional[str] = None,
) -> ProcessedChunk:
    """
    精修文本片段
    
    去口语化、翻译、保留情绪。
    
    Args:
        current_chunk: 当前待处理切片
        context_summary: 上一段落的核心大意
        kb: 知识库（术语表）
        position_info: 本段在视频中的位置描述
        
    Returns:
        ProcessedChunk: 处理后的切片
    """
    client = get_llm_client()
    
    # 构建提示词
    glossary = kb.to_glossary_prompt() if kb.entities else "（无特定术语表）"
    
    context = context_summary if context_summary else "（这是文章的开头部分）"
    
    style = f"""
- 整体风格：{kb.tone_profile.style}
- 情绪关键词：{', '.join(kb.tone_profile.emotion_keywords) if kb.tone_profile.emotion_keywords else '无特定关键词'}
- 目标受众：{kb.tone_profile.audience}
"""
    
    position = position_info or f"第 {current_chunk.chunk_id + 1} 段"
    
    user_prompt = REFINEMENT_USER_PROMPT.format(
        glossary=glossary,
        context=context,
        style=style,
        text=current_chunk.full_text,
        position=position,
    )
    
    # 调用 LLM
    response = client.chat(
        messages=[
            {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    
    # 解析响应
    refined_content, summary = _parse_refinement_response(response)
    
    return ProcessedChunk(
        chunk_id=current_chunk.chunk_id,
        raw_content=current_chunk.raw_text,
        refined_content=refined_content,
        summary=summary,
        start_time=current_chunk.start_time,
        end_time=current_chunk.end_time,
    )


def _parse_refinement_response(response: str) -> tuple[str, str]:
    """
    解析精修响应
    
    Returns:
        tuple[str, str]: (精修内容, 本段摘要)
    """
    summary = ""
    content = response
    
    # 尝试提取摘要
    if "【本段摘要】" in response:
        parts = response.split("【本段摘要】")
        content = parts[0].strip()
        summary = parts[1].strip() if len(parts) > 1 else ""
    elif "[本段摘要]" in response:
        parts = response.split("[本段摘要]")
        content = parts[0].strip()
        summary = parts[1].strip() if len(parts) > 1 else ""
    
    return content, summary


def batch_refine_segments(
    chunks: list[Chunk],
    kb: KnowledgeBase,
    total_duration: Optional[float] = None,
    on_progress: Optional[callable] = None,
) -> list[ProcessedChunk]:
    """
    批量处理切片
    
    串行处理以确保上下文连贯性。
    
    Args:
        chunks: 切片列表
        kb: 知识库
        total_duration: 视频总时长（秒），用于计算位置信息
        on_progress: 进度回调函数 (current, total) -> None
        
    Returns:
        list[ProcessedChunk]: 处理后的切片列表
    """
    processed_chunks = []
    context_summary = ""
    
    for i, chunk in enumerate(chunks):
        # 计算位置信息
        if total_duration and chunk.start_time:
            progress = chunk.start_time / total_duration
            if progress < 0.1:
                position_info = "开头部分（引入主题）"
            elif progress < 0.3:
                position_info = "前期部分（展开论述）"
            elif progress < 0.7:
                position_info = "中间部分（核心内容）"
            elif progress < 0.9:
                position_info = "后期部分（深入讨论）"
            else:
                position_info = "结尾部分（总结收尾）"
        else:
            position_info = f"第 {i + 1}/{len(chunks)} 段"
        
        # 处理当前切片
        processed = refine_segment(
            current_chunk=chunk,
            context_summary=context_summary,
            kb=kb,
            position_info=position_info,
        )
        
        processed_chunks.append(processed)
        context_summary = processed.summary
        
        # 进度回调
        if on_progress:
            on_progress(i + 1, len(chunks))
    
    return processed_chunks
