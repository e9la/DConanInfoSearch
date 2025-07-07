"""
内容搜索服务模块 - 基于关键词的智能访谈内容搜索
实现相关性评分、上下文提取、去重和长度控制
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

from utils.interview_sources import get_interview_metadata


@dataclass
class SearchResult:
    """搜索结果数据类"""
    text: str                      # 上下文文本
    keywords_found: List[str]      # 匹配的关键词
    relevance_score: float         # 相关性分数
    source: str                    # 来源文件
    url: Optional[str]             # 原文链接  
    highlighted_text: str          # 高亮关键词后的文本
    start_position: int            # 在原文中的起始位置
    end_position: int              # 在原文中的结束位置


class ContentSearchService:
    """内容搜索服务"""
    
    def __init__(self, interview_cache: Dict[str, str]):
        """
        初始化搜索服务
        
        Args:
            interview_cache: 访谈文本缓存字典
        """
        self.interview_cache = interview_cache
        self.sentence_delimiters = r'[。！？\n]'
        
    def search_keywords(self, keywords: List[str], max_length: int = 10000) -> List[SearchResult]:
        """
        根据关键词搜索相关内容
        
        Args:
            keywords: 关键词列表
            max_length: 结果总长度限制
            
        Returns:
            按相关性排序的搜索结果列表
        """
        if not keywords:
            return []
        
        print(f"🔍 开始搜索关键词: {keywords}")
        
        # 1. 收集所有匹配结果
        all_matches = self._find_all_matches(keywords)
        print(f"📊 找到 {len(all_matches)} 个初步匹配")
        
        # 2. 提取上下文并评分
        search_results = []
        for match in all_matches:
            # 传递所有关键词用于上下文分析
            match['all_keywords'] = keywords
            context = self._extract_context(match)
            if context:
                search_results.append(context)
        
        print(f"📝 提取 {len(search_results)} 个上下文片段")
        
        # 3. 去重和合并
        deduplicated_results = self._deduplicate_results(search_results)
        print(f"🔄 去重后剩余 {len(deduplicated_results)} 个片段")
        
        # 4. 按相关性排序
        sorted_results = sorted(deduplicated_results, key=lambda x: x.relevance_score, reverse=True)
        
        # 5. 长度控制
        final_results = self._select_top_results(sorted_results, max_length)
        print(f"✅ 最终返回 {len(final_results)} 个结果，总长度约 {sum(len(r.text) for r in final_results)} 字符")
        
        return final_results
    
    def _find_all_matches(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """查找所有关键词匹配"""
        matches = []
        
        for file_path, content in self.interview_cache.items():
            if not content.strip():
                continue
                
            for keyword in keywords:
                # 使用正则表达式进行不区分大小写的搜索
                pattern = re.escape(keyword)
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    matches.append({
                        'keyword': keyword,
                        'file_path': file_path,
                        'content': content,
                        'start': match.start(),
                        'end': match.end(),
                        'position': match.start()
                    })
        
        return matches
    
    def _extract_context(self, match: Dict[str, Any], radius: int = 200) -> Optional[SearchResult]:
        """提取匹配关键词的上下文"""
        content = match['content']
        keyword = match['keyword']
        position = match['position']
        file_path = match['file_path']
        
        # 计算上下文边界
        start_pos = max(0, position - radius)
        end_pos = min(len(content), position + radius)
        
        # 扩展到句子边界
        start_boundary = self._find_sentence_start(content, start_pos)
        end_boundary = self._find_sentence_end(content, end_pos)
        
        # 提取上下文文本
        context_text = content[start_boundary:end_boundary].strip()
        
        if not context_text or len(context_text) < 10:
            return None
        
        # 获取来源信息
        metadata = get_interview_metadata(file_path)
        source_name = metadata.get('source', file_path)
        source_url = metadata.get('url')
        
        # 查找这个上下文中的所有关键词
        keywords_found = []
        all_keywords = match.get('all_keywords', [keyword])  # 从外部传入所有关键词
        
        for kw in all_keywords:
            if re.search(re.escape(kw), context_text, re.IGNORECASE):
                keywords_found.append(kw)
        
        # 如果没有传入所有关键词，至少包含当前关键词
        if not keywords_found:
            keywords_found = [keyword]
        
        # 计算相关性分数
        relevance_score = self._calculate_relevance_score(context_text, keywords_found)
        
        # 生成高亮文本
        highlighted_text = self._highlight_keywords(context_text, keywords_found)
        
        return SearchResult(
            text=context_text,
            keywords_found=keywords_found,
            relevance_score=relevance_score,
            source=source_name,
            url=source_url,
            highlighted_text=highlighted_text,
            start_position=start_boundary,
            end_position=end_boundary
        )
    
    def _find_sentence_start(self, text: str, position: int) -> int:
        """向前查找句子开始位置"""
        if position <= 0:
            return 0
        
        # 向前查找句子分隔符
        for i in range(position - 1, -1, -1):
            if re.match(self.sentence_delimiters, text[i]):
                return i + 1
        
        return 0
    
    def _find_sentence_end(self, text: str, position: int) -> int:
        """向后查找句子结束位置"""
        if position >= len(text):
            return len(text)
        
        # 向后查找句子分隔符
        for i in range(position, len(text)):
            if re.match(self.sentence_delimiters, text[i]):
                return i + 1
        
        return len(text)
    
    def _calculate_relevance_score(self, text: str, keywords_found: List[str]) -> float:
        """计算相关性分数"""
        if not keywords_found:
            return 0.0
        
        # 基础分数：每个关键词匹配 +2分
        base_score = len(keywords_found) * 2.0
        
        # 密度奖励：多个关键词在同一段落 +0.5分/词
        density_bonus = 0.5 * len(keywords_found) if len(keywords_found) > 1 else 0
        
        # 长度惩罚：过长文本轻微降分
        length_penalty = len(text) / 2000  # 每2000字符减1分
        
        # 关键词密度奖励
        total_keyword_chars = sum(len(kw) for kw in keywords_found)
        density_ratio = total_keyword_chars / len(text) if text else 0
        density_bonus += density_ratio * 5  # 密度越高分数越高
        
        final_score = base_score + density_bonus - length_penalty
        return max(0.1, final_score)  # 最低0.1分
    
    def _highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """高亮关键词"""
        highlighted = text
        
        for keyword in keywords:
            # 使用HTML标记高亮（适用于前端显示）
            pattern = re.escape(keyword)
            highlighted = re.sub(
                pattern, 
                f'<mark>{keyword}</mark>', 
                highlighted, 
                flags=re.IGNORECASE
            )
        
        return highlighted
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重和合并相似结果"""
        if not results:
            return []
        
        # 按来源分组
        grouped_by_source = defaultdict(list)
        for result in results:
            grouped_by_source[result.source].append(result)
        
        deduplicated = []
        
        for source_results in grouped_by_source.values():
            # 按位置排序
            source_results.sort(key=lambda x: x.start_position)
            
            merged_results = []
            i = 0
            
            while i < len(source_results):
                current = source_results[i]
                j = i + 1
                
                # 查找可以合并的相邻结果
                while j < len(source_results):
                    next_result = source_results[j]
                    
                    # 如果重叠或距离很近（<100字符），合并
                    if (next_result.start_position - current.end_position) < 100:
                        # 合并文本
                        merged_text = current.text
                        if not merged_text.endswith(next_result.text):
                            merged_text += " ... " + next_result.text
                        
                        # 合并关键词
                        merged_keywords = list(set(current.keywords_found + next_result.keywords_found))
                        
                        # 创建合并后的结果
                        current = SearchResult(
                            text=merged_text,
                            keywords_found=merged_keywords,
                            relevance_score=current.relevance_score + next_result.relevance_score * 0.5,
                            source=current.source,
                            url=current.url,
                            highlighted_text=self._highlight_keywords(merged_text, merged_keywords),
                            start_position=current.start_position,
                            end_position=next_result.end_position
                        )
                        j += 1
                    else:
                        break
                
                merged_results.append(current)
                i = j
            
            deduplicated.extend(merged_results)
        
        return deduplicated
    
    def _select_top_results(self, sorted_results: List[SearchResult], max_length: int) -> List[SearchResult]:
        """根据长度限制选择顶部结果"""
        selected = []
        total_length = 0
        
        for result in sorted_results:
            result_length = len(result.text)
            
            # 如果加上这个结果不会超过限制，就添加
            if total_length + result_length <= max_length:
                selected.append(result)
                total_length += result_length
            else:
                # 如果这是第一个结果且过长，截断它
                if not selected and result_length > max_length:
                    truncated_text = result.text[:max_length - 100] + "..."
                    result.text = truncated_text
                    result.highlighted_text = self._highlight_keywords(truncated_text, result.keywords_found)
                    selected.append(result)
                break
        
        return selected


def create_content_search_service(interview_cache: Dict[str, str]) -> ContentSearchService:
    """
    创建内容搜索服务实例
    
    Args:
        interview_cache: 访谈文本缓存
        
    Returns:
        ContentSearchService 实例
    """
    return ContentSearchService(interview_cache)