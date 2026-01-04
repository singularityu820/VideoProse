"""
聚合与排版模块 (Assembler)

缝合片段，生成结构化文档。
"""

from typing import Optional

from ..llm import get_llm_client
from ..models import KnowledgeBase, MarkdownDocument, Metadata, ProcessedChunk


SYNTHESIS_PROMPT = """你是一位专业的内容编辑，负责将多个文章片段整合成一篇完整、流畅的深度长文。

## 任务

1. **审阅所有片段摘要**，生成文章的结构化目录（H2 级别标题）
2. **提取核心观点**，形成 3-5 个 Key Takeaways
3. **识别金句**，提取最有价值的 3-5 句话

## 输入信息

标题：{title}
作者：{author}
核心主题：{theme}

片段摘要：
{summaries}

## 输出格式

请严格按照以下 JSON 格式输出：

```json
{{
  "table_of_contents": ["章节1标题", "章节2标题", ...],
  "executive_summary": "3-5 句话的核心观点摘要，使用 Markdown 格式",
  "highlights": ["金句1", "金句2", ...]
}}
```

## 注意事项

- 目录标题要精炼，反映每部分的核心内容
- 摘要要突出最重要的洞见，不要简单罗列
- 金句要有洞察力，能引发读者思考
"""


def synthesize_article(
    processed_chunks: list[ProcessedChunk],
    metadata: Optional[Metadata] = None,
    kb: Optional[KnowledgeBase] = None,
) -> MarkdownDocument:
    """
    聚合片段生成结构化文档
    
    Args:
        processed_chunks: 处理后的切片列表
        metadata: 视频元数据
        kb: 知识库
        
    Returns:
        MarkdownDocument: 最终的 Markdown 文档
    """
    if not processed_chunks:
        raise ValueError("没有可处理的内容片段")
    
    # 准备元数据
    title = metadata.title if metadata else "视频转录长文"
    author = metadata.author if metadata else "未知"
    theme = kb.core_theme if kb else "未知主题"
    
    # 生成摘要列表
    summaries = "\n".join(
        f"【第{i+1}段】{chunk.summary or '（无摘要）'}"
        for i, chunk in enumerate(processed_chunks)
    )
    
    # 调用 LLM 生成元信息
    client = get_llm_client()
    prompt = SYNTHESIS_PROMPT.format(
        title=title,
        author=author,
        theme=theme,
        summaries=summaries,
    )
    
    response = client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    
    # 解析响应
    import json
    try:
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        
        meta_info = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        meta_info = {
            "table_of_contents": [f"第{i+1}部分" for i in range(len(processed_chunks))],
            "executive_summary": "文章摘要生成失败，请手动补充。",
            "highlights": [],
        }
    
    # 组装正文
    body = _assemble_body(processed_chunks, meta_info.get("table_of_contents", []))
    
    return MarkdownDocument(
        title=title,
        author=author,
        executive_summary=meta_info.get("executive_summary", ""),
        table_of_contents=meta_info.get("table_of_contents", []),
        body=body,
        highlights=meta_info.get("highlights", []),
    )


def _assemble_body(
    chunks: list[ProcessedChunk],
    toc: list[str],
) -> str:
    """
    组装文章正文
    
    根据目录将各片段组合成完整的文章。
    """
    sections = []
    chunks_per_section = max(1, len(chunks) // max(1, len(toc)))
    
    for i, heading in enumerate(toc):
        section_chunks = chunks[i * chunks_per_section:(i + 1) * chunks_per_section]
        
        if not section_chunks:
            continue
        
        # 添加章节标题
        section_content = f"## {heading}\n\n"
        
        # 添加章节内容
        for chunk in section_chunks:
            content = chunk.refined_content.strip()
            # 确保段落之间有适当间隔
            if not content.endswith("\n"):
                content += "\n"
            section_content += content + "\n"
        
        sections.append(section_content)
    
    # 处理剩余的 chunks（如果有）
    remaining_start = len(toc) * chunks_per_section
    if remaining_start < len(chunks):
        remaining_chunks = chunks[remaining_start:]
        section_content = "## 补充内容\n\n"
        for chunk in remaining_chunks:
            section_content += chunk.refined_content.strip() + "\n\n"
        sections.append(section_content)
    
    return "\n".join(sections)


def smooth_transitions(
    chunks: list[ProcessedChunk],
) -> list[ProcessedChunk]:
    """
    平滑段落间的过渡
    
    检查并优化段落之间的衔接。
    """
    if len(chunks) < 2:
        return chunks
    
    client = get_llm_client()
    
    for i in range(1, len(chunks)):
        prev_chunk = chunks[i - 1]
        curr_chunk = chunks[i]
        
        # 检查是否需要过渡词
        prev_text = prev_chunk.refined_content[-200:]
        curr_text = curr_chunk.refined_content[:200]
        
        # 简单检查是否已有过渡词
        transition_words = [
            "此外", "另外", "然而", "但是", "因此", "所以",
            "同时", "接下来", "与此同时", "不过", "总之",
            "Moreover", "However", "Therefore", "Meanwhile",
        ]
        
        has_transition = any(
            curr_chunk.refined_content.strip().startswith(word)
            for word in transition_words
        )
        
        if not has_transition:
            # 可以在这里调用 LLM 添加过渡，但为了效率暂时跳过
            pass
    
    return chunks


def generate_toc_from_content(
    chunks: list[ProcessedChunk],
    num_sections: int = 5,
) -> list[str]:
    """
    从内容自动生成目录
    
    Args:
        chunks: 处理后的切片列表
        num_sections: 期望的章节数
        
    Returns:
        list[str]: 目录标题列表
    """
    if not chunks:
        return []
    
    # 收集所有摘要
    summaries = [
        f"段落{i+1}: {chunk.summary}"
        for i, chunk in enumerate(chunks)
        if chunk.summary
    ]
    
    if not summaries:
        # 如果没有摘要，返回默认目录
        return [f"第{i+1}部分" for i in range(min(num_sections, len(chunks)))]
    
    client = get_llm_client()
    
    prompt = f"""根据以下段落摘要，生成 {num_sections} 个章节标题。
标题应该简洁有力，能概括各部分的核心内容。

{chr(10).join(summaries)}

请直接输出 {num_sections} 个标题，每行一个，不要编号。"""
    
    response = client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500,
    )
    
    # 解析响应
    titles = [
        line.strip().lstrip("0123456789.-、) ")
        for line in response.strip().split("\n")
        if line.strip()
    ]
    
    return titles[:num_sections] if titles else [f"第{i+1}部分" for i in range(num_sections)]
