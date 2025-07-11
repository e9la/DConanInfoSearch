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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as tfidf_cosine_similarity

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.config import INTERVIEW_DATA_DIR, PROCESSED_DATA_DIR, LOG_DIR
from utils.constants import NAMES, CATEGORIES

def extract_time(title):
    match = re.search(r"\d{4}", title)
    return match.group() if match else "未知"

def extract_participants(content):
    for name in NAMES:
        if name in content:
            return name
    return "未知"

def extract_theme(title, content):
    for catg in CATEGORIES:
        if catg in title or catg in content:
            return catg
        else:
            return "常规访谈"

def is_valid_txt(name):
    return (
        name.endswith(".txt")
        and "__MACOSX" not in name
        and not os.path.basename(name).startswith("._")
    )

def normalize_text(text):
    text = re.sub(r"[QＡ]?[.\d：:]+", "", text)
    text = text.replace("\n", "").replace(" ", "")
    text = text.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    return text.strip()

def extract_all_texts(data_dir):
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
                    all_entries.append({"text": text, "source": path, "title": filename})
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
                                    all_entries.append({"text": text, "source": f"{path}:{name}", "title": filename})
                                except Exception as e:
                                    logging.warning(f"❌ zip 解码失败: {path} 中的 {name}，原因: {e}")
                except Exception as e:
                    logging.error(f"❌ 无法打开 zip 文件: {path}，原因: {e}")
    return all_entries

def cluster_texts(entries, sentence_threshold=0.9, min_match_count=10):
    """
    快速基于局部文本相似度的访谈聚类。
    若两篇文章有 >= min_match_count 条句子彼此相似（cos > sentence_threshold），则认为可以合并。
    """
    from sklearn.utils import murmurhash3_32
    
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 提取句子
    all_sentences = []
    entry_sent_idx = []  # entry_id -> list of sentence indices

    for idx, entry in enumerate(entries):
        sents = re.split(r'[。！？\n]', entry['text'])
        sents = [s.strip() for s in sents if len(s.strip()) > 6]  # 去除短句
        all_sentences.extend(sents)
        entry_sent_idx.append((idx, list(range(len(all_sentences) - len(sents), len(all_sentences)))))

    # 向量化所有句子（一次性）
    sentence_embeddings = model.encode(all_sentences, show_progress_bar=True)

    # 为每篇文章建立 MinHash 签名集合
    sig_sets = []
    for _, sent_ids in entry_sent_idx:
        hashes = set(murmurhash3_32(str(sentence_embeddings[i]), positive=True) for i in sent_ids)
        sig_sets.append(hashes)

    # 简单判重：若 hash 重叠数 >= N，则判为近似
    clusters = []
    used = set()
    for i in range(len(entries)):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        for j in range(i + 1, len(entries)):
            if j in used:
                continue
            overlap = len(sig_sets[i] & sig_sets[j])
            if overlap >= min_match_count:
                cluster.append(j)
                used.add(j)
        clusters.append(cluster)
        
    # 后处理：尝试避免将某些特殊文本（如 bbs_aptx）单独留在 cluster 中
    final_clusters = []
    for cluster in clusters:
        if len(cluster) > 1:
            final_clusters.append(cluster)
        else:
            i = cluster[0]
            if "bbs_aptx.txt" in entries[i]["source"]:
                # 尝试加入到最相近的已有 cluster 中
                max_overlap = 0
                best_cluster = None
                for c in final_clusters:
                    j = c[0]  # 任取代表项
                    overlap = len(sig_sets[i] & sig_sets[j])
                    if overlap > max_overlap:
                        max_overlap = overlap
                        best_cluster = c
                if best_cluster:
                    best_cluster.append(i)
                else:
                    logging.warning(f"🟡 {entries[i]['source']} 无法与其他访谈匹配，已忽略")
            else:
                final_clusters.append(cluster)
    
    return final_clusters

def merge_clusters(entries, clusters):
    merged = []
    for idx, cluster in enumerate(clusters):
        merged_texts = [entries[i]["text"] for i in cluster]
        sources = [entries[i]["source"] for i in cluster]
        representative_idx = next(i for i in cluster if "bbs_aptx" not in entries[i]["title"])
        representative_text = entries[representative_idx]["text"]
        raw_title = entries[representative_idx].get("title", "").strip()
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
