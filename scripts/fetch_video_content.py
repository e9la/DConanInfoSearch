import os
import requests

from datetime import timedelta
from utils.constants import INTERVEW_DATA_DIR, PROCESSED_DATA_DIR

bv_json_url_map = {
    "BV1Ju411b7kb": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/prod/53043272911831779509d78f9ae92f4282416488971c532d912?auth_key=1752233623-56cb5b87091b4796979deede3c04971e-0-211f70e1a614aecdd74b14f4f620a210",
    "BV1zzZtYAE9p": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/prod/11426201809950929179644574089c229a070bbf33e57cb1d310e563ef?auth_key=1752235072-22e0fe298b44437d9241dd6313f622da-0-13c4e8f981697c9a00aae289ff6b",
    "BV17e4y137yk": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/prod/6482554009114618983148defc5371c71efb3fa305f1c9f301?auth_key=1752235212-78b7d4e3a6a340b0bf454c5eab14e9f0-0-7d14690e651c17e1223a87aec03d1778",
    "BV1m24y1T7Dd": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/prod/7834016751124503138b6674960b4b3a7f068f32145a5c74bab?auth_key=1752235291-8e5ff29471c44c44a19b1d18679e6aab-0-4426b33307ec4d6b6201be150e356207",
    "BV1zzZtYAE9p": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/prod/11426201809950929179644574089c229a070bbf33e57cb1d310e563ef?auth_key=1752235356-39f8c5f791794190856cde9fb385c784-0-1bb9aa6d3f07362a9f9a1ff2e3ad3",
    "BV1wYVdzLEsZ": "https://aisubtitle.hdslb.com/bfs/ai_subtitle/prod/114483158581395298895951552cfc03bb2423457f88c17106151e0e5d?auth_key=1752235405-c6e0e785e26a431aaa270d7f4736ba26-0-f31fc80e832a968179e3955f7d96477c",
    # 添加更多...
}

def format_time(seconds):
    """将秒数转成 HH:MM:SS.ss 格式"""
    td = timedelta(seconds=seconds)
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"

def get_video_title(bvid):
    """从 B 站 API 获取视频标题，失败就回退用 bvid"""
    api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com",
    }
    try:
        resp = requests.get(api, headers=headers)
        resp.raise_for_status()
        json_data = resp.json()
        title = json_data.get("data", {}).get("title", "")
        if title:
            print(f"🎬 [{bvid}] 视频标题: {title}")
            return title
        else:
            print(f"⚠️ [{bvid}] 未能提取标题，用 BV 号代替")
            return bvid
    except Exception as e:
        print(f"⚠️ [{bvid}] 获取标题失败: {e}")
        return bvid


def download_and_save_subtitles(bvid, json_url, output_dir="subtitles_txt"):
    """下载 JSON 并保存为带时间的 TXT"""
    try:
        resp = requests.get(json_url)
        resp.raise_for_status()
        body = resp.json().get("body", [])

        lines = []
        for seg in body:
            start = format_time(seg["from"])
            end = format_time(seg["to"])
            content = seg["content"]
            lines.append(f"[{start} - {end}] {content}")

        title = get_video_title(bvid)
        safe_title = "".join(c if c.isalnum() or c in " _-[]" else "_" for c in title)
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"[{bvid}]{safe_title}.txt")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✅ [{bvid}] 保存成功: {out_path}")
    except Exception as e:
        print(f"❌ [{bvid}] 处理失败: {e}")

if __name__ == "__main__":
    for bv, url in bv_json_url_map.items():
        download_and_save_subtitles(
            bv, url,
            output_dir = os.path.join(INTERVIEW_DATA_DIR, "bilibili_subtitles"))
        
        
        
        
