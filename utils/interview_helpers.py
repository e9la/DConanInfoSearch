# 文件: utils/interview_helpers.py

import re

def extract_time(title):
    """
    尝试从标题中提取年份信息
    """
    match = re.search(r"\d{4}", title)
    return match.group() if match else "未知"

def extract_participants(content):
    """
    尝试从内容中提取可能出现的访谈参与者（根据关键词判断）
    """
    known_names = ["青山刚昌", "山口胜平", "高山南", "堀川りょう", "林原めぐみ", "古谷彻", "小山力也", "大谷育江", "岩居由希子"]
    participants = [name for name in known_names if name in content]
    return "、".join(participants) if participants else "未知"

def extract_theme(title, content):
    """
    尝试从标题或内容中提取访谈主题（如剧场版、纪念、角色等）
    """
    if "剧场版" in title or "映画" in title or "映画" in content:
        return "剧场版访谈"
    elif "1000话" in title or "1000話" in content or "周年" in title:
        return "纪念访谈"
    elif "角色" in content or "人物" in title or "CV" in content:
        return "角色专访"
    return "常规访谈"

# def extract_contexts(full_text, keyword, window=1):
#     paragraphs = full_text.split("\n")
#     matches = []
#     for i, para in enumerate(paragraphs):
#         if keyword in para:
#             start = max(i - window, 0)
#             end = min(i + window + 1, len(paragraphs))
#             context_block = "\n".join(paragraphs[start:end])
#             matches.append(context_block)
#     return matches


def extract_contexts(text, keyword, window=1):
    if not keyword:
        return []
    paragraphs = text.split("\n")
    results = []
    for i, para in enumerate(paragraphs):
        if keyword in para:
            start = max(0, i - window)
            end = min(len(paragraphs), i + window + 1)
            block = "\n".join(paragraphs[start:end])
            results.append(block)
    return results
