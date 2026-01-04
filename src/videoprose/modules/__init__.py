"""
VideoProse 模块包
"""

from .media_processor import (
    detect_platform,
    extract_audio,
    fetch_metadata,
    get_subtitle,
)
from .transcription import (
    detect_silences,
    get_full_transcript,
    merge_short_segments,
    speech_to_text,
)
from .knowledge_architect import build_glossary
from .semantic_chunker import semantic_split
from .refinement_engine import refine_segment
from .assembler import synthesize_article

__all__ = [
    # Media Processor
    "detect_platform",
    "fetch_metadata",
    "extract_audio",
    "get_subtitle",
    # Transcription
    "speech_to_text",
    "merge_short_segments",
    "detect_silences",
    "get_full_transcript",
    # Knowledge Architect
    "build_glossary",
    # Semantic Chunker
    "semantic_split",
    # Refinement Engine
    "refine_segment",
    # Assembler
    "synthesize_article",
]
