# 文件: app.py
import os
import time
import re
import random
import json
import zipfile

from flask import Flask, request, redirect, render_template, make_response, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from utils.interview_sources import get_interview_metadata
from utils.config import MANGA_TEXT_DIR, INTERVIEW_DATA_DIR
from utils.cache_utils import init_manga_cache, init_interview_cache, manga_text_cache, interview_text_cache
from utils.search_utils import count_word_in_documents, word_expand

from utils.quiz_utils import load_quiz_bank

# Flask init
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "your-secret-key"

# Rate limit
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

# Quiz bank init
quiz_bank = load_quiz_bank()

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
    base_dir = INTERVIEW_DATA_DIR
    results = []

    if not word:
        return jsonify(results)

    file_data = interview_text_cache if os.environ.get("ENABLE_CACHE", "true").lower() == "true" else {}
    if not file_data:
        init_interview_cache()
        file_data = interview_text_cache

    for rel_path, text in file_data.items():
        try:
            meta = get_interview_metadata(rel_path)
            if source_filter and meta["source"] != source_filter:
                continue

            words = word_expand(word)
            for word in words:
                count = text.count(word)
                if count > 0:
                    sentences = re.split(r'[\u3002！？\n]', text)
                    snippets = [f"...{s.strip()}..." for s in sentences if word in s][:3]
                    results.append({
                        "file": rel_path,
                        "count": count,
                        "source": meta["source"],
                        "url": meta["url"],
                        "snippets": snippets
                    })
        except Exception as e:
            print(f"❌ Error processing {rel_path}: {e}")

    results.sort(key=lambda x: -x["count"])
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
