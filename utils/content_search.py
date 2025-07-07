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
        
        # 常见关键词列表（需要降权的）
        self.common_keywords = {
            # 主要角色（出现频率很高）
            "柯南", "工藤新一", "新一", "灰原哀", "小哀", "哀", "小兰", "毛利兰", 
            "毛利小五郎", "阿笠博士", "博士", "少年侦探团",
            # 常见词汇
            "名侦探柯南", "柯南", "侦探", "案件", "推理", "真相", "黑衣组织", "组织",
            "青山刚昌", "作者", "漫画", "动画", "剧场版",
            # 日文常见词
            "コナン", "新一", "蘭", "哀", "灰原"
        }
        
        # 计算关键词在整个语料库中的频率
        self._keyword_frequencies = self._calculate_keyword_frequencies()
    
    def _calculate_keyword_frequencies(self) -> Dict[str, int]:
        """计算关键词在整个语料库中的出现频率"""
        frequencies = {}
        total_text = " ".join(self.interview_cache.values())
        
        for keyword in self.common_keywords:
            count = len(re.findall(re.escape(keyword), total_text, re.IGNORECASE))
            frequencies[keyword] = count
        
        return frequencies
    
    def _get_keyword_importance(self, keyword: str) -> float:
        """
        计算关键词重要性分数
        
        Args:
            keyword: 关键词
            
        Returns:
            重要性分数，0.1-1.0，越常见分数越低
        """
        if keyword in self.common_keywords:
            # 常见关键词降权
            frequency = self._keyword_frequencies.get(keyword, 0)
            if frequency > 100:  # 出现超过100次的关键词大幅降权
                return 0.2
            elif frequency > 50:  # 出现超过50次的关键词中等降权
                return 0.4
            elif frequency > 20:  # 出现超过20次的关键词轻微降权
                return 0.6
            else:
                return 0.8
        else:
            # 非常见关键词保持高权重
            return 1.0
    
    def _should_include_context(self, keywords_in_context: List[str], all_keywords: List[str]) -> bool:
        """
        判断是否应该包含某个上下文片段
        
        Args:
            keywords_in_context: 该上下文中找到的关键词
            all_keywords: 用户查询的所有关键词
            
        Returns:
            是否应该包含这个上下文
        """
        if not keywords_in_context:
            return False
        
        # 计算常见关键词和非常见关键词的数量
        common_count = sum(1 for kw in keywords_in_context if kw in self.common_keywords)
        uncommon_count = len(keywords_in_context) - common_count
        
        # 如果只有常见关键词，要求至少有2个不同的关键词
        if uncommon_count == 0:
            return len(set(keywords_in_context)) >= 2
        
        # 如果有非常见关键词，总是包含
        return True
    
    def _calculate_context_length_limit(self, keywords_in_context: List[str], base_radius: int = 200) -> int:
        """
        根据关键词类型动态调整上下文长度
        
        Args:
            keywords_in_context: 上下文中的关键词
            base_radius: 基础半径
            
        Returns:
            调整后的上下文半径
        """
        if not keywords_in_context:
            return base_radius
        
        # 计算平均重要性
        avg_importance = sum(self._get_keyword_importance(kw) for kw in keywords_in_context) / len(keywords_in_context)
        
        # 常见关键词减少上下文长度
        if avg_importance < 0.5:
            return int(base_radius * 0.6)  # 减少40%
        elif avg_importance < 0.7:
            return int(base_radius * 0.8)  # 减少20%
        else:
            return base_radius
        
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
        
        # 🚀 Step 0: 分析关键词重要性
        keyword_importance = {kw: self._get_keyword_importance(kw) for kw in keywords}
        print(f"📊 关键词重要性: {keyword_importance}")
        
        # 1. 收集所有匹配结果
        all_matches = self._find_all_matches(keywords)
        print(f"📊 找到 {len(all_matches)} 个初步匹配")
        
        # 2. 提取上下文并评分（加入过滤）
        search_results = []
        filtered_count = 0
        for match in all_matches:
            # 传递所有关键词用于上下文分析
            match['all_keywords'] = keywords
            context = self._extract_context(match)
            if context:
                # 🚀 应用关键词组合过滤
                if self._should_include_context(context.keywords_found, keywords):
                    search_results.append(context)
                else:
                    filtered_count += 1
        
        print(f"📝 提取 {len(search_results)} 个上下文片段（过滤掉 {filtered_count} 个只有常见关键词的片段）")
        
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
    
    def _extract_context(self, match: Dict[str, Any], base_radius: int = 200) -> Optional[SearchResult]:
        """提取匹配关键词的上下文"""
        content = match['content']
        keyword = match['keyword']
        position = match['position']
        file_path = match['file_path']
        all_keywords = match.get('all_keywords', [keyword])
        
        # 🚀 预先找到这个区域的所有关键词，用于动态调整上下文长度
        temp_start = max(0, position - base_radius)
        temp_end = min(len(content), position + base_radius)
        temp_context = content[temp_start:temp_end]
        
        temp_keywords_found = []
        for kw in all_keywords:
            if re.search(re.escape(kw), temp_context, re.IGNORECASE):
                temp_keywords_found.append(kw)
        
        # 🚀 根据关键词类型动态调整上下文长度
        adjusted_radius = self._calculate_context_length_limit(temp_keywords_found, base_radius)
        
        # 计算上下文边界
        start_pos = max(0, position - adjusted_radius)
        end_pos = min(len(content), position + adjusted_radius)
        
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
        for kw in all_keywords:
            if re.search(re.escape(kw), context_text, re.IGNORECASE):
                keywords_found.append(kw)
        
        # 如果没有找到关键词，至少包含当前关键词
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
        
        # 🚀 计算基于重要性的加权分数
        importance_weighted_score = 0.0
        for keyword in keywords_found:
            importance = self._get_keyword_importance(keyword)
            importance_weighted_score += importance * 2.0  # 每个关键词基础分2分，按重要性加权
        
        # 密度奖励：多个关键词在同一段落（但考虑重要性）
        if len(keywords_found) > 1:
            # 计算平均重要性
            avg_importance = sum(self._get_keyword_importance(kw) for kw in keywords_found) / len(keywords_found)
            density_bonus = 0.5 * len(keywords_found) * avg_importance
        else:
            density_bonus = 0
        
        # 长度惩罚：过长文本轻微降分
        length_penalty = len(text) / 2000  # 每2000字符减1分
        
        # 关键词密度奖励（但降低常见词的影响）
        weighted_keyword_chars = sum(len(kw) * self._get_keyword_importance(kw) for kw in keywords_found)
        density_ratio = weighted_keyword_chars / len(text) if text else 0
        density_bonus += density_ratio * 3  # 调整系数从5降到3
        
        final_score = importance_weighted_score + density_bonus - length_penalty
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