"""
VideoProse 主工作流

使用 LangGraph 编排完整的视频转文章处理流程。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from .config import get_config
from .models import (
    AudioFile,
    Chunk,
    KnowledgeBase,
    MarkdownDocument,
    Metadata,
    ProcessedChunk,
    TranscriptSegment,
)
from .modules import (
    build_glossary,
    extract_audio,
    fetch_metadata,
    get_full_transcript,
    get_subtitle,
    merge_short_segments,
    refine_segment,
    semantic_split,
    speech_to_text,
    synthesize_article,
)


class WorkflowState(TypedDict):
    """工作流状态"""
    # 输入
    url: str
    
    # 中间状态
    metadata: Optional[Metadata]
    audio_file: Optional[AudioFile]
    segments: list[TranscriptSegment]
    full_text: str
    knowledge_base: Optional[KnowledgeBase]
    chunks: list[Chunk]
    processed_chunks: list[ProcessedChunk]
    
    # 输出
    document: Optional[MarkdownDocument]
    
    # 控制状态
    current_step: str
    error: Optional[str]
    
    # 消息历史（用于调试）
    messages: Annotated[list, add_messages]


def create_initial_state(url: str) -> WorkflowState:
    """创建初始状态"""
    return WorkflowState(
        url=url,
        metadata=None,
        audio_file=None,
        segments=[],
        full_text="",
        knowledge_base=None,
        chunks=[],
        processed_chunks=[],
        document=None,
        current_step="start",
        error=None,
        messages=[],
    )


# ============ 节点函数 ============

def fetch_video_info(state: WorkflowState) -> dict:
    """获取视频信息"""
    try:
        metadata = fetch_metadata(state["url"])
        return {
            "metadata": metadata,
            "current_step": "fetch_metadata",
            "messages": [f"✓ 获取视频信息: {metadata.title}"],
        }
    except Exception as e:
        return {
            "error": f"获取视频信息失败: {e}",
            "current_step": "error",
        }


def get_transcript(state: WorkflowState) -> dict:
    """获取转录文本"""
    try:
        # 首先尝试获取字幕
        segments = get_subtitle(state["url"])
        
        if segments:
            # 有字幕，直接使用
            segments = merge_short_segments(segments)
            full_text = get_full_transcript(segments)
            return {
                "segments": segments,
                "full_text": full_text,
                "current_step": "transcript_from_subtitle",
                "messages": [f"✓ 使用字幕获取转录 ({len(segments)} 个片段)"],
            }
        
        # 没有字幕，需要 ASR
        audio_file = extract_audio(state["url"])
        segments = speech_to_text(audio_file)
        segments = merge_short_segments(segments)
        full_text = get_full_transcript(segments)
        
        return {
            "audio_file": audio_file,
            "segments": segments,
            "full_text": full_text,
            "current_step": "transcript_from_asr",
            "messages": [f"✓ ASR 转录完成 ({len(segments)} 个片段)"],
        }
    except Exception as e:
        return {
            "error": f"获取转录失败: {e}",
            "current_step": "error",
        }


def build_knowledge(state: WorkflowState) -> dict:
    """构建知识库"""
    try:
        kb = build_glossary(state["full_text"])
        return {
            "knowledge_base": kb,
            "current_step": "build_glossary",
            "messages": [
                f"✓ 提取术语 {len(kb.entities)} 个",
                f"✓ 核心主题: {kb.core_theme}",
            ],
        }
    except Exception as e:
        return {
            "error": f"构建知识库失败: {e}",
            "current_step": "error",
        }


def chunk_text(state: WorkflowState) -> dict:
    """切片处理"""
    try:
        chunks = semantic_split(state["segments"])
        return {
            "chunks": chunks,
            "current_step": "chunk",
            "messages": [f"✓ 文本切分为 {len(chunks)} 个片段"],
        }
    except Exception as e:
        return {
            "error": f"切片失败: {e}",
            "current_step": "error",
        }


def refine_text(state: WorkflowState) -> dict:
    """精修文本"""
    try:
        processed_chunks = []
        context_summary = ""
        kb = state["knowledge_base"] or KnowledgeBase()
        total_duration = state["metadata"].duration if state["metadata"] else None
        
        for chunk in state["chunks"]:
            # 计算位置信息
            if total_duration and chunk.start_time:
                progress = chunk.start_time / total_duration
                if progress < 0.1:
                    position_info = "开头部分"
                elif progress < 0.3:
                    position_info = "前期部分"
                elif progress < 0.7:
                    position_info = "中间部分"
                elif progress < 0.9:
                    position_info = "后期部分"
                else:
                    position_info = "结尾部分"
            else:
                position_info = f"第 {chunk.chunk_id + 1} 段"
            
            processed = refine_segment(
                current_chunk=chunk,
                context_summary=context_summary,
                kb=kb,
                position_info=position_info,
            )
            
            processed_chunks.append(processed)
            context_summary = processed.summary
        
        return {
            "processed_chunks": processed_chunks,
            "current_step": "refine",
            "messages": [f"✓ 完成 {len(processed_chunks)} 个片段的精修"],
        }
    except Exception as e:
        return {
            "error": f"精修失败: {e}",
            "current_step": "error",
        }


def assemble_document(state: WorkflowState) -> dict:
    """组装文档"""
    try:
        document = synthesize_article(
            processed_chunks=state["processed_chunks"],
            metadata=state["metadata"],
            kb=state["knowledge_base"],
        )
        return {
            "document": document,
            "current_step": "complete",
            "messages": ["✓ 文档生成完成"],
        }
    except Exception as e:
        return {
            "error": f"组装文档失败: {e}",
            "current_step": "error",
        }


# ============ 条件路由 ============

def should_continue(state: WorkflowState) -> str:
    """判断是否继续"""
    if state.get("error"):
        return "error"
    return "continue"


# ============ 构建工作流图 ============

def build_workflow() -> StateGraph:
    """构建工作流图"""
    workflow = StateGraph(WorkflowState)
    
    # 添加节点
    workflow.add_node("fetch_info", fetch_video_info)
    workflow.add_node("get_transcript", get_transcript)
    workflow.add_node("build_knowledge", build_knowledge)
    workflow.add_node("chunk", chunk_text)
    workflow.add_node("refine", refine_text)
    workflow.add_node("assemble", assemble_document)
    
    # 设置入口
    workflow.set_entry_point("fetch_info")
    
    # 添加边（线性流程）
    workflow.add_conditional_edges(
        "fetch_info",
        should_continue,
        {"continue": "get_transcript", "error": END},
    )
    workflow.add_conditional_edges(
        "get_transcript",
        should_continue,
        {"continue": "build_knowledge", "error": END},
    )
    workflow.add_conditional_edges(
        "build_knowledge",
        should_continue,
        {"continue": "chunk", "error": END},
    )
    workflow.add_conditional_edges(
        "chunk",
        should_continue,
        {"continue": "refine", "error": END},
    )
    workflow.add_conditional_edges(
        "refine",
        should_continue,
        {"continue": "assemble", "error": END},
    )
    workflow.add_edge("assemble", END)
    
    return workflow


def create_app():
    """创建可执行的工作流应用"""
    workflow = build_workflow()
    return workflow.compile()


# ============ 便捷函数 ============

def process_video(
    url: str,
    output_path: Optional[str] = None,
    on_progress: Optional[callable] = None,
) -> MarkdownDocument:
    """
    处理视频的便捷函数
    
    Args:
        url: 视频 URL
        output_path: 输出文件路径（可选）
        on_progress: 进度回调函数
        
    Returns:
        MarkdownDocument: 生成的文档
    """
    app = create_app()
    initial_state = create_initial_state(url)
    
    # 运行工作流
    final_state = None
    for state in app.stream(initial_state):
        final_state = state
        
        # 获取当前节点的状态
        node_name = list(state.keys())[0]
        node_state = state[node_name]
        
        if on_progress and "messages" in node_state:
            for msg in node_state["messages"]:
                on_progress(msg)
    
    # 检查是否有错误
    if final_state:
        last_node = list(final_state.keys())[0]
        result = final_state[last_node]
        
        if result.get("error"):
            raise RuntimeError(result["error"])
        
        document = result.get("document")
        
        if document and output_path:
            # 保存文档
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(document.to_markdown(), encoding="utf-8")
        
        return document
    
    raise RuntimeError("工作流执行失败")
