# VideoProse

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

将长视频（B站 / YouTube / 本地音视频 / 粘贴字幕）转写成结构化长文，保留原作者的语感与节奏。

## 📖 项目简介

VideoProse 让长视频快速变成好读的长文：智能获取字幕或执行 ASR，提取术语表，语义切片防止“降智”，再用 LLM 精修、排版，生成含摘要、目录、正文与高亮的完整文档。

## ✨ 核心特性

- 🔗 输入多源：B站 / YouTube 链接、本地视频音频、或直接粘贴字幕
- 🎙️ 高效转写：Whisper 快速模式 + Qwen ASR 分片，长音频仍可流畅处理
- 🧠 语义切片：根据语义/静默点分段，防止长内容失去上下文
- 📚 术语表：先提取领域术语，保障后续翻译/引用一致
- 📝 长文生成：摘要、目录、正文、高亮一键生成，保持原作者语感
- 💻 前后端分离：FastAPI 后端 + Next.js/Tailwind 前端

## 📋 环境要求

- Python 3.10+
- Node.js 18+
- ffmpeg（音视频抽取）
- 可选：yt-dlp（抓取站外视频）

## 🚀 快速开始

### 1) 克隆与安装

```bash
git clone https://github.com/singularityu820/VideoProse.git
cd video2text

# Python 依赖
python -m venv .venv
./.venv/Scripts/activate    # Windows
# 或 source .venv/bin/activate
pip install -r requirements.txt

# 前端依赖
cd web
npm install
cd ..
```

### 2) 配置环境变量

复制 `.env.example` 为 `.env`，填入对应 Key（至少一个 LLM Key，若用 Qwen ASR 需 DASHScope 兼容 Key）：

```env
# LLM
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your-key

# Whisper / Qwen ASR
WHISPER_DEVICE=cpu
QWEN_ASR_API_KEY=your-qwen-key
QWEN_ASR_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 3) 启动服务

在仓库根目录：

```bash
# 后端（需在项目根目录，让 videoprose 成为可导入包）
cd src
uvicorn videoprose.api:app --host 0.0.0.0 --port 8000

# 前端（新终端）
cd web
npm run dev
```

前端默认访问 [http://localhost:3000](http://localhost:3000)，后端 [http://localhost:8000](http://localhost:8000)，Swagger 文档 [http://localhost:8000/docs](http://localhost:8000/docs)。

## 💡 使用说明

1. 打开前端，选择来源：链接 / 本地路径 / 粘贴字幕。
2. 可在设置中切换 LLM、ASR（Whisper/Qwen）、目标字数、上下文重叠等参数。
3. 提交后等待：
   - 自动取字幕；若无字幕则抽取音频并 ASR。
   - 术语表生成 → 语义分片 → 精修 → 汇总成长文。
4. 在结果页查看摘要、目录、正文与高亮，可复制导出。

本地路径示例（需后端可访问）：

```text
D:/media/video.mp4
file:///D:/audio/podcast.wav
```

字幕粘贴：直接在表单中粘贴纯文本字幕，将跳过音频处理。

## ⚙️ 关键配置

- Whisper 快速模式：超过配置阈值（默认 15 分钟）自动切换 fast 模型与 beam 设置。
- Qwen ASR 分片：长音频自动按秒切段并并行请求。
- 切片参数：
  - `CHUNK_TARGET_LENGTH` 目标字数（默认 1200）
  - `CHUNK_MAX_LENGTH` 最大字数（默认 1500）
  - `CONTEXT_OVERLAP_RATIO` 上下文重叠比例（默认 0.1）

## 🧭 处理流程

```text
输入 (链接 / 本地 / 字幕)
    ↓
[媒体处理] 元数据 + 字幕/音频提取 (ffmpeg / yt-dlp)
    ↓
[ASR] Whisper 快速模式 或 Qwen ASR 分片
    ↓
[术语表] 抽取实体与语气
    ↓
[语义切片] 按静默/语义分段，保留重叠
    ↓
[精修合成] LLM 去口语化、生成摘要/目录/正文/高亮
    ↓
输出 Markdown/结构化文档
```

## 📁 目录结构

```text
video2text/
├─ src/videoprose/        # 后端 & 处理流程
│  ├─ api.py              # FastAPI 入口
│  ├─ config.py           # 配置/默认参数
│  ├─ modules/            # 媒体处理、转录、切片、精修
│  └─ ...
├─ web/                   # 前端 (Next.js + Tailwind)
│  └─ src/app/            # 页面与组件
├─ requirements.txt
├─ pyproject.toml
└─ README.md
```

## 🧰 技术栈

**后端**：FastAPI · Uvicorn · ffmpeg · yt-dlp · Whisper · 通义千问 ASR (兼容 OpenAI API)

**前端**：Next.js · React · Tailwind CSS · Framer Motion · shadcn/ui


## 📄 许可证

MIT License
