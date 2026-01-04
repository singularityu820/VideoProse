"""
LLM 客户端封装

支持多种 LLM 提供商：OpenAI, Anthropic, DeepSeek
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from .config import get_config


class BaseLLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """发送聊天请求"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


class AnthropicClient(BaseLLMClient):
    """Anthropic 客户端"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        # Anthropic 需要将 system 消息单独处理
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)
        
        kwargs = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system_message:
            kwargs["system"] = system_message
        
        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class DeepSeekClient(BaseLLMClient):
    """DeepSeek 客户端（兼容 OpenAI API）"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
        )
        self.model = model
    
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


# 全局客户端实例
_llm_client: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """获取 LLM 客户端实例"""
    global _llm_client
    
    if _llm_client is None:
        config = get_config()
        llm_config = config.llm
        
        if llm_config.provider == "openai":
            _llm_client = OpenAIClient(
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
        elif llm_config.provider == "anthropic":
            _llm_client = AnthropicClient(
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
        elif llm_config.provider == "deepseek":
            _llm_client = DeepSeekClient(
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
        else:
            raise ValueError(f"不支持的 LLM 提供商: {llm_config.provider}")
    
    return _llm_client


def set_llm_client(client: BaseLLMClient) -> None:
    """设置 LLM 客户端实例"""
    global _llm_client
    _llm_client = client


def create_llm_client(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
) -> BaseLLMClient:
    """创建指定类型的 LLM 客户端"""
    if provider == "openai":
        return OpenAIClient(api_key=api_key, model=model or "gpt-4o")
    elif provider == "anthropic":
        return AnthropicClient(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
    elif provider == "deepseek":
        return DeepSeekClient(api_key=api_key, model=model or "deepseek-chat")
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
