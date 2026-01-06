"""
VideoProse 配置管理
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv

# 在模块加载时就加载 .env 文件
# 从项目根目录查找 .env
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)

# 必须在 huggingface_hub 导入前设置这些环境变量
_hf_home = os.getenv("HF_HOME")
if _hf_home:
    os.environ["HF_HOME"] = _hf_home
    os.environ["HUGGINGFACE_HUB_CACHE"] = _hf_home
    os.environ["TRANSFORMERS_CACHE"] = _hf_home
    # 创建目录
    Path(_hf_home).mkdir(parents=True, exist_ok=True)

# 禁用符号链接警告
if os.getenv("HF_HUB_DISABLE_SYMLINKS_WARNING"):
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: Literal["openai", "anthropic", "deepseek"] = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class WhisperConfig:
    """Whisper 配置"""
    model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    language: Optional[str] = None  # None 表示自动检测
    # 长音频加速参数
    fast_model: Optional[str] = None  # 可选：medium / small 等，None 表示仍用主模型
    fast_threshold_minutes: int = 20  # 超过该分钟数启用加速策略
    fast_beam_size: int = 1  # 加速模式下的 beam size
    fast_word_timestamps: bool = False  # 长音频默认关闭逐词时间戳以提速


@dataclass
class QwenASRConfig:
    """Qwen ASR 配置"""
    model: str = "qwen3-asr-flash"
    api_key: Optional[str] = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    chunk_on_long: bool = True
    max_chunk_seconds: int = 280  # 每段最长 4 分 40 秒，兼容 5 分钟限制


@dataclass
class ChunkingConfig:
    """切片配置"""
    target_length: int = 1200  # 目标字数
    max_length: int = 1500  # 最大字数
    context_overlap_ratio: float = 0.1  # 上下文重叠比例
    min_silence_duration: float = 1.5  # 最小静默时长（秒）


@dataclass
class Config:
    """全局配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    asr_provider: Literal["whisper", "qwen"] = "whisper"
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    qwen_asr: QwenASRConfig = field(default_factory=QwenASRConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    output_dir: Path = field(default_factory=lambda: Path("./output"))

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "Config":
        """从环境变量加载配置"""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        llm_config = LLMConfig(
            provider=os.getenv("DEFAULT_LLM_PROVIDER", "anthropic"),
            model=os.getenv("DEFAULT_MODEL", "claude-3-5-sonnet-20241022"),
            api_key=os.getenv(f"{os.getenv('DEFAULT_LLM_PROVIDER', 'ANTHROPIC').upper()}_API_KEY"),
        )

        asr_provider = os.getenv("ASR_PROVIDER", "whisper")

        whisper_config = WhisperConfig(
            model=os.getenv("WHISPER_MODEL", "large-v3"),
            device=os.getenv("WHISPER_DEVICE", "cuda"),
            compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "float16"),
            language=os.getenv("WHISPER_LANGUAGE") or None,
            fast_model=os.getenv("WHISPER_FAST_MODEL") or None,
            fast_threshold_minutes=int(os.getenv("WHISPER_FAST_THRESHOLD_MINUTES", "20")),
            fast_beam_size=int(os.getenv("WHISPER_FAST_BEAM_SIZE", "1")),
            fast_word_timestamps=os.getenv("WHISPER_FAST_WORD_TIMESTAMPS", "false").lower() == "true",
        )

        qwen_asr_config = QwenASRConfig(
            model=os.getenv("QWEN_ASR_MODEL", "qwen3-asr-flash"),
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            chunk_on_long=os.getenv("QWEN_ASR_CHUNK_ON_LONG", "true").lower() == "true",
            max_chunk_seconds=int(os.getenv("QWEN_ASR_MAX_CHUNK_SECONDS", "280")),
        )

        chunking_config = ChunkingConfig(
            target_length=int(os.getenv("CHUNK_TARGET_LENGTH", "1200")),
            max_length=int(os.getenv("CHUNK_MAX_LENGTH", "1500")),
            context_overlap_ratio=float(os.getenv("CONTEXT_OVERLAP_RATIO", "0.1")),
        )

        output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))

        return cls(
            llm=llm_config,
            asr_provider=asr_provider if asr_provider in ["whisper", "qwen"] else "whisper",
            whisper=whisper_config,
            qwen_asr=qwen_asr_config,
            chunking=chunking_config,
            output_dir=output_dir,
        )


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """设置全局配置"""
    global _config
    _config = config
