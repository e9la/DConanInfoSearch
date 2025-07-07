from flask import Flask, render_template, request, jsonify
import os
import re

from utils.interview_sources import get_interview_metadata
from utils.llm_service import create_llm_service
from utils.content_search import create_content_search_service


app = Flask(__name__, static_folder="static", template_folder="templates")

# 🚀 内存缓存 - 性能优化
ENABLE_CACHE = os.environ.get("ENABLE_CACHE", "true").lower() == "true"
manga_text_cache = {}  # 漫画文本缓存
interview_text_cache = {}  # 访谈文本缓存

# 🚀 通用缓存初始化辅助函数
def _init_cache_from_directory(cache_dict, base_dir, content_type, use_walk=False):
    """通用缓存初始化函数
    
    Args:
        cache_dict: 目标缓存字典
        base_dir: 基础目录路径
        content_type: 内容类型描述（用于日志）
        use_walk: 是否使用os.walk递归遍历子目录
    """
    if not ENABLE_CACHE or cache_dict:
        return
    
    if not os.path.exists(base_dir):
        return
    
    print(f"📥 正在预加载{content_type}到内存缓存...")
    
    if use_walk:
        # 递归遍历子目录
        for root, _, files in os.walk(base_dir):
            for filename in files:
                if filename.endswith(".txt"):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, base_dir)
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            cache_dict[rel_path] = f.read()
                    except Exception as e:
                        print(f"❌ 缓存文件失败 {rel_path}: {e}")
    else:
        # 只遍历当前目录
        for filename in os.listdir(base_dir):
            if filename.endswith(".txt"):
                file_path = os.path.join(base_dir, filename)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        cache_dict[filename] = f.read()
                except Exception as e:
                    print(f"❌ 缓存文件失败 {filename}: {e}")
    
    print(f"✅ 已缓存 {len(cache_dict)} 个{content_type}文件")

def init_manga_cache():
    """初始化漫画文本缓存"""
    _init_cache_from_directory(manga_text_cache, "data/japanese_text", "漫画文本")

def init_interview_cache():
    """初始化访谈文本缓存"""
    _init_cache_from_directory(interview_text_cache, "data/interviews", "访谈文本", use_walk=True)

# 功能一：漫画文本检索（优化版）
def count_word_in_documents(word):
    result = []
    base_dir = "data/japanese_text"
    
    # 🚀 使用缓存或直接读取文件
    if ENABLE_CACHE:
        init_manga_cache()  # 懒加载
        file_data = manga_text_cache
    else:
        # 原始方式：直接读取文件
        file_data = {}
        if not os.path.exists(base_dir):
            return result
        
        for filename in os.listdir(base_dir):
            if filename.endswith(".txt"):
                file_path = os.path.join(base_dir, filename)
                with open(file_path, encoding="utf-8") as f:
                    file_data[filename] = f.read()
    
    # 处理逻辑保持不变
    for filename, text in file_data.items():
        # 分页结构：===Page X===
        pages = re.split(r"===Page (\d+)===", text)
        page_nums = []
        total_count = 0

        # 结构：['', page_num1, content1, page_num2, content2, ...]
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

    # ✅ 按卷号排序
    result.sort(key=lambda x: x["volume"])
    return result

# 首页：返回 HTML 页面
@app.route("/")
def home():
    return render_template("index.html")

# 漫画文本检索接口
@app.route("/search", methods=["POST"])
def search():
    word = request.form.get("word", "").strip()
    result = count_word_in_documents(word)
    return jsonify(result)

# 访谈资料接口（优化版）
@app.route("/interview_search", methods=["POST"])
def interview_search():
    word = request.form.get("word", "").strip()
    base_dir = "data/interviews"
    results = []

    if not word:
        return jsonify(results)

    # 🚀 使用缓存或直接读取文件
    if ENABLE_CACHE:
        init_interview_cache()  # 懒加载
        file_data = interview_text_cache
    else:
        # 原始方式：直接读取文件
        file_data = {}
        for root, _, files in os.walk(base_dir):
            for filename in files:
                if filename.endswith(".txt"):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, base_dir)
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            file_data[rel_path] = f.read()
                    except Exception as e:
                        print(f"❌ Error reading {filepath}: {e}")

    # 处理逻辑保持不变
    for rel_path, text in file_data.items():
        try:
            count = text.count(word)
            if count > 0:
                # 匹配句子片段（简化处理：用句号、换行、问号、叹号分句）
                sentences = re.split(r'[。！？\n]', text)
                matched_snippets = []
                for s in sentences:
                    if word in s:
                        snippet = f"...{s.strip()}..."
                        matched_snippets.append(snippet)
                matched_snippets = matched_snippets[:3]  # 最多 3 条

                # 来源信息：可以继续扩展更多规则
                meta = get_interview_metadata(rel_path)

                results.append({
                    "file": rel_path,
                    "count": count,
                    "source": meta["source"],
                    "url": meta["url"],
                    "snippets": matched_snippets
                })
        except Exception as e:
            print(f"❌ Error processing {rel_path}: {e}")

    results.sort(key=lambda x: -x["count"])
    return jsonify(results)


# 🚀 缓存状态查看接口（调试用）
@app.route("/cache_status")
def cache_status():
    """查看缓存状态"""
    status = {
        "cache_enabled": ENABLE_CACHE,
        "manga_cache_size": len(manga_text_cache),
        "interview_cache_size": len(interview_text_cache),
        "total_memory_usage_mb": sum(len(text.encode('utf-8')) for text in manga_text_cache.values()) / 1024 / 1024 +
                                sum(len(text.encode('utf-8')) for text in interview_text_cache.values()) / 1024 / 1024
    }
    return jsonify(status)

# 未来：接入 LLM 问答接口
@app.route("/ask", methods=["GET", "POST"])
def ask():
    if request.method == "GET":
        return render_template("ask.html")
    
    question = request.form.get("question", "").strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400
    elif len(question) < 5:
        return jsonify({"error": "问题太短了, 请提供更多细节"}), 400
    elif len(question) > 50:
        return jsonify({"error": "问题太长了, 请简化你的问题"}), 400
    
    try:
        # 🚀 Step 1: 使用 LLM 服务提取关键词
        llm_service = create_llm_service()
        keyword_result = llm_service.extract_keywords(question)
        keywords = keyword_result["keywords"]
        
        print(f"📝 提取到关键词: {keywords}")
        
        # 🚀 Step 2: 初始化访谈文本缓存
        init_interview_cache()
        
        # 🚀 Step 3: 使用内容搜索服务查找相关内容
        search_service = create_content_search_service(interview_text_cache)
        search_results = search_service.search_keywords(keywords, max_length=10000)
        
        # 🚀 Step 4: 格式化返回结果
        if not search_results:
            return jsonify({
                "answer": "抱歉，没有找到相关的访谈内容。",
                "keywords_extracted": keywords,
                "results_count": 0
            })
        
        # 格式化搜索结果
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "text": result.text,
                "highlighted_text": result.highlighted_text,
                "keywords_found": result.keywords_found,
                "source": result.source,
                "url": result.url,
                "relevance_score": round(result.relevance_score, 2)
            })
        
        return jsonify({
            "answer": f"找到 {len(search_results)} 条相关访谈内容",
            "keywords_extracted": keywords,
            "results_count": len(search_results),
            "search_results": formatted_results,
            "total_length": sum(len(r.text) for r in search_results)
        })
        
    except Exception as e:
        print(f"❌ AI 处理失败：{e}")
        return jsonify({
            "answer": "抱歉，处理您的问题时出现了错误，请稍后再试。",
            "error": str(e)
        }), 500

# 启动服务（适配 Render 的 PORT 环境变量）
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
