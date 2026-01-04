"""
VideoProse Web 界面

使用 Streamlit 实现交互式 Web 界面。
"""

import json
import time
from pathlib import Path

import streamlit as st

# 页面配置
st.set_page_config(
    page_title="VideoProse - 视频转长文",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .step-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .progress-text {
        color: #28a745;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "result" not in st.session_state:
        st.session_state.result = None
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = None
    if "progress_messages" not in st.session_state:
        st.session_state.progress_messages = []


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("⚙️ 设置")
        
        # LLM 选择
        st.subheader("模型配置")
        provider = st.selectbox(
            "LLM 提供商",
            ["anthropic", "openai", "deepseek"],
            index=0,
        )
        
        model_options = {
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "openai": ["gpt-4o", "gpt-4-turbo"],
            "deepseek": ["deepseek-chat", "deepseek-coder"],
        }
        
        model = st.selectbox(
            "模型",
            model_options.get(provider, []),
        )
        
        api_key = st.text_input(
            "API Key",
            type="password",
            help="输入对应提供商的 API Key",
        )
        
        st.divider()
        
        # 切片配置
        st.subheader("切片配置")
        target_length = st.slider(
            "目标字数",
            min_value=800,
            max_value=2000,
            value=1200,
            step=100,
        )
        
        context_overlap = st.slider(
            "上下文重叠比例",
            min_value=0.05,
            max_value=0.2,
            value=0.1,
            step=0.01,
        )
        
        st.divider()
        
        # 关于
        st.subheader("关于")
        st.markdown("""
        **VideoProse v1.0**
        
        将长视频转化为具备深度阅读感的结构化长文。
        
        支持 B站 和 YouTube 视频。
        """)
        
        return {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "target_length": target_length,
            "context_overlap": context_overlap,
        }


def render_main_content(settings: dict):
    """渲染主要内容"""
    st.markdown('<p class="main-header">📝 VideoProse</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">将长视频转化为深度长文</p>', unsafe_allow_html=True)
    
    # 输入区域
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url = st.text_input(
            "视频链接",
            placeholder="输入 B站 或 YouTube 视频链接...",
            help="支持 bilibili.com 和 youtube.com",
        )
    
    with col2:
        st.write("")  # 占位
        st.write("")  # 占位
        process_btn = st.button(
            "🚀 开始处理",
            type="primary",
            disabled=st.session_state.processing or not url,
            use_container_width=True,
        )
    
    # 处理流程
    if process_btn and url:
        process_video_ui(url, settings)
    
    # 显示结果
    if st.session_state.result:
        render_result(st.session_state.result)


def process_video_ui(url: str, settings: dict):
    """处理视频（UI 版本）"""
    st.session_state.processing = True
    st.session_state.progress_messages = []
    
    # 配置
    from videoprose.config import Config, LLMConfig, ChunkingConfig, set_config
    from videoprose.llm import create_llm_client, set_llm_client
    
    # 设置配置
    config = Config(
        llm=LLMConfig(
            provider=settings["provider"],
            model=settings["model"],
            api_key=settings["api_key"],
        ),
        chunking=ChunkingConfig(
            target_length=settings["target_length"],
            context_overlap_ratio=settings["context_overlap"],
        ),
    )
    set_config(config)
    
    # 设置 LLM 客户端
    if settings["api_key"]:
        client = create_llm_client(
            provider=settings["provider"],
            api_key=settings["api_key"],
            model=settings["model"],
        )
        set_llm_client(client)
    
    # 进度容器
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            ("获取视频信息", 0.1),
            ("提取字幕/转录", 0.3),
            ("构建知识库", 0.4),
            ("语义切片", 0.5),
            ("文本精修", 0.8),
            ("生成文档", 1.0),
        ]
        
        try:
            from videoprose.workflow import process_video
            
            def on_progress(msg: str):
                st.session_state.progress_messages.append(msg)
                # 查找当前步骤
                for step_name, progress in steps:
                    if step_name in msg or any(k in msg for k in ["获取", "提取", "构建", "切分", "精修", "生成"]):
                        progress_bar.progress(progress)
                        status_text.text(msg)
                        break
            
            # 执行处理
            document = process_video(
                url=url,
                on_progress=on_progress,
            )
            
            st.session_state.result = document
            st.session_state.processing = False
            
            progress_bar.progress(1.0)
            status_text.text("✅ 处理完成！")
            st.success("视频转文章完成！")
            
        except Exception as e:
            st.session_state.processing = False
            st.error(f"处理失败: {e}")
            return
    
    st.rerun()


def render_result(document):
    """渲染处理结果"""
    st.divider()
    st.header("📄 生成结果")
    
    # 选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["📖 正文预览", "📋 目录", "💡 金句", "⬇️ 下载"])
    
    with tab1:
        st.markdown(document.body)
    
    with tab2:
        st.subheader("核心要点")
        st.markdown(document.executive_summary)
        
        st.subheader("目录")
        for item in document.table_of_contents:
            st.markdown(f"- {item}")
    
    with tab3:
        st.subheader("金句摘录")
        for i, highlight in enumerate(document.highlights, 1):
            st.info(f"**{i}.** {highlight}")
    
    with tab4:
        # 生成完整 Markdown
        full_markdown = document.to_markdown()
        
        st.download_button(
            label="📥 下载 Markdown 文件",
            data=full_markdown,
            file_name=f"{document.title}.md",
            mime="text/markdown",
        )
        
        # 预览
        with st.expander("预览 Markdown 源码"):
            st.code(full_markdown, language="markdown")


def render_glossary_editor():
    """渲染术语表编辑器"""
    if st.session_state.knowledge_base:
        kb = st.session_state.knowledge_base
        
        st.subheader("📚 术语表")
        
        # 显示术语
        if kb.entities:
            for i, entity in enumerate(kb.entities):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.text_input(
                        "原词",
                        value=entity.term,
                        key=f"term_{i}",
                        label_visibility="collapsed",
                    )
                with col2:
                    st.text_input(
                        "翻译",
                        value=entity.translation,
                        key=f"trans_{i}",
                        label_visibility="collapsed",
                    )
                with col3:
                    st.selectbox(
                        "类型",
                        ["Person", "Company", "Technical", "General"],
                        index=["Person", "Company", "Technical", "General"].index(entity.entity_type),
                        key=f"type_{i}",
                        label_visibility="collapsed",
                    )
        
        # 语气特征
        st.subheader("🎭 语气特征")
        st.text_input("风格描述", value=kb.tone_profile.style, key="style")
        st.text_area("情绪关键词", value=", ".join(kb.tone_profile.emotion_keywords), key="emotions")


def main():
    """主函数"""
    init_session_state()
    settings = render_sidebar()
    render_main_content(settings)


if __name__ == "__main__":
    main()
