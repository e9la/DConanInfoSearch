let currentMode = "japanese";
const modeInput = document.getElementById("mode");
const resultList = document.getElementById("results");
const descriptionBox = document.getElementById("mode-description");
const volumeFilter = document.getElementById("volume-filter");
const sourceFilter = document.getElementById("source-filter");

const modeDescriptions = {
  japanese: `📘 当前模式：<strong>漫画文本检索</strong><br>・仅搜索漫画原文（持续更新中）<br>・仅支持日文全词匹配（不支持模糊搜索）<br>・可填写卷号进行过滤`,
  interview: `
🗣️ 当前模式：<strong>访谈资料检索</strong><br>
<ul style="padding-left: 1em; margin: 0;">
  <li>作者访谈、花絮、幕后整理内容</li>
  <li>点击卡片可跳转至访谈详情页</li>
  <li>目前收录信息：
    <ul style="padding-left: 1em;">
      <li><a href="https://www.sbsub.com/posts/category/interviews/" target="_blank">银色子弹访谈整理</a></li>
      <li><a href="https://bbs.aptx.cn/thread-296846-2-1.html" target="_blank">名侦探柯南事务所论坛访谈整理</a></li>
      <li><a href="https://www.detectiveconanworld.com/wiki/Interviews" target="_blank">名侦探柯南维基百科</a></li>
      <li>其他访谈文字记录</li>
      <li>部分访谈视频</li>
      <li><a href="https://ameblo.jp/megumi--hayashibara/entrylist.html" target="_blank">林原惠美博客</a></li>
    </ul>
  </li>
</ul>
`.trim()
};



document.getElementById("tab-japanese").addEventListener("click", () => switchMode("japanese"));
document.getElementById("tab-interview").addEventListener("click", () => switchMode("interview"));

function switchMode(mode) {
  currentMode = mode;
  modeInput.value = mode;
  descriptionBox.innerHTML = modeDescriptions[mode];
  document.querySelectorAll(".tab-bar button").forEach(btn => btn.classList.remove("active"));
  document.getElementById("tab-" + mode).classList.add("active");
  resultList.innerHTML = "";
  volumeFilter.style.display = (mode === "japanese") ? "block" : "none";
  sourceFilter.style.display = "none";
  if (mode === "interview") loadInterviewSources();
}

async function loadInterviewSources() {
  const res = await fetch("/interview_sources");
  const data = await res.json();
  sourceFilter.innerHTML = `<option value="">📂 全部来源</option>`;
  data.forEach(src => {
    const opt = document.createElement("option");
    opt.value = src;
    opt.textContent = src;
    sourceFilter.appendChild(opt);
  });
}

document.getElementById("search-form").addEventListener("submit", async function (e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const word = formData.get("word").trim();
  const volume = formData.get("volume_filter") || "";
  const source = formData.get("source_filter") || "";

  const endpoint = currentMode === "japanese" ? "/search" : "/interview_search";
  const body = currentMode === "japanese" ? { word, volume_filter: volume } : { word, source_filter: source };

  resultList.innerHTML = "";

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(body)
  });

  const data = await res.json();
  if (!Array.isArray(data) || data.length === 0) {
    resultList.innerHTML = `<div class='no-result'>未找到包含「${word}」的结果。</div>`;
    return;
  }

  if (currentMode === "japanese") {
    data.forEach(({ volume, count, pages }) => {
      const div = document.createElement("div");
      div.textContent = `📄「${word}」在第 ${volume} 卷中出现了 ${count} 次，位于第 ${pages.join("、")} 页`;
      div.style.marginBottom = "1em";
      resultList.appendChild(div);
    });
  } else {
    data.forEach(({ id, title, count, sources, snippets }) => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.border = "1px solid #ccc";
      card.style.borderRadius = "8px";
      card.style.marginBottom = "1.5em";
      card.style.backgroundColor = "#fff";
      card.style.cursor = "pointer";
      card.addEventListener("click", () => {
        const encodedKw = encodeURIComponent(word);
        window.open(`/interview_detail/${id}?kw=${encodedKw}`, "_blank");
      });


      const header = document.createElement("div");
      header.textContent = title;
      header.style.backgroundColor = "#e2ecf8";
      header.style.padding = "0.8em 1em";
      header.style.fontWeight = "bold";
      header.style.fontSize = "1.05em";
      card.appendChild(header);

      const body = document.createElement("div");
      body.style.padding = "1em";

      // ✅ 替换为来源信息
      const metaLine = document.createElement("p");
      const sourceCount = sources.length;
      metaLine.innerHTML = `📁 本访谈整理自 <strong>${sourceCount}</strong> 个来源`;
      metaLine.style.marginBottom = "0.5em";
      body.appendChild(metaLine);

      snippets.forEach(snippet => {
        const p = document.createElement("p");
        p.innerHTML = snippet.replace(new RegExp(word, "g"), `<mark>${word}</mark>`);
        p.style.lineHeight = "1.6";
        body.appendChild(p);
      });

      card.appendChild(body);
      resultList.appendChild(card);
    });
  }
});
