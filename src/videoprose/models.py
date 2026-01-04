"""
VideoProse 核心数据模型

定义全链路使用的数据结构，确保模块间一致性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SourcePlatform(Enum):
    """视频来源平台"""
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    LOCAL = "local"


@dataclass
class Metadata:
    """视频元数据"""
    title: str
    author: str
    duration: float  # 秒
    thumbnail_url: Optional[str] = None
    original_language: str = "zh"
    platform: SourcePlatform = SourcePlatform.LOCAL
    url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class AudioFile:
    """音频文件信息"""
    file_path: str
    sample_rate: int = 16000
    channels: int = 1
    duration: float = 0.0


@dataclass
class TranscriptSegment:
    """
    原始转录片段
    
    Attributes:
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        text: 原始口语文本
    """
    start_time: float
    end_time: float
    text: str

    @property
    def duration(self) -> float:
        """片段时长"""
        return self.end_time - self.start_time


@dataclass
class Entity:
    """术语实体"""
    term: str  # 原始术语
    translation: str  # 标准翻译
    definition: str = ""  # 定义说明
    entity_type: str = "General"  # Person, Company, Technical, General


@dataclass
class ToneProfile:
    """语气特征描述"""
    style: str  # 风格描述，如 "Professional yet passionate"
    emotion_keywords: list[str] = field(default_factory=list)  # 情绪关键词
    audience: str = "general"  # 目标受众


@dataclass
class KnowledgeBase:
    """
    前置知识库
    
    在处理全文前建立的"上帝视角"字典，包含术语表和语气特征。
    """
    entities: list[Entity] = field(default_factory=list)
    tone_profile: ToneProfile = field(default_factory=lambda: ToneProfile(style="neutral"))
    core_theme: str = ""  # 视频核心主旨预判

    def get_entity(self, term: str) -> Optional[Entity]:
        """根据术语名称获取实体"""
        for entity in self.entities:
            if entity.term.lower() == term.lower():
                return entity
        return None

    def to_glossary_prompt(self) -> str:
        """生成用于 Prompt 的术语表文本"""
        if not self.entities:
            return ""
        
        lines = ["## 术语对照表\n"]
        for e in self.entities:
            line = f"- {e.term} → {e.translation}"
            if e.definition:
                line += f" ({e.definition})"
            lines.append(line)
        
        lines.append(f"\n## 语气风格\n{self.tone_profile.style}")
        return "\n".join(lines)


@dataclass
class Chunk:
    """
    语义切片（待处理）
    
    Attributes:
        chunk_id: 切片序号
        segments: 包含的原始转录片段
        context_prefix: 前一段末尾的上下文（用于逻辑过渡）
    """
    chunk_id: int
    segments: list[TranscriptSegment]
    context_prefix: str = ""

    @property
    def raw_text(self) -> str:
        """合并所有片段的原始文本"""
        return " ".join(seg.text for seg in self.segments)

    @property
    def full_text(self) -> str:
        """包含上下文前缀的完整文本"""
        if self.context_prefix:
            return f"{self.context_prefix} {self.raw_text}"
        return self.raw_text

    @property
    def start_time(self) -> float:
        """切片开始时间"""
        return self.segments[0].start_time if self.segments else 0.0

    @property
    def end_time(self) -> float:
        """切片结束时间"""
        return self.segments[-1].end_time if self.segments else 0.0

    @property
    def char_count(self) -> int:
        """字符数"""
        return len(self.raw_text)


@dataclass
class ProcessedChunk:
    """
    处理后的切片
    
    Attributes:
        chunk_id: 切片序号
        raw_content: 原始内容
        refined_content: 精修后的内容
        summary: 本段小结，用于下一段的上下文引用
    """
    chunk_id: int
    raw_content: str
    refined_content: str
    summary: str = ""
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class MarkdownDocument:
    """最终输出的 Markdown 文档"""
    title: str
    author: str
    executive_summary: str  # 核心观点摘要
    table_of_contents: list[str]  # 目录
    body: str  # 正文
    highlights: list[str] = field(default_factory=list)  # 金句库
    
    def to_markdown(self) -> str:
        """生成完整的 Markdown 文本"""
        lines = [
            f"# {self.title}",
            f"\n**作者**: {self.author}\n",
            "---\n",
            "## 核心要点\n",
            self.executive_summary,
            "\n---\n",
            "## 目录\n",
        ]
        
        for item in self.table_of_contents:
            lines.append(f"- {item}")
        
        lines.append("\n---\n")
        lines.append(self.body)
        
        if self.highlights:
            lines.append("\n---\n")
            lines.append("## 金句摘录\n")
            for h in self.highlights:
                lines.append(f"> {h}\n")
        
        return "\n".join(lines)


@dataclass
class ProcessingState:
    """处理状态（用于断点续传）"""
    video_url: str
    current_chunk_id: int = 0
    total_chunks: int = 0
    processed_chunks: list[ProcessedChunk] = field(default_factory=list)
    knowledge_base: Optional[KnowledgeBase] = None
    status: str = "pending"  # pending, processing, paused, completed, error
    error_message: Optional[str] = None
