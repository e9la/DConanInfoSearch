let currentMode = "japanese";
const modeInput = document.getElementById("mode");
const resultList = document.getElementById("results");
const descriptionBox = document.getElementById("mode-description");
const volumeFilterContainer = document.getElementById("volume-filter-container");
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
</ul>`.trim(),
  debunk: `
🔍 当前模式：<strong>真伪考据专区</strong><br>
・收录网络广为传播但出处不明的图文资料<br>
・查证语录、截图、采访是否真实
`.trim()
};

document.getElementById("tab-japanese").addEventListener("click", () => switchMode("japanese"));
document.getElementById("tab-interview").addEventListener("click", () => switchMode("interview"));
document.getElementById("tab-debunk").addEventListener("click", () => switchMode("debunk"));

function switchMode(mode) {
  currentMode = mode;
  modeInput.value = mode;
  descriptionBox.innerHTML = modeDescriptions[mode];
  document.querySelectorAll(".tab-bar button").forEach(btn => btn.classList.remove("active"));
  document.getElementById("tab-" + mode).classList.add("active");
  resultList.innerHTML = "";

  // ✅ 动态添加 / 移除卷号输入框
  volumeFilterContainer.innerHTML = "";
  if (mode === "japanese") {
    const input = document.createElement("input");
    input.type = "text";
    input.name = "volume_filter";
    input.id = "volume-filter";
    input.placeholder = "（可选）填写卷号";
    volumeFilterContainer.appendChild(input);
  }

  sourceFilter.style.display = "none";
  if (mode === "interview") loadInterviewSources();
  if (mode === "debunk") {
    fetch("/debunk_search", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ word: "" })
    })
      .then(res => res.json())
      .then(data => renderDebunkResults(data, ""));
  }
}

function renderDebunkResults(data, word) {
  resultList.innerHTML = "";

  if (!Array.isArray(data) || data.length === 0) {
    resultList.innerHTML = `<div class='no-result'>未找到包含「${word}」的结果。</div>`;
    return;
  }

  data.forEach(({ title, claim, truth }) => {
    const card = document.createElement("div");
    card.className = "debunk-card";

    const titleEl = document.createElement("h3");
    titleEl.textContent = title;
    card.appendChild(titleEl);

    const inner = document.createElement("div");
    inner.className = "debunk-inner";

    const scrollable = document.createElement("div");
    scrollable.className = "debunk-scrollable";

    const claimDiv = document.createElement("div");
    claimDiv.className = "debunk-claim";
    const claimHeader = document.createElement("h4");
    claimHeader.textContent = "📌 流传说法";
    claimDiv.appendChild(claimHeader);
    if (claim.note) {
      const note = document.createElement("p");
      note.innerHTML = `<em>${claim.note}</em>`;
      claimDiv.appendChild(note);
    }
    claim.text.split("\n").forEach(line => {
      const p = document.createElement("p");
      p.textContent = line;
      claimDiv.appendChild(p);
    });
    (claim.images || []).forEach(img => {
      const i = document.createElement("img");
      i.src = img;
      i.className = "debunk-image";
      claimDiv.appendChild(i);
    });
    (claim.links || []).forEach(link => {
      if (link) {
        const li = document.createElement("li");
        li.innerHTML = `<a href="${link}" target="_blank">${link}</a>`;
        const ul = claimDiv.querySelector("ul") || document.createElement("ul");
        ul.appendChild(li);
        claimDiv.appendChild(ul);
      }
    });

    const truthDiv = document.createElement("div");
    truthDiv.className = "debunk-truth";
    const truthHeader = document.createElement("h4");
    truthHeader.textContent = "✅ 考据结论";
    truthDiv.appendChild(truthHeader);
    if (truth.note) {
      const note = document.createElement("p");
      note.innerHTML = `<em>${truth.note}</em>`;
      truthDiv.appendChild(note);
    }
    truth.text.split("\n").forEach(line => {
      const p = document.createElement("p");
      p.textContent = line;
      truthDiv.appendChild(p);
    });
    (truth.images || []).forEach(img => {
      const i = document.createElement("img");
      i.src = img;
      i.className = "debunk-image";
      truthDiv.appendChild(i);
    });
    (truth.links || []).forEach(link => {
      if (link) {
        const li = document.createElement("li");
        li.innerHTML = `<a href="${link}" target="_blank">${link}</a>`;
        const ul = truthDiv.querySelector("ul") || document.createElement("ul");
        ul.appendChild(li);
        truthDiv.appendChild(ul);
      }
    });

    inner.appendChild(claimDiv);
    inner.appendChild(truthDiv);
    scrollable.appendChild(inner);
    card.appendChild(scrollable);

    const overlay = document.createElement("div");
    overlay.className = "debunk-overlay";

    const toggleBtn = document.createElement("button");
    toggleBtn.textContent = "展开";
    toggleBtn.className = "debunk-toggle";

    toggleBtn.addEventListener("click", () => {
      card.classList.toggle("expanded");
      toggleBtn.textContent = card.classList.contains("expanded") ? "收起" : "展开";
    });

    overlay.appendChild(toggleBtn);
    card.appendChild(overlay);

    resultList.appendChild(card);
  });
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

  let endpoint = "";
  let body = {};

  if (currentMode === "japanese") {
    endpoint = "/search";
    body = { word, volume_filter: volume };
  } else if (currentMode === "interview") {
    endpoint = "/interview_search";
    body = { word, source_filter: source };
  } else if (currentMode === "debunk") {
    endpoint = "/debunk_search";
    body = { word };
  }

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
  } else if (currentMode == "interview") {
    // 略
  } else if (currentMode === "debunk") {
    renderDebunkResults(data, word);
  }
});

document.addEventListener("DOMContentLoaded", () => {
  switchMode("japanese");
});
