"""
知识建模模块 (Knowledge Architect)

在处理全文前，建立"上帝视角"字典，包含术语表和语气特征。
这是项目的核心创新点。
"""

import json
from typing import Optional

from ..config import get_config
from ..models import Entity, KnowledgeBase, ToneProfile
from ..llm import get_llm_client


GLOSSARY_EXTRACTION_PROMPT = """你是一个专业的内容分析助手。请分析以下视频转录文本，提取关键信息。

## 任务

1. **术语提取**：识别文本中的专有名词，包括：
     - 人名（中文/英文）
     - 公司/品牌名
     - 技术术语
     - 特定概念或隐喻

2. **语气分析**：判断演讲者的表达风格，包括：
     - 整体风格（如：专业、激进、幽默、严谨、热情等）
     - 情绪关键词
     - 目标受众

3. **核心主题**：用一句话概括这段内容的核心主旨

## 输出格式

请严格按照以下 JSON 格式输出：

```json
{{
    "entities": [
        {{
            "term": "原始术语",
            "translation": "标准中文翻译（若原本就是中文则保持原样）",
            "definition": "简短定义或说明",
            "entity_type": "Person/Company/Technical/General"
        }}
    ],
    "tone_profile": {{
        "style": "风格描述",
        "emotion_keywords": ["关键词1", "关键词2"],
        "audience": "目标受众"
    }},
    "core_theme": "核心主旨"
}}
```

## 待分析文本

{text}

## 注意事项

- 术语翻译要准确统一，符合行业惯例
- 保留原文中有特色的表达方式
- 情绪关键词要反映演讲者的真实态度
- 仅输出 JSON，不要有其他内容
"""


def build_glossary(
    full_text: str,
    sample_ratio: float = 0.1,
    max_sample_length: int = 5000,
) -> KnowledgeBase:
    """
    构建前置知识库
    
    抽取全文前 10% 和关键词密度最高的部分投喂给 LLM，
    提取专有名词、人名、特定隐喻、演讲者的语言风格。
    
    Args:
        full_text: 完整的转录文本
        sample_ratio: 采样比例
        max_sample_length: 最大采样长度
        
    Returns:
        KnowledgeBase: 知识库对象
    """
    # 获取采样文本
    sample_text = _get_sample_text(full_text, sample_ratio, max_sample_length)
    
    # 调用 LLM 进行分析
    client = get_llm_client()
    prompt = GLOSSARY_EXTRACTION_PROMPT.format(text=sample_text)
    
    response = client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # 低温度以获得更稳定的结果
    )
    
    # 解析响应
    return _parse_glossary_response(response)


def _get_sample_text(
    full_text: str,
    sample_ratio: float,
    max_length: int,
) -> str:
    """
    获取用于分析的采样文本
    
    策略：
    1. 取开头 10% 的内容（通常包含介绍和关键概念）
    2. 取中间部分（核心内容）
    3. 取结尾部分（总结）
    """
    text_length = len(full_text)
    target_length = min(int(text_length * sample_ratio), max_length)
    
    if text_length <= max_length:
        return full_text
    
    # 分配比例：开头 40%，中间 30%，结尾 30%
    head_length = int(target_length * 0.4)
    middle_length = int(target_length * 0.3)
    tail_length = target_length - head_length - middle_length
    
    head = full_text[:head_length]
    
    middle_start = (text_length - middle_length) // 2
    middle = full_text[middle_start:middle_start + middle_length]
    
    tail = full_text[-tail_length:]
    
    return f"{head}\n\n[...中间省略...]\n\n{middle}\n\n[...中间省略...]\n\n{tail}"


def _parse_glossary_response(response: str) -> KnowledgeBase:
    """解析 LLM 返回的 JSON 响应"""
    try:
        # 提取 JSON 部分
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        
        data = json.loads(json_str.strip())
        
        # 构建 Entity 列表
        entities = []
        for e in data.get("entities", []):
            entities.append(Entity(
                term=e.get("term", ""),
                translation=e.get("translation", ""),
                definition=e.get("definition", ""),
                entity_type=e.get("entity_type", "General"),
            ))
        
        # 构建 ToneProfile
        tone_data = data.get("tone_profile", {})
        tone_profile = ToneProfile(
            style=tone_data.get("style", "neutral"),
            emotion_keywords=tone_data.get("emotion_keywords", []),
            audience=tone_data.get("audience", "general"),
        )
        
        return KnowledgeBase(
            entities=entities,
            tone_profile=tone_profile,
            core_theme=data.get("core_theme", ""),
        )
        
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        # 解析失败时返回空知识库
        print(f"警告：知识库解析失败 - {e}")
        return KnowledgeBase()


def update_glossary(
    kb: KnowledgeBase,
    new_text: str,
) -> KnowledgeBase:
    """
    增量更新知识库
    
    在处理过程中发现新术语时调用。
    
    Args:
        kb: 现有知识库
        new_text: 包含新术语的文本
        
    Returns:
        KnowledgeBase: 更新后的知识库
    """
    # 获取已有术语列表
    existing_terms = {e.term.lower() for e in kb.entities}
    
    # 分析新文本
    new_kb = build_glossary(new_text, sample_ratio=1.0)
    
    # 合并新术语
    for entity in new_kb.entities:
        if entity.term.lower() not in existing_terms:
            kb.entities.append(entity)
            existing_terms.add(entity.term.lower())
    
    return kb


def export_glossary(kb: KnowledgeBase, output_path: str) -> None:
    """
    导出术语表为 JSON 文件
    
    Args:
        kb: 知识库对象
        output_path: 输出路径
    """
    data = {
        "entities": [
            {
                "term": e.term,
                "translation": e.translation,
                "definition": e.definition,
                "entity_type": e.entity_type,
            }
            for e in kb.entities
        ],
        "tone_profile": {
            "style": kb.tone_profile.style,
            "emotion_keywords": kb.tone_profile.emotion_keywords,
            "audience": kb.tone_profile.audience,
        },
        "core_theme": kb.core_theme,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def import_glossary(input_path: str) -> KnowledgeBase:
    """
    从 JSON 文件导入术语表
    
    Args:
        input_path: 输入路径
        
    Returns:
        KnowledgeBase: 知识库对象
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    entities = [
        Entity(
            term=e["term"],
            translation=e["translation"],
            definition=e.get("definition", ""),
            entity_type=e.get("entity_type", "General"),
        )
        for e in data.get("entities", [])
    ]
    
    tone_data = data.get("tone_profile", {})
    tone_profile = ToneProfile(
        style=tone_data.get("style", "neutral"),
        emotion_keywords=tone_data.get("emotion_keywords", []),
        audience=tone_data.get("audience", "general"),
    )
    
    return KnowledgeBase(
        entities=entities,
        tone_profile=tone_profile,
        core_theme=data.get("core_theme", ""),
    )
