import os
import re
from utils.cache_utils import init_manga_cache, manga_text_cache
from utils.config import MANGA_TEXT_DIR, ENABLE_CACHE

def count_word_in_documents(word):
    result = []

    if ENABLE_CACHE:
        init_manga_cache()
        file_data = manga_text_cache
    else:
        file_data = {}
        for filename in os.listdir(MANGA_TEXT_DIR):
            if filename.endswith(".txt"):
                with open(os.path.join(MANGA_TEXT_DIR, filename), encoding="utf-8") as f:
                    file_data[filename] = f.read()

    for filename, text in file_data.items():
        pages = re.split(r"===Page (\d+)===", text)
        page_nums = []
        total_count = 0

        for i in range(1, len(pages) - 1, 2):
            page_number = int(pages[i])
            content = pages[i + 1]
            count = content.count(word)
            if count > 0:
                page_nums.append(page_number)
                total_count += count

        if total_count > 0:
            volume_match = re.match(r"^(\d+)\.txt$", filename)
            volume = int(volume_match.group(1)) if volume_match else filename
            result.append({
                "volume": volume,
                "count": total_count,
                "pages": sorted(page_nums)
            })

    result.sort(key=lambda x: x["volume"])
    return result


def word_expand(word):
    related_lists = [Vocabulary for Vocabulary in Vocabularys if word in Vocabulary]
    if related_lists:
        # 拼接所有相关列表并去重（保持原始顺序）
        result = []
        seen = set()
        for lst in related_lists:
            for item in lst:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
        return result
    else:
        # 未找到时返回仅包含该词的列表
        return [word]
