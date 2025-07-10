# DConanInfoSearch 数据处理说明

本项目为《名侦探柯南》相关访谈内容的检索网站，后端使用 Flask，数据来自多个来源的 `.txt` 文件和压缩包，需统一清洗、聚合和去重。

---

## 📁 项目结构

```
DConanInfoSearch/
├── scripts/
│   ├── crawler_bilibili.py          # 示例爬虫
│   ├── crawler_magazine.py          # 示例爬虫
│   └── merge_and_dedup.py           # 🔁 聚类合并核心脚本
│
├── utils/
│   └── config.py                    # 📦 存放目录路径配置
│
├── data/
│   ├── raw/                         # 📥 所有原始 txt 与 zip 数据放在这里（多个来源）
│   └── processed/
│       └── merged_interviews.json  # ✅ 合并后的标准数据格式
│
├── app.py                           # Flask 主程序
├── templates/
├── static/
└── README.md
```

---

## 📦 安装依赖

请确保你已安装以下包（建议使用虚拟环境）：

```bash
pip install sentence-transformers scikit-learn numpy
```

---

## 🚀 如何运行聚合处理脚本

在项目根目录运行（**不是 scripts 目录！**）：

```bash
python scripts/merge_and_dedup.py
```

该脚本将：

1. 遍历 `data/raw/` 文件夹中的所有 `.txt` 与 `.zip`
2. 提取文本内容
3. 使用语义向量聚类（SentenceTransformer）
4. 自动判断重复访谈并合并
5. 生成 `data/processed/merged_interviews.json`

---

## 🕓 定时自动更新数据（可选）

你可以设置定时任务，自动执行以下步骤：

1. 运行爬虫更新数据源（例如爬 B 站、SUNDAY 杂志）
2. 合并并去重所有新数据

### 方案 1：使用 crontab（Linux/macOS）

```bash
crontab -e
```

添加如下内容（每天凌晨 2 点运行）：

```cron
0 2 * * * /path/to/venv/bin/python /your/project/scripts/crawler_bilibili.py
5 2 * * * /path/to/venv/bin/python /your/project/scripts/crawler_magazine.py
10 2 * * * /path/to/venv/bin/python /your/project/scripts/merge_and_dedup.py
```

### 方案 2：使用 Makefile 一键运行所有脚本

创建项目根目录下的 `Makefile`：

```makefile
update_all:
	python scripts/crawler_bilibili.py
	python scripts/crawler_magazine.py
	python scripts/merge_and_dedup.py
```

然后在终端运行：

```bash
make update_all
```

---

## 🧠 配置模块说明（可选）

你可以将路径常量写入 `utils/config.py` 中，供多个脚本调用：

```python
# utils/config.py
INTERVIEW_DATA_DIR = "./data/raw"
PROCESSED_DATA_DIR = "./data/processed"
```

在 `merge_and_dedup.py` 中使用：

```python
from utils.config import INTERVIEW_DATA_DIR, PROCESSED_DATA_DIR
```

并在脚本顶部加一行确保模块路径正确解析：

```python
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

---

## ✅ 输出数据格式说明

合并后的 JSON 文件（`merged_interviews.json`）结构如下：

```json
[
  {
    "id": "interview_1",
    "title": "自动生成访谈_1",
    "content": "……访谈正文……",
    "sources": [
      "data/raw/bilibili/fileA.txt",
      "data/raw/zip/fileB.zip:fileB.txt"
    ]
  },
  ...
]
```

此文件会被 Flask 网站用于搜索与展示。

---

## ✨ 后续可扩展

- 手动编辑访谈标题或标签（如作者、年份等）
- 将内容送入向量数据库做问答（如 OpenAI Embedding + FAISS）
- 为每条访谈生成摘要或关键词
