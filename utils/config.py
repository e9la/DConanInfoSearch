# config.py
import os

MANGA_TEXT_DIR = "data/submodule_data/纯文本/日文"
INTERVIEW_DATA_DIR = "data/interviews/raw"
PROCESSED_DATA_DIR = "data/interviews/processed"
LOG_DIR = "./logs"

# 缓存开关
ENABLE_CACHE = os.environ.get("ENABLE_CACHE", "true").lower() == "true"