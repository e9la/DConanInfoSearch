import os
import re
import json

from utils.config import MANGA_TEXT_DIR, INTERVIEW_DATA_DIR, PROCESSED_DATA_DIR

# 加载 sbsub 访谈标题-链接映射表
try:
    with open(os.path.join(INTERVIEW_DATA_DIR, "sbsub/sbsub_title_url_map.json"), encoding="utf-8") as f:
        sbsub_title_url_map = json.load(f)

    with open(os.path.join(INTERVIEW_DATA_DIR, "bilibili_article/bilibili_readlists.json"), encoding="utf-8") as f:
        bilibili_source_map = json.load(f)

except FileNotFoundError:
    sbsub_title_url_map = {}
    bilibili_source_map = {}

# Old version, kinda hard-coded
# def get_interview_metadata(rel_path: str) -> dict:
#     # 1. 名侦探柯南事务所论坛
#     if "bbs_aptx.txt" in rel_path:
#         return {
#             "source": "名侦探柯南事务所论坛",
#             "url": "https://bbs.aptx.cn/forum.php?mod=viewthread&tid=296846&extra=page%3D5&page=2"
#         }

#     # 2. B站 readlist
#     match = re.search(r"bilibili_article/(rl\d+)", rel_path)
#     if match:
#         full_rl_id = match.group(1)        # rl725889
#         numeric_id = full_rl_id[2:]        # 725889
#         source = bilibili_source_map.get(numeric_id, "B站访谈整理（by未知）")
#         return {
#             "source": source,
#             "url": f"https://www.bilibili.com/read/readlist/{full_rl_id}"
#         }

#     # 3. 银色子弹 sbsub
#     if "sbsub/" in rel_path:
#         filename = os.path.basename(rel_path).replace(".txt", "")
#         url = sbsub_title_url_map.get(filename)
#         return {
#             "source": "银色子弹访谈整理",
#             "url": url
#         }
    
#     # ✅ 4. B站字幕（匹配文件名中的 [BVxxxx]）
#     match = re.search(r"bilibili_subtitles/.*?\[(BV[0-9A-Za-z]{10})\]", rel_path)
#     if match:
#         bvid = match.group(1)
#         return {
#             "source": "B站视频",
#             "url": f"https://www.bilibili.com/video/{bvid}/"
#         }
    

#     # 5. fallback
    # return {
    #     "source": "未知来源",
    #     "url": None
    # }

def get_interview_metadata(rel_path: str) -> dict:
    metadata = {}

    # 提取文件名和上级目录名
    filename = os.path.basename(rel_path).replace(".txt", "")
    parent_folder = os.path.basename(os.path.dirname(rel_path))  # 可能是年份或“其他”

    # 年份处理
    if re.fullmatch(r"\d{4}", parent_folder):
        metadata["year"] = parent_folder
    else:
        metadata["year"] = "未知年份"  # 或保留为 "其他"

    # 提取文件名结构：如 1997_M1_青山刚昌_日文.txt
    parts = filename.split(".txt")[0].split("_")
    if len(parts) >= 4:
        metadata["source"] = parts[:-1].join(" ")
        metadata["language"] = parts[-1]
    else:
        metadata["source"] = "未知来源"
        metadata["language"] = "未知语言"

    # 提取文件中的所有 URL
    try:
        with open(rel_path, "r", encoding="utf-8") as f:
            content = f.read()
            urls = re.findall(r'https?://[^\s\)\]]+', content)
            metadata["urls"] = list(set(urls))  # 去重
    except Exception as e:
        metadata["urls"] = []
        print(f"[Warning] Failed to read {rel_path}: {e}")

    return metadata

    