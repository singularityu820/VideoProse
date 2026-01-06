"""
VideoProse FastAPI 后端

为 Next.js 前端提供 REST API。
"""

import os
import asyncio
import uuid
from typing import Optional
from contextlib import asynccontextmanager

# 尽早加载配置（确保 HF_HOME 等环境变量生效）
from .config import get_config, Config, LLMConfig, ChunkingConfig, WhisperConfig, QwenASRConfig
get_config()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 存储任务状态
tasks: dict = {}

# Whisper 模型是否已加载
_whisper_loaded = False


def _build_runtime_config(request: "ProcessRequest"):
    """组装 LLM 与 ASR 运行时配置"""
    current_config = get_config()
    env_provider = current_config.llm.provider
    env_model = current_config.llm.model
    env_api_key = current_config.llm.api_key

    provider = request.provider or env_provider
    model = request.model or env_model
    api_key = request.apiKey or os.getenv(f"{provider.upper()}_API_KEY") or env_api_key
    fallback_message = None

    if not api_key:
        fallback_key = os.getenv(f"{env_provider.upper()}_API_KEY") or env_api_key
        if fallback_key:
            provider = env_provider
            model = env_model
            api_key = fallback_key
            fallback_message = f"未找到 {request.provider or '指定'} 的 API Key，已回退到默认 {env_provider}"

    asr_provider = (request.asrProvider or current_config.asr_provider or "whisper").lower()

    whisper_config = WhisperConfig(
        model=request.asrModel if (asr_provider == "whisper" and request.asrModel) else current_config.whisper.model,
        device=current_config.whisper.device,
        compute_type=current_config.whisper.compute_type,
        language=current_config.whisper.language,
        fast_model=current_config.whisper.fast_model,
        fast_threshold_minutes=current_config.whisper.fast_threshold_minutes,
        fast_beam_size=current_config.whisper.fast_beam_size,
        fast_word_timestamps=current_config.whisper.fast_word_timestamps,
    )

    qwen_asr_config = QwenASRConfig(
        model=request.asrModel or current_config.qwen_asr.model,
        api_key=request.asrApiKey or current_config.qwen_asr.api_key,
        base_url=request.asrBaseUrl or current_config.qwen_asr.base_url,
    )

    config = Config(
        llm=LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
        ),
        asr_provider=asr_provider,
        whisper=whisper_config,
        qwen_asr=qwen_asr_config,
        chunking=ChunkingConfig(
            target_length=request.targetLength,
            context_overlap_ratio=request.contextOverlap,
        ),
    )

    return config, provider, model, api_key, asr_provider, fallback_message, current_config


def _get_transcript_segments(
    request: "ProcessRequest",
    config: Config,
    asr_provider: str,
    long_audio: bool,
    update_task_fn,
    task_id: str,
):
    """优先字幕，缺失时走 ASR；支持本地文件"""
    from .modules import get_subtitle, extract_audio, speech_to_text
    from .models import TranscriptSegment
    import os

    if request.sourceType == "subtitle" and request.subtitleText:
        lines = [l.strip() for l in request.subtitleText.splitlines() if l.strip()]
        segments: list[TranscriptSegment] = []
        for idx, line in enumerate(lines):
            start = float(idx) * 3.0
            end = start + 3.0
            segments.append(TranscriptSegment(start_time=start, end_time=end, text=line))
        return segments

    # subtitle from remote
    if request.sourceType != "local-audio":
        segments = get_subtitle(request.url)
        if segments:
            return segments

    update_task_fn(task_id, "ASR 转录中...", 25)
    # 支持本地文件路径（含 file://）
    local_path = request.url.replace("file://", "") if request.url.startswith("file://") else request.url
    if request.sourceType == "local-audio" and os.path.exists(local_path):
        audio = extract_audio(local_path)
    else:
        audio = extract_audio(request.url)

    return speech_to_text(
        audio,
        model=config.whisper.model if asr_provider == "whisper" else config.qwen_asr.model,
        language=config.whisper.language,
        provider=asr_provider,
        api_key=config.qwen_asr.api_key,
        base_url=config.qwen_asr.base_url,
        prefer_fast=long_audio,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _whisper_loaded
    # 启动时预加载 Whisper 模型
    print("正在预加载 Whisper 模型（首次需要下载，请耐心等待）...")
    try:
        from .modules.transcription import preload_whisper_model
        _whisper_loaded = preload_whisper_model()
        if _whisper_loaded:
            print("✓ Whisper 模型预加载完成")
        else:
            print("⚠ Whisper 模型预加载失败，将在首次使用时加载")
    except Exception as e:
        print(f"⚠ Whisper 模型预加载出错: {e}")
    
    yield
    tasks.clear()


app = FastAPI(
    title="VideoProse API",
    description="视频转长文 API 服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 请求/响应模型 ============

class ProcessRequest(BaseModel):
    url: str
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    apiKey: Optional[str] = None
    sourceType: str = "auto"  # auto | local-audio | local-video | subtitle
    subtitleText: Optional[str] = None
    asrProvider: str = "whisper"
    asrModel: Optional[str] = None
    asrApiKey: Optional[str] = None
    asrBaseUrl: Optional[str] = None
    targetLength: int = 1200
    contextOverlap: float = 0.1


class GlossaryEntity(BaseModel):
    term: str
    translation: str
    definition: str
    entityType: str


class ToneProfile(BaseModel):
    style: str
    emotionKeywords: list[str]
    audience: str


class GlossaryData(BaseModel):
    entities: list[GlossaryEntity]
    toneProfile: ToneProfile
    coreTheme: str


class ContinueRequest(BaseModel):
    glossary: GlossaryData


class TaskStatus(BaseModel):
    status: str
    currentStep: str
    progress: int
    messages: list[str]
    error: Optional[str] = None
    glossary: Optional[GlossaryData] = None
    result: Optional[dict] = None


# ============ API 端点 ============

@app.post("/api/process")
async def start_process(request: ProcessRequest, background_tasks: BackgroundTasks):
    """开始处理视频"""
    task_id = str(uuid.uuid4())
    
    # 初始化任务状态
    tasks[task_id] = {
        "status": "processing",
        "currentStep": "初始化...",
        "progress": 0,
        "messages": [],
        "error": None,
        "glossary": None,
        "result": None,
        "request": request.model_dump(),
    }
    
    # 后台执行处理
    background_tasks.add_task(process_video_task, task_id, request)
    
    return {"taskId": task_id}


@app.get("/api/status/{task_id}")
async def get_status(task_id: str) -> TaskStatus:
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return TaskStatus(
        status=task["status"],
        currentStep=task["currentStep"],
        progress=task["progress"],
        messages=task["messages"],
        error=task.get("error"),
        glossary=task.get("glossary"),
        result=task.get("result"),
    )


@app.post("/api/process/{task_id}/continue")
async def continue_process(
    task_id: str,
    request: ContinueRequest,
    background_tasks: BackgroundTasks,
):
    """确认术语表后继续处理"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    if task["status"] != "glossary-review":
        raise HTTPException(status_code=400, detail="任务状态不正确")
    
    # 更新术语表
    task["glossary"] = request.glossary.model_dump()
    task["status"] = "processing"
    task["currentStep"] = "继续处理..."
    
    # 继续后台处理
    background_tasks.add_task(continue_processing_task, task_id)
    
    return {"status": "ok"}


# ============ 后台任务 ============

def process_video_task(task_id: str, request: ProcessRequest):
    """处理视频的后台任务"""
    task = tasks[task_id]
    
    try:
        from .config import set_config
        from .llm import create_llm_client, set_llm_client
        from .modules import fetch_metadata, get_subtitle, extract_audio

        config, provider, model, api_key, asr_provider, fallback_message, current_config = _build_runtime_config(request)
        set_config(config)
        if fallback_message:
            add_message(task_id, fallback_message)
        if not api_key:
            raise HTTPException(status_code=400, detail="缺少对应提供商的 API Key")

        client = create_llm_client(provider=provider, api_key=api_key, model=model)
        set_llm_client(client)

        # Step 1: 获取视频信息
        update_task(task_id, "获取视频信息...", 10)
        keyframe_eligible = True
        if request.sourceType == "subtitle" and request.subtitleText:
            from .models import Metadata, SourcePlatform
            metadata = Metadata(title="本地字幕", author="local", duration=0, platform=SourcePlatform.LOCAL)
            keyframe_eligible = False
        elif request.sourceType in ["local-audio", "local-video"]:
            metadata = fetch_metadata(request.url, allow_local=True)
            keyframe_eligible = request.sourceType == "local-video"
        else:
            metadata = fetch_metadata(request.url)

        task["metadata"] = {
            "title": metadata.title,
            "author": metadata.author,
            "duration": metadata.duration,
        }
        task["keyframeEligible"] = keyframe_eligible
        add_message(task_id, f"✓ 视频: {metadata.title}")
        long_audio = bool(metadata.duration and metadata.duration >= current_config.whisper.fast_threshold_minutes * 60)

        # Step 2: 获取转录
        update_task(task_id, "提取字幕...", 20)
        from .modules import merge_short_segments, get_full_transcript

        segments = _get_transcript_segments(
            request,
            config,
            asr_provider,
            long_audio,
            update_task,
            task_id,
        )

        segments = merge_short_segments(segments)
        full_text = get_full_transcript(segments)
        task["segments"] = [{"start": s.start_time, "end": s.end_time, "text": s.text} for s in segments]
        task["fullText"] = full_text
        add_message(task_id, f"✓ 转录完成 ({len(segments)} 个片段)")

        # Step 3: 构建知识库
        update_task(task_id, "构建知识库...", 40)
        from .modules import build_glossary
        kb = build_glossary(full_text)
        task["knowledgeBase"] = kb

        glossary_data = {
            "entities": [
                {
                    "term": e.term,
                    "translation": e.translation,
                    "definition": e.definition,
                    "entityType": e.entity_type,
                }
                for e in kb.entities
            ],
            "toneProfile": {
                "style": kb.tone_profile.style,
                "emotionKeywords": kb.tone_profile.emotion_keywords,
                "audience": kb.tone_profile.audience,
            },
            "coreTheme": kb.core_theme,
        }
        task["glossary"] = glossary_data
        add_message(task_id, f"✓ 提取术语 {len(kb.entities)} 个")

        task["status"] = "glossary-review"
        task["currentStep"] = "等待确认术语表..."
        task["progress"] = 45

    except Exception as e:  # noqa: BLE001
        import traceback
        task["status"] = "error"
        task["error"] = str(e)
        task["currentStep"] = "处理出错"
        tb = traceback.format_exc()
        task["messages"].append(f"异常: {e}")
        task["messages"].append(tb)
        print(tb)


def continue_processing_task(task_id: str):
    """继续处理的后台任务"""
    task = tasks[task_id]
    try:
        from .models import (
            TranscriptSegment,
            KnowledgeBase,
            Entity,
            ToneProfile,
            Metadata,
        )
        from .modules import semantic_split, refine_segment, synthesize_article

        def _restore_segments_and_kb(task_state):
            segments_restored = [
                TranscriptSegment(
                    start_time=s["start"],
                    end_time=s["end"],
                    text=s["text"],
                )
                for s in task_state["segments"]
            ]

            glossary = task_state["glossary"]
            kb_restored = KnowledgeBase(
                entities=[
                    Entity(
                        term=e["term"],
                        translation=e["translation"],
                        definition=e["definition"],
                        entity_type=e["entityType"],
                    )
                    for e in glossary["entities"]
                ],
                tone_profile=ToneProfile(
                    style=glossary["toneProfile"]["style"],
                    emotion_keywords=glossary["toneProfile"]["emotionKeywords"],
                    audience=glossary["toneProfile"]["audience"],
                ),
                core_theme=glossary["coreTheme"],
            )
            return segments_restored, kb_restored

        segments, kb = _restore_segments_and_kb(task)
        # Step 4: 语义切片
        update_task(task_id, "语义切片...", 55)
        chunks = semantic_split(segments)
        add_message(task_id, f"✓ 切分为 {len(chunks)} 个片段")

        # Step 5: 片段精修（顺序执行保证上下文稳定）
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            position = f"第 {i + 1} 段"
            update_task(task_id, f"精修 {position}...", 60 + int((i / max(len(chunks), 1)) * 25))
            refined = refine_segment(
                current_chunk=chunk,
                context_summary="",
                kb=kb,
                position_info=position,
            )
            processed_chunks.append(refined)

        add_message(task_id, f"✓ 完成 {len(processed_chunks)} 个片段精修")

        # Step 6: 生成文档
        update_task(task_id, "生成文档...", 90)
        metadata = Metadata(
            title=task["metadata"]["title"],
            author=task["metadata"]["author"],
            duration=task["metadata"]["duration"],
        )

        document = synthesize_article(
            processed_chunks=processed_chunks,
            metadata=metadata,
            kb=kb,
        )

        # 转换为前端格式
        result = {
            "title": document.title,
            "author": document.author,
            "executiveSummary": document.executive_summary,
            "tableOfContents": document.table_of_contents,
            "body": document.body,
            "highlights": document.highlights,
        }

        task["result"] = result
        task["status"] = "completed"
        task["currentStep"] = "处理完成"
        task["progress"] = 100
        add_message(task_id, "✓ 文档生成完成")

    except Exception as e:  # noqa: BLE001
        import traceback
        task["status"] = "error"
        task["error"] = str(e)
        task["currentStep"] = "处理出错"
        tb = traceback.format_exc()
        task["messages"].append(f"异常: {e}")
        task["messages"].append(tb)
        print(tb)


def update_task(task_id: str, step: str, progress: int):
    """更新任务状态"""
    if task_id in tasks:
        tasks[task_id]["currentStep"] = step
        tasks[task_id]["progress"] = progress


def add_message(task_id: str, message: str):
    """添加消息"""
    if task_id in tasks:
        tasks[task_id]["messages"].append(message)


# ============ 健康检查 ============

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
