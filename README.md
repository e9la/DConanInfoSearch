# DConanInfoSearch

一个为《名侦探柯南》粉丝打造的开放式信息检索平台。

本项目致力于收集、整理并结构化柯南的幕后访谈与漫画文本，构建一个支持关键词搜索和问答的网页应用，帮助粉丝高效定位资料内容。

---

## 🚀 功能简介

- **关键词检索：**
  - 支持搜索漫画日文原文，定位某个关键词首次或集中出现的位置。
  - 支持搜索访谈资料，展示关键词出现次数、出处链接、上下文片段。

- **问答验证（可选）**
  - 首页支持答题验证（题库可选加载），用于限制访问搜索功能。
  - 若本地未配置题库，则默认跳过验证直接进入搜索界面。

---

## 📁 项目结构概览

```
.
├── app.py                 # 主程序入口
├── templates/             # 网页模板目录（HTML）
├── static/                # 静态资源目录（CSS/JS）
├── scripts/               # 数据爬取与处理脚本
├── utils/                 # 各类辅助工具函数
│   ├── quiz_utils.py      # 题库加载与首页答题逻辑
│   ├── search_utils.py    # 文本检索核心逻辑
│   ├── interview_sources.py # 访谈元信息指路
│   └── ...
└── data/                  # 可选的数据目录（如漫画文本、访谈原文等）
```

---

## 🛠 本地运行

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/DConanInfoSearch.git
cd DConanInfoSearch
```

### 2. 安装依赖

推荐使用 Python 3.9+

```bash
pip install -r requirements.txt
```

### 3. 本地运行网站

```bash
python app.py
```

默认打开 http://10.0.0.94:7860

---

## 💬 可选题库支持

### 开启答题验证（线上版默认启用）

首页答题功能需要加载本地 `quiz_bank.json` 或环境变量 `QUIZ_BANK_JSON`。题库为 JSON 数组，格式如下：

```json
[
  {
    "question": "工藤新一第一次出场是在第几话？",
    "answer": "1"
  },
  ...
]
```

如果未设置本地文件或环境变量，网站将自动跳过验证，直接放行。

---

## 🤝 如何贡献

### 想参与但不知做什么？

1. 浏览已有的 [Issues](https://github.com/e9la/DConanInfoSearch/issues)
2. 将建议或问题提交为issue
3. 留言认领一个 issue，避免重复劳动

### 贡献流程

```bash
# Fork 本仓库
# 克隆到本地
git clone https://github.com/你的用户名/DConanInfoSearch.git

# 创建新分支
git checkout -b feature/xxx

# 开发 + 提交 + 推送
git commit -m "添加 xxx 功能"
git push origin feature/xxx

# 提交 Pull Request
```

---

### ⚠️ 重要说明

漫画文本数据通过 Git 子模块管理，存放于私有仓库，  
因此**本地运行时如果未正确初始化和拉取该子模块，漫画文本检索功能将不可用**。  
访谈资料搜索功能不受影响，依然可以正常使用。

如果需要完整体验漫画文本检索，建议确保已初始化并更新子模块，或者部署到支持访问私有仓库的服务器环境（如 Render）。

---

## 📌 声明

本项目所有资料均来自公开互联网，仅供非商业学术与粉丝整理使用。如涉及版权问题请联系删除。

---

## 🌐 在线体验（开发中）

> 尝试预览地址：  
> https://dconaninfosearch.onrender.com

---

## ✅ TODO（规划中）

- [ ] 集成向量数据库，实现基于语义的问答系统（RAG）
- [ ] 支持 LLM 问答，基于 OpenAI API、Deepseek、Gemini 等平台
- [ ] 多轮对话支持与回答出处追踪
- [ ] 设立“辟谣”模块，方便粉丝了解与辨识

