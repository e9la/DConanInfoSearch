import os
import zipfile
import json
from utils.config import MANGA_TEXT_DIR, INTERVIEW_DATA_DIR, PROCESSED_DATA_DIR, ENABLE_CACHE

manga_text_cache = {}
interview_text_cache = {}

def init_manga_cache():
    if not ENABLE_CACHE or manga_text_cache:
        return
    _init_cache_from_directory(manga_text_cache, MANGA_TEXT_DIR)

def init_interview_cache():
    if not ENABLE_CACHE or interview_text_cache:
        return

    json_path = os.path.join(PROCESSED_DATA_DIR, "merged_interviews.json")
    if not os.path.exists(json_path):
        print(f"⚠️ 找不到 {json_path}，请先运行 merge_and_dedup.py 生成该文件")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            merged = json.load(f)
        for interview in merged:
            interview_text_cache[interview["id"]] = interview["content"]
    except Exception as e:
        print(f"❌ 加载 merged_interviews.json 失败: {e}")

def _init_cache_from_directory(cache_dict, base_dir, use_walk=False):
    if not os.path.exists(base_dir):
        return

    file_iter = os.walk(base_dir) if use_walk else [(base_dir, [], os.listdir(base_dir))]

    for root, _, files in file_iter:
        for filename in files:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir)

            if filename.endswith(".txt"):
                try:
                    with open(filepath, encoding="utf-8") as f:
                        cache_dict[rel_path] = f.read()
                except Exception as e:
                    print(f"❌ 缓存失败: {rel_path}: {e}")

            elif filename.endswith(".zip"):
                try:
                    with zipfile.ZipFile(filepath, "r") as z:
                        for name in z.namelist():
                            # 过滤 __MACOSX 文件夹 和 Apple 资源文件
                            if "__MACOSX" in name or os.path.basename(name).startswith("._"):
                                continue
                            if name.endswith(".txt"):
                                try:
                                    with z.open(name) as f:
                                        content = f.read().decode("utf-8")
                                        key = f"{rel_path}|{name}"
                                        cache_dict[key] = content
                                except UnicodeDecodeError:
                                    print(f"❌ 解码失败: {rel_path} 中的 {name}")
                except Exception as e:
                    print(f"❌ 无法读取 zip 文件: {rel_path}: {e}")
