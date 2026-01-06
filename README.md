# VideoProse v1.0

将 Bilibili/YouTube 长视频（15min - 4h+）转化为具备深度阅读感的、保持原作者语感的结构化长文。

## ✨ 特性

- 🎬 支持 B站 和 YouTube 视频
- 🎙️ 智能字幕提取或 ASR 转录（Faster-Whisper）
- 📚 自动提取术语表，保证翻译一致性
- ✂️ 语义感知切片，解决长文本"降智"问题
- 🎭 保留原作者语感和情绪
- 📄 生成结构化 Markdown 文档

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/videoprose.git
cd videoprose

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 yt-dlp（用于视频下载）
pip install yt-dlp

# 安装 ffmpeg（用于音频处理）
# Windows: choco install ffmpeg
# Mac: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

### 配置

复制环境变量模板并填入 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 选择 LLM 提供商
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-5-sonnet-20241022

# 填入 API Key
ANTHROPIC_API_KEY=sk-ant-your-key
# 或 OPENAI_API_KEY=sk-your-key
# 或 DEEPSEEK_API_KEY=your-key
```

### 使用

#### 命令行

```bash
# 处理视频
python -m videoprose.cli process "https://www.bilibili.com/video/BVxxx"

# 指定输出路径
python -m videoprose.cli process "https://www.youtube.com/watch?v=xxx" -o output.md

# 使用不同的 LLM
python -m videoprose.cli process "URL" --provider openai --model gpt-4o
```

#### Web 界面

```bash
# 1. 启动后端 API 服务
cd src
uvicorn videoprose.api:app --reload --port 8000

# 2. 启动前端开发服务器（新终端）
cd web
npm install
npm run dev
```

然后访问 [http://localhost:3000](http://localhost:3000)

#### Python API

```python
from videoprose.workflow import process_video

# 处理视频
document = process_video(
    url="https://www.bilibili.com/video/BVxxx",
    output_path="output.md",
)

print(document.title)
print(document.executive_summary)
```

## 📖 处理流程

```
URL 输入
    ↓
┌─────────────────┐
│  媒体处理模块    │ → 提取元数据、字幕或音频
└─────────────────┘
    ↓
┌─────────────────┐
│  转录模块        │ → ASR 转录（若无字幕）
└─────────────────┘
    ↓
┌─────────────────┐
│  知识建模模块    │ → 提取术语、分析语气
└─────────────────┘
    ↓
┌─────────────────┐
│  语义切片模块    │ → 智能分段（1200-1500字）
└─────────────────┘
    ↓
┌─────────────────┐
│  文本提纯引擎    │ → 去口语化、保留情绪
└─────────────────┘
    ↓
┌─────────────────┐
│  聚合排版模块    │ → 生成目录、摘要、金句
└─────────────────┘
    ↓
Markdown 文档输出
```

## 🔧 配置选项

### LLM 配置

| 提供商 | 推荐模型 | 特点 |
|--------|----------|------|
| Anthropic | claude-3-5-sonnet | 文笔最细腻，推荐 |
| OpenAI | gpt-4o | 通用性强 |
| DeepSeek | deepseek-chat | 高性价比 |

### 切片配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| CHUNK_TARGET_LENGTH | 1200 | 目标切片字数 |
| CHUNK_MAX_LENGTH | 1500 | 最大切片字数 |
| CONTEXT_OVERLAP_RATIO | 0.1 | 上下文重叠比例 |

## 📁 项目结构

```
videoprose/
├── src/videoprose/
│   ├── __init__.py
│   ├── models.py          # 数据模型
│   ├── config.py          # 配置管理
│   ├── llm.py             # LLM 客户端
│   ├── workflow.py        # 主工作流
│   ├── api.py             # FastAPI 后端
│   ├── cli.py             # 命令行
│   └── modules/
│       ├── media_processor.py      # 媒体处理
│       ├── transcription.py        # 转录
│       ├── knowledge_architect.py  # 知识建模
│       ├── semantic_chunker.py     # 语义切片
│       ├── refinement_engine.py    # 文本提纯
│       └── assembler.py            # 聚合排版
├── web/                   # Next.js 前端
│   ├── src/
│   │   ├── app/           # 页面
│   │   ├── components/    # 组件
│   │   └── lib/           # 工具函数
│   ├── package.json
│   └── tailwind.config.ts
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## 🗺️ 路线图

- [x] Phase 1 (MVP): URL → Whisper → LLM 一次性转录
- [x] Phase 2 (Chunking): 分段处理逻辑
- [x] Phase 3 (Glossary): 前置知识提取
- [x] Phase 4 (UI): Web 界面
- [ ] Phase 5 (Multi-modal): 关键帧截取插入

## 📄 许可证

MIT License
