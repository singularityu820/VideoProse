#!/usr/bin/env python
"""
Whisper 模型下载脚本

单独运行此脚本预下载模型，避免在服务启动时等待。
"""

import os
import sys
from pathlib import Path

# 加载 .env 配置
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# 设置 HuggingFace 缓存目录
hf_home = os.getenv("HF_HOME", "D:/hf_cache")
os.environ["HF_HOME"] = hf_home
os.environ["HUGGINGFACE_HUB_CACHE"] = hf_home
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# 创建缓存目录
Path(hf_home).mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Whisper 模型下载工具")
print("=" * 60)
print(f"缓存目录: {hf_home}")
print()

# 模型信息
MODELS = {
    "tiny": {"size": "39 MB", "params": "39M"},
    "base": {"size": "74 MB", "params": "74M"},
    "small": {"size": "244 MB", "params": "244M"},
    "medium": {"size": "769 MB", "params": "769M"},
    "large-v3": {"size": "3.09 GB", "params": "1550M"},
}

def download_model(model_name: str, device: str = "cuda", compute_type: str = "float16"):
    """下载并加载模型"""
    from faster_whisper import WhisperModel
    
    info = MODELS.get(model_name, {})
    size = info.get("size", "未知")
    
    print(f"模型: {model_name}")
    print(f"大小: {size}")
    print(f"设备: {device}")
    print(f"精度: {compute_type}")
    print()
    print("开始下载（如果模型已缓存则直接加载）...")
    print("-" * 60)
    
    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
        print("-" * 60)
        print()
        print("✓ 模型下载/加载成功！")
        print(f"✓ 模型已缓存到: {hf_home}")
        return model
    except Exception as e:
        print()
        print(f"✗ 错误: {e}")
        return None


def main():
    # 获取模型名称
    model_name = os.getenv("WHISPER_MODEL", "tiny")
    device = os.getenv("WHISPER_DEVICE", "cuda")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    if len(sys.argv) > 2:
        device = sys.argv[2]
    
    print("可用模型:")
    for name, info in MODELS.items():
        marker = " <-- 当前选择" if name == model_name else ""
        print(f"  - {name}: {info['size']}{marker}")
    print()
    
    # 下载模型
    model = download_model(model_name, device, compute_type)
    
    if model:
        print()
        print("现在可以启动服务了：")
        print("  .venv\\Scripts\\python -m uvicorn src.videoprose.api:app --port 8000")
    
    return 0 if model else 1


if __name__ == "__main__":
    sys.exit(main())
