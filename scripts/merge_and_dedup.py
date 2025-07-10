import os
import sys
import zipfile
import re
import json
import logging
import time
from pathlib import Path
from collections import defaultdict
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.config import INTERVIEW_DATA_DIR, PROCESSED_DATA_DIR, LOG_DIR

def extract_time(title):
    match = re.search(r"\d{4}", title)
    return match.group() if match else "未知"

def extract_participants(content):
    for name in ["青山刚昌", "山口胜平", "高山南", "堀川りょう"]:
        if name in content:
            return name
    return "未知"

def extract_theme(title, content):
    if "剧场版" in title:
        return "剧场版访谈"
    elif "1000话" in content:
        return "纪念访谈"
    return "常规访谈"

def is_valid_txt(name):
    return (
        name.endswith(".txt")
        and "__MACOSX" not in name
        and not os.path.basename(name).startswith("._")
    )

def extract_all_texts(data_dir):
    """提取所有 .txt 文件和 .zip 文件中的文本内容，添加 title 字段"""
    all_entries = []

    for root, _, files in os.walk(data_dir):
        for file in files:
            path = os.path.join(root, file)

            if "__MACOSX" in path or file.startswith("._"):
                continue

            if file.endswith(".txt"):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    filename = os.path.basename(path).replace(".txt", "")
                    all_entries.append({
                        "text": text,
                        "source": path,
                        "title": filename
                    })
                except Exception as e:
                    logging.warning(f"❌ 本地 txt 解码失败: {path} 原因: {e}")

            elif file.endswith(".zip"):
                try:
                    with zipfile.ZipFile(path, "r") as zipf:
                        for name in zipf.namelist():
                            if "__MACOSX" in name or os.path.basename(name).startswith("._"):
                                continue
                            if name.endswith(".txt"):
                                try:
                                    with zipf.open(name) as f:
                                        text = f.read().decode("utf-8").strip()
                                    filename = os.path.basename(name).replace(".txt", "")
                                    all_entries.append({
                                        "text": text,
                                        "source": f"{path}:{name}",
                                        "title": filename
                                    })
                                except Exception as e:
                                    logging.warning(f"❌ zip 解码失败: {path} 中的 {name}，原因: {e}")
                except Exception as e:
                    logging.error(f"❌ 无法打开 zip 文件: {path}，原因: {e}")

    return all_entries

def cluster_texts(entries, threshold=0.90):
    texts = [entry["text"] for entry in entries]
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(texts)
    similarity_matrix = cosine_similarity(embeddings)

    clusters = []
    used = set()
    for i in range(len(texts)):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        for j in range(i + 1, len(texts)):
            if j not in used and similarity_matrix[i][j] > threshold:
                cluster.append(j)
                used.add(j)
        clusters.append(cluster)
    return clusters

def merge_clusters(entries, clusters):
    """根据聚类结果合并内容、来源及元信息"""
    merged = []
    for idx, cluster in enumerate(clusters):
        merged_texts = [entries[i]["text"] for i in cluster]
        sources = [entries[i]["source"] for i in cluster]
        representative_text = merged_texts[0]

        # ✅ 使用首条的 title，如果没有则 fallback
        raw_title = entries[cluster[0]].get("title", "").strip()
        title = raw_title if raw_title else f"自动生成访谈_{idx+1}"

        metadata = {
            "time": extract_time(title),
            "theme": extract_theme(title, representative_text),
            "participants": extract_participants(representative_text)
        }

        merged.append({
            "id": f"interview_{idx+1}",
            "title": title,
            "content": representative_text,
            "sources": sources,
            "time": metadata["time"],
            "theme": metadata["theme"],
            "participants": metadata["participants"]
        })
    return merged

# 初始化日志目录和设置
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "merge_log.txt"), mode="a", encoding="utf-8")
    ]
)

def main():
    raw_dir = INTERVIEW_DATA_DIR
    output_path = os.path.join(PROCESSED_DATA_DIR, "merged_interviews.json")
    Path(PROCESSED_DATA_DIR).mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    logging.info("📂 提取所有文本中...")
    all_entries = extract_all_texts(raw_dir)
    logging.info(f"✅ 共提取文本数量: {len(all_entries)}")

    logging.info("🔍 计算语义相似度并聚类...")
    clusters = cluster_texts(all_entries)
    logging.info(f"✅ 聚类完成，生成访谈条数: {len(clusters)}")

    logging.info("🧩 合并聚类内容...")
    merged = merge_clusters(all_entries, clusters)

    logging.info(f"💾 保存到 {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    duration = time.time() - start_time
    logging.info(f"🎉 完成！共写入 {len(merged)} 条访谈，用时 {duration:.2f} 秒")

if __name__ == "__main__":
    main()
