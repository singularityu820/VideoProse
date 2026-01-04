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
from .config import get_config
get_config()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 存储任务状态
tasks: dict = {}

# Whisper 模型是否已加载
_whisper_loaded = False


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
        # 配置
        from .config import Config, LLMConfig, ChunkingConfig, set_config, get_config
        from .llm import create_llm_client, set_llm_client
        
        current_config = get_config()
        env_provider = current_config.llm.provider
        env_model = current_config.llm.model
        env_api_key = current_config.llm.api_key

        # 解析 LLM 配置
        provider = request.provider or env_provider
        model = request.model or env_model
        api_key = request.apiKey
        if not api_key:
            env_key = os.getenv(f"{provider.upper()}_API_KEY")
            api_key = env_key or env_api_key

        # 如果指定的 provider 缺少 key，则自动回退到默认 provider（deepseek）
        if not api_key:
            fallback_key = os.getenv(f"{env_provider.upper()}_API_KEY") or env_api_key
            if fallback_key:
                provider = env_provider
                model = env_model
                api_key = fallback_key
                add_message(task_id, f"未找到 {request.provider or '指定'} 的 API Key，已回退到默认 {env_provider}")

        llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
        )
        config = Config(
            llm=llm_config,
            chunking=ChunkingConfig(
                target_length=request.targetLength,
                context_overlap_ratio=request.contextOverlap,
            ),
            # 保持当前的 Whisper 配置，避免被默认 large-v3 覆盖
            whisper=current_config.whisper,
        )
        set_config(config)
        
        if api_key:
            client = create_llm_client(
                provider=provider,
                api_key=api_key,
                model=model,
            )
            set_llm_client(client)
        else:
            raise HTTPException(status_code=400, detail="缺少对应提供商的 API Key")
        
        # Step 1: 获取视频信息
        update_task(task_id, "获取视频信息...", 10)
        from .modules import fetch_metadata, get_subtitle, extract_audio
        
        metadata = fetch_metadata(request.url)
        task["metadata"] = {
            "title": metadata.title,
            "author": metadata.author,
            "duration": metadata.duration,
        }
        add_message(task_id, f"✓ 视频: {metadata.title}")
        
        # Step 2: 获取转录
        update_task(task_id, "提取字幕...", 20)
        from .modules import speech_to_text, merge_short_segments, get_full_transcript
        
        segments = get_subtitle(request.url)
        if not segments:
            update_task(task_id, "ASR 转录中...", 25)
            audio = extract_audio(request.url)
            segments = speech_to_text(audio)
        
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
        
        # 转换为前端格式
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
        
        # 暂停等待用户确认
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
        )
        from .modules import semantic_split, refine_segment, synthesize_article
        
        # 重建数据结构
        segments = [
            TranscriptSegment(
                start_time=s["start"],
                end_time=s["end"],
                text=s["text"],
            )
            for s in task["segments"]
        ]
        
        glossary = task["glossary"]
        kb = KnowledgeBase(
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
        
        # Step 4: 语义切片
        update_task(task_id, "语义切片...", 50)
        chunks = semantic_split(segments)
        add_message(task_id, f"✓ 切分为 {len(chunks)} 个片段")
        
        # Step 5: 文本精修
        update_task(task_id, "文本精修...", 55)
        from .models import ProcessedChunk
        import concurrent.futures
        
        total_duration = task["metadata"]["duration"] if task.get("metadata") else None
        
        def process_single_chunk(i, chunk):
            # 计算位置信息
            if total_duration and chunk.start_time:
                ratio = chunk.start_time / total_duration
                if ratio < 0.1:
                    position = "开头部分"
                elif ratio < 0.3:
                    position = "前期部分"
                elif ratio < 0.7:
                    position = "中间部分"
                elif ratio < 0.9:
                    position = "后期部分"
                else:
                    position = "结尾部分"
            else:
                position = f"第 {i + 1} 段"
            
            # 并行处理时，上下文信息较弱，我们可以传入前一段的原始文本摘要（如果需要）
            # 这里简单处理，不传 context_summary
            return refine_segment(
                current_chunk=chunk,
                context_summary="", # 并行模式下暂不提供上文摘要
                kb=kb,
                position_info=position,
            )

        processed_chunks = [None] * len(chunks)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_index = {executor.submit(process_single_chunk, i, chunk): i for i, chunk in enumerate(chunks)}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_index):
                i = future_to_index[future]
                try:
                    processed = future.result()
                    processed_chunks[i] = processed
                    completed += 1
                    progress = 55 + int((completed / len(chunks)) * 25)
                    update_task(task_id, f"精修片段 {completed}/{len(chunks)}...", progress)
                except Exception as e:
                    add_message(task_id, f"片段 {i+1} 处理失败: {e}")
                    raise e
        
        add_message(task_id, f"✓ 完成 {len(processed_chunks)} 个片段精修")
        
        # Step 6: 生成文档
        update_task(task_id, "生成文档...", 90)
        from .models import Metadata
        
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
