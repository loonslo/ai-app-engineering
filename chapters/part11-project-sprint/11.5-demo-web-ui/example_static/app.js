// 零依赖的最小前端：调用 POST /chat 与 POST /feedback（约定见 ../README.md）。
// 你的服务字段不同时，只需要改下面的 adaptChatResponse。
"use strict";

const API_BASE = "";  // 同源（由 FastAPI 的静态文件服务提供）。跨域部署时填 "https://你的域名"。

const $ = (id) => document.getElementById(id);
let lastConversationId = null;

// 把服务返回的 JSON 适配成页面使用的结构。
function adaptChatResponse(data) {
  return {
    answer: String(data.answer ?? ""),
    sources: Array.isArray(data.sources) ? data.sources.map(String) : [],
    conversationId: data.conversation_id ?? null,
    traceId: data.trace_id ?? "",
    degraded: Boolean(data.degraded),
    needsHuman: Boolean(data.needs_human),
  };
}

// 按状态码给出可读的错误信息；不显示服务端堆栈，只给 trace_id 以便报障。
function explainError(status, traceId) {
  const suffix = traceId ? `（trace_id：${traceId}）` : "";
  if (status === 401 || status === 403) return "没有访问权限：请检查 API key。" + suffix;
  if (status === 422) return "问题不符合要求：请检查长度（1–1000 字）。" + suffix;
  if (status === 429) return "请求太频繁，请稍后再试。" + suffix;
  if (status === 503) return "服务暂时没有准备好，请稍后再试。" + suffix;
  if (status >= 500) return "服务出错了，请稍后再试；若持续出现，请把 trace_id 发给维护者。" + suffix;
  return `请求失败（HTTP ${status}）。` + suffix;
}

function headers() {
  const h = { "Content-Type": "application/json" };
  const key = $("key").value.trim();
  if (key) h["Authorization"] = `Bearer ${key}`;  // key 只存在输入框里，不写入 localStorage
  return h;
}

function showError(message) {
  $("error").textContent = message;
  $("error").hidden = false;
}

function clearError() {
  $("error").hidden = true;
  $("error").textContent = "";
}

function renderResult(r) {
  const badges = $("badges");
  badges.replaceChildren();
  if (r.degraded) {
    const b = document.createElement("span");
    b.className = "badge degraded";
    b.textContent = "已降级：本次回答可能不如平时可靠";
    badges.append(b);
  }
  if (r.needsHuman) {
    const b = document.createElement("span");
    b.className = "badge human";
    b.textContent = "建议转人工：请联系维护者确认";
    badges.append(b);
  }
  $("answer").textContent = r.answer;  // textContent：不把服务返回的内容当 HTML 解析
  const list = $("sources");
  list.replaceChildren();
  if (r.sources.length === 0) {
    const li = document.createElement("li");
    li.textContent = "无引用";
    list.append(li);
  }
  for (const s of r.sources) {
    const li = document.createElement("li");
    li.textContent = s;
    list.append(li);
  }
  $("trace").textContent = r.traceId;
  $("feedback-note").hidden = true;
  $("up").disabled = $("down").disabled = r.conversationId === null;
  lastConversationId = r.conversationId;
  $("result").hidden = false;
}

async function ask() {
  const question = $("question").value.trim();
  if (!question) { showError("请先输入问题。"); return; }
  clearError();
  $("ask").disabled = true;           // 提交中禁用，防止重复提交
  $("status").textContent = "思考中…";
  try {
    const resp = await fetch(`${API_BASE}/chat`, { method: "POST", headers: headers(), body: JSON.stringify({ question }) });
    const traceId = resp.headers.get("X-Trace-Id") || "";
    if (!resp.ok) { showError(explainError(resp.status, traceId)); return; }
    renderResult(adaptChatResponse(await resp.json()));
  } catch (err) {
    showError("网络连接失败：请检查网络或服务是否在线。");  // 不显示 err.message
  } finally {
    $("ask").disabled = false;
    $("status").textContent = "";
  }
}

async function sendFeedback(rating) {
  if (lastConversationId === null) return;
  const note = $("feedback-note");
  try {
    const resp = await fetch(`${API_BASE}/feedback`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({ conversation_id: lastConversationId, rating }),
    });
    note.textContent = resp.ok ? "已收到反馈，谢谢。" : "反馈没有提交成功：" + explainError(resp.status, "");
  } catch (err) {
    note.textContent = "反馈没有提交成功：网络连接失败。";
  }
  note.hidden = false;
}

$("ask").addEventListener("click", ask);
$("up").addEventListener("click", () => sendFeedback(1));
$("down").addEventListener("click", () => sendFeedback(-1));
