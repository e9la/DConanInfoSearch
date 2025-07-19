# 文件: app.py
import os
import time
import re
import random
import json

from flask import Flask, request, redirect, render_template, make_response, jsonify, session, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from utils.interview_sources import get_interview_metadata
from utils.cache_utils import init_interview_cache, manga_text_cache, interview_text_cache
from utils.search_utils import count_word_in_documents, word_expand
from utils.quiz_utils import load_quiz_bank
from utils.interview_helpers import extract_time, extract_participants, extract_theme, extract_contexts
from urllib.parse import unquote

# Flask init
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "your-secret-key"

# Rate limit
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

# Quiz bank init
quiz_bank = load_quiz_bank()

# used for clustered interviews
# with open(os.path.join(PROCESSED_DATA_DIR, "merged_interviews.json"), "r", encoding="utf-8") as f:
#     INTERVIEWS = json.load(f)

with open("data/debunk/debunk_data.json", encoding="utf-8") as f:
    debunk_data = json.load(f)

# =============================
# 页面入口：答题验证界面
# =============================
@app.route("/", methods=["GET", "POST"])
def quiz_entry():
    if not quiz_bank:
        print("⚠️ 当前无题库，自动跳过验证流程")
        resp = make_response(redirect("/search_page"))
        resp.set_cookie("verified", "true")
        return resp

    if request.method == "POST":
        user_answer = request.form.get("answer", "").strip()
        correct_answer = session.get("correct_answer", "")
        if user_answer == correct_answer:
            resp = make_response(redirect("/search_page"))
            resp.set_cookie("verified", "true")
            return resp
        return render_template("quiz.html", question=session.get("question", "题库加载失败"), error="回答错误，请再试一次")

    q = random.choice(quiz_bank)
    session["question"] = q["question"]
    session["correct_answer"] = q["answer"]
    return render_template("quiz.html", question=q["question"])

# =============================
# 搜索界面页面（前端 HTML）
# =============================
@app.route("/search_page")
def search_page():
    verified = request.cookies.get("verified")
    if verified != "true":
        return redirect("/")
    return render_template("index.html")

# =============================
# 漫画文本检索接口
# =============================
@app.route("/search", methods=["POST"])
def search():
    word = request.form.get("word", "").strip()
    volume_filter = request.form.get("volume_filter", "").strip()
    results = count_word_in_documents(word)

    if volume_filter:
        results = [
            r for r in results if str(r.get("volume", "")).strip() == volume_filter
        ]

    return jsonify(results)

# =============================
# 访谈来源选项接口
# =============================
@app.route("/interview_sources", methods=["GET"])
def interview_sources():
    if not interview_text_cache:
        init_interview_cache()

    sources = set()
    for rel_path in interview_text_cache:
        meta = get_interview_metadata(rel_path)
        if meta["source"]:
            sources.add(meta["source"])

    return jsonify(sorted(sources))

# =============================
# 访谈资料搜索接口
# =============================
@app.route("/interview_search", methods=["POST"])
def interview_search():
    word = request.form.get("word", "").strip()
    source_filter = request.form.get("source_filter", "").strip()
    results = []

    if not word:
        return jsonify(results)

    words = word_expand(word)  # 支持日文变形展开，如ひらがな/漢字等

    for rel_path, text in interview_text_cache.items():
        meta = get_interview_metadata(rel_path)

        # 来源筛选（可选）
        if source_filter and meta["source"] != source_filter:
            continue

        matched = False
        total_count = 0
        all_snippets = []

        for w in words:
            count = text.count(w)
            if count > 0:
                matched = True
                total_count += count
                sentences = re.split(r'[\u3002！？\n]', text)
                snippets = [f"...{s.strip()}..." for s in sentences if w in s][:3]
                all_snippets.extend(snippets)

        if matched:
            results.append({
                "id": rel_path,  # rel_path 作为唯一标识符
                "title": os.path.basename(rel_path).replace(".txt", ""),
                "count": total_count,
                "sources": [rel_path],
                "snippets": all_snippets[:3],
            })

    results.sort(key=lambda x: -x["count"])
    
    #print(f"🔍 返回结果含 ID: {[r['id'] for r in results]}")

    return jsonify(results)

# =============================
# 访谈详情页接口
# =============================
@app.route("/interview_detail/<path:interview_id>")
def interview_detail(interview_id):
    interview_id = unquote(interview_id)
    # 查找缓存
    text = interview_text_cache.get(interview_id)
    if not text:
        print(f"❌ 找不到访谈缓存: {interview_id}")
        return "该访谈不存在", 404

    # 提取元数据
    title = os.path.basename(interview_id).replace(".txt", "")
    meta = get_interview_metadata(interview_id)

    metadata = {
        "time": extract_time(title),
        "participants": extract_participants(text),
        "theme": extract_theme(title, text),
    }

    # 获取关键词
    search_word = request.args.get("kw", "").strip()
    match_contexts = extract_contexts(text, search_word)

    source_links = [{
        "title": title,
        "source": meta.get("source", "未知来源"),
        "url": meta["urls"][0] if meta.get("urls") else None
    }]

    return render_template(
        "interview_detail.html",
        interview={"id": interview_id, "title": title, "content": text},
        metadata=metadata,
        keyword=search_word,
        match_contexts=match_contexts,
        source_links=source_links
    )

@app.route("/debunk")
def debunk():
    return render_template("debunk.html")

from flask import send_from_directory

@app.route("/debunk_all", methods=["GET"])
def debunk_all():
    return jsonify(debunk_data)


@app.route("/data/debunk/figs/<path:filename>")
def serve_debunk_image(filename):
    return send_from_directory("data/debunk/figs", filename)


@app.route("/debunk_search", methods=["POST"])
def debunk_search():
    from flask import request, jsonify
    import json
    import os

    word = request.form.get("word", "").strip().lower()

    debunk_path = os.path.join("data", "debunk", "debunk_data.json")
    with open(debunk_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    def match(entry):
        return (
            word in entry["title"].lower()
            or word in entry["claim"]["text"].lower()
            or word in entry["truth"]["text"].lower()
        )

    if word:
        results = [e for e in entries if match(e)]
    else:
        results = entries

    return jsonify(results)





# =============================
# 调试接口
# =============================
@app.route("/cache_status")
def cache_status():
    status = {
        "cache_enabled": os.environ.get("ENABLE_CACHE", "true").lower() == "true",
        "manga_cache_size": len(manga_text_cache),
        "interview_cache_size": len(interview_text_cache)
    }
    return jsonify(status)

@app.route("/ping")
def ping():
    return jsonify({"status": "alive", "timestamp": int(time.time())})

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "")
    return jsonify({"answer": f"暂未接入 LLM，收到问题：{question}"})

# =============================
# 启动检查 + 启动服务
# =============================
if __name__ == "__main__":
    from utils.startup_check import startup_check
    startup_check()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
