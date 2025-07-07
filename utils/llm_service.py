"""
LLM 服务模块 - 支持多个 LLM 提供商的抽象接口
目前支持：Gemini 2.0 Flash
"""

import os
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLM 提供商抽象基类"""
    
    @abstractmethod
    def extract_keywords(self, question: str) -> Dict[str, Any]:
        """  
        从用户问题中提取关键词
        
        Args:
            question: 用户提问
            
        Returns:
            包含关键词的字典，格式：
            {
                "keywords": ["关键词1", "关键词2", ...],
                "question_type": "漫画内容" | "访谈信息" | "综合查询",
                "confidence": 0.8
            }
        """
        pass


class GeminiProvider(LLMProvider):
    """Gemini LLM 提供商实现"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化 Gemini 客户端"""
        try:
            from google import genai
            # API key 从环境变量 GEMINI_API_KEY 获取
            self.client = genai.Client()
        except ImportError:
            raise ImportError("请安装 google-genai 库：pip install google-genai")
        except Exception as e:
            raise Exception(f"Gemini 客户端初始化失败：{e}")
    
    def extract_keywords(self, question: str) -> Dict[str, Any]:
        """使用 Gemini 2.0 Flash 提取关键词"""
        if not self.client:
            raise Exception("Gemini 客户端未初始化")
        
        prompt = """你是一个专门分析名侦探柯南相关问题的助手。请分析用户的问题，提取关键词句并判断问题类型。

用户问题："{}"

请以 JSON 格式返回结果，包含以下字段：
1. keywords: 关键词列表（日文和中文都要考虑，优先提取可能在漫画原文和采访作者青山刚昌时会出现的词汇, 
如果词汇过于常见比如: "柯南", "灰原哀" 等，则返回更加有意义的短句比如: "工藤新一的真实身份" “灰原哀喜欢的品牌”）
2. question_type: 问题类型，选择一个：
   - "漫画内容": 询问漫画剧情、角色对话、具体场景等
   - "访谈信息": 询问作者访谈、幕后制作、角色设定等  
   - "综合查询": 需要综合多种资料来回答
3. confidence: 置信度（0-1之间的数值）

示例格式：
{{
  "keywords": ["柯南的真实身份", "工藤新一"],
  "question_type": "漫画内容", 
  "confidence": 0.9
}}

只返回 JSON，不要其他解释!!!""".format(question)

        result_text = ""        
        try:
            print("🔄 正在调用 Gemini API...")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # 解析 JSON 响应
            result_text = response.text
            if result_text is None:
                result_text = ""
            result_text = result_text.strip()
            
            print(f"📥 API 原始响应: {result_text[:200]}...")
            
            # 移除可能的 markdown 代码块标记
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
            
            # 验证结果格式
            if not all(key in result for key in ["keywords", "question_type", "confidence"]):
                raise ValueError("返回格式不完整")
            
            print("✅ API 调用成功")
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败：{e}")
            # 尝试获取原始响应文本
            try:
                print(f"原始响应: {result_text}")
            except:
                print("无法获取原始响应")
            # 返回默认结果
            return {
                "keywords": [question],  # 将整个问题作为关键词
                "question_type": "综合查询",
                "confidence": 0.5
            }
        except Exception as e:
            print(f"❌ Gemini API 调用失败：{e}")
            # 返回默认结果
            return {
                "keywords": [question],
                "question_type": "综合查询", 
                "confidence": 0.3
            }


class MockProvider(LLMProvider):
    """模拟 LLM 提供商（用于测试）"""
    
    def extract_keywords(self, question: str) -> Dict[str, Any]:
        """模拟关键词提取"""
        # 简单的关键词提取逻辑（用于开发测试）
        keywords = []
        
        # 常见角色名称
        characters = ["柯南", "新一", "小兰", "小哀", "灰原", "博士", "基德", "赤井", "安室"]
        for char in characters:
            if char in question:
                keywords.append(char)
        
        # 如果没有找到角色，使用整个问题
        if not keywords:
            keywords = [question]
        
        return {
            "keywords": keywords,
            "question_type": "综合查询",
            "confidence": 0.6
        }


class LLMService:
    """LLM 服务管理器"""
    
    def __init__(self, provider_type: str = "gemini"):
        """
        初始化 LLM 服务
        
        Args:
            provider_type: 提供商类型 ("gemini", "mock")
        """
        self.provider_type = provider_type
        self.provider = self._create_provider()
    
    def _create_provider(self) -> LLMProvider:
        """创建 LLM 提供商实例"""
        if self.provider_type == "gemini":
            return GeminiProvider()
        elif self.provider_type == "mock":
            return MockProvider()
        else:
            raise ValueError(f"不支持的提供商类型：{self.provider_type}")
    
    def extract_keywords(self, question: str) -> Dict[str, Any]:
        """提取关键词（统一接口）"""
        return self.provider.extract_keywords(question)


# 工厂函数
def create_llm_service(provider_type: Optional[str] = None) -> LLMService:
    """
    创建 LLM 服务实例
    
    Args:
        provider_type: 提供商类型，如果为 None 则从环境变量读取
    """
    if provider_type is None:
        provider_type = os.environ.get("LLM_PROVIDER", "gemini")
    
    return LLMService(provider_type)