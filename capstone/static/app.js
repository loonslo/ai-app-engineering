// 零依赖演示前端：调用 POST /v1/chat 与 POST /v1/feedback。
// 状态：degraded（备用模型回答）、status=pending_approval（需要人工审批）、cache_hit（来自缓存）。
"use strict";

const $ = (id) => document.getElementById(id);
let lastRequestId = null;

function adaptChatResponse(data) {
  return {
    answer: String(data.answer ?? ""),
    citations: Array.isArray(data.citations) ? data.citations : [],
    requestId: data.request_id ?? "",
    degraded: Boolean(data.degraded),
    needsHuman: data.status === "pending_approval",
    cacheHit: Boolean(data.cache_hit),
  };
}

// 按状态码给出可读的错误信息；不显示服务端堆栈。
function explainError(status, requestId) {
  const suffix = requestId ? `（request_id：${requestId}）` : "";
  if (status === 401) return "未登录或令牌无效：请先登录。" + suffix;
  if (status === 403) return "没有访问权限。" + suffix;
  if (status === 400 || status === 422) return "问题不符合要求或被安全策略拒绝：请修改后重试。" + suffix;
  if (status === 429) return "请求太频繁，请稍后再试。" + suffix;
  if (status === 503) return "服务暂时不可用，请稍后再试。" + suffix;
  if (status >= 500) return "服务出错了，请稍后再试；若持续出现，请把 request_id 发给维护者。" + suffix;
  return `请求失败（HTTP ${status}）。` + suffix;
}

function headers() {
  const h = { "Content-Type": "application/json" };
  const token = $("token").value.trim();
  if (token) h["Authorization"] = `Bearer ${token}`;  // 令牌只在输入框里，不写入 localStorage
  return h;
}

function showError(message) { $("error").textContent = message; $("error").hidden = false; }
function clearError() { $("error").hidden = true; $("error").textContent = ""; }

function badge(text, cls) {
  const b = document.createElement("span");
  b.className = `badge ${cls}`;
  b.textContent = text;
  return b;
}

function citationText(c) {
  return String(c.source_id ?? "") + (c.page ? ` 第${c.page}页` : "");
}

function renderResult(r) {
  const badges = $("badges");
  badges.replaceChildren();
  if (r.degraded) badges.append(badge("已降级：由备用模型回答，可能不如平时可靠", "degraded"));
  if (r.needsHuman) badges.append(badge("需要人工审批：这是一个待审批的请求，尚未执行", "human"));
  if (r.cacheHit) badges.append(badge("来自缓存", "cache"));
  $("answer").textContent = r.answer;  // textContent：不把服务返回的内容当 HTML 解析
  const list = $("sources");
  list.replaceChildren();
  // 同一来源可能有多个分块被引用，页面上按“来源 + 页码”去重显示
  const items = r.citations.length ? [...new Set(r.citations.map(citationText))] : ["无引用"];
  for (const text of items) {
    const li = document.createElement("li");
    li.textContent = text;
    list.append(li);
  }
  $("request-id").textContent = r.requestId;
  $("feedback-note").hidden = true;
  $("up").disabled = $("down").disabled = !r.requestId;
  lastRequestId = r.requestId || null;
  $("result").hidden = false;
}

async function ask() {
  const question = $("question").value.trim();
  if (!question) { showError("请先输入问题。"); return; }
  clearError();
  $("ask").disabled = true;
  $("status").textContent = "思考中…";
  try {
    const resp = await fetch("/v1/chat", { method: "POST", headers: headers(), body: JSON.stringify({ question }) });
    const requestId = resp.headers.get("X-Request-ID") || "";
    if (!resp.ok) { showError(explainError(resp.status, requestId)); return; }
    renderResult(adaptChatResponse(await resp.json()));
  } catch (err) {
    showError("网络连接失败：请检查网络或服务是否在线。");
  } finally {
    $("ask").disabled = false;
    $("status").textContent = "";
  }
}

async function sendFeedback(rating) {
  if (!lastRequestId) return;
  const note = $("feedback-note");
  try {
    const resp = await fetch("/v1/feedback", {
      method: "POST", headers: headers(), body: JSON.stringify({ request_id: lastRequestId, rating }),
    });
    note.textContent = resp.ok ? "已收到反馈，谢谢。" : "反馈没有提交成功：" + explainError(resp.status, "");
  } catch (err) {
    note.textContent = "反馈没有提交成功：网络连接失败。";
  }
  note.hidden = false;
}

async function devLogin() {
  clearError();
  const user = $("dev-user").value.trim();
  const tenant = $("dev-tenant").value.trim();
  if (!user || !tenant) { showError("开发登录需要用户名和租户。"); return; }
  try {
    const resp = await fetch("/v1/dev-login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: user, tenant, roles: ["employee"] }),
    });
    if (!resp.ok) { showError(resp.status === 404 ? "当前环境没有开启开发登录，请粘贴访问令牌。" : explainError(resp.status, "")); return; }
    $("token").value = (await resp.json()).access_token;
  } catch (err) {
    showError("网络连接失败：请检查服务是否在线。");
  }
}

$("ask").addEventListener("click", ask);
$("up").addEventListener("click", () => sendFeedback(1));
$("down").addEventListener("click", () => sendFeedback(-1));
$("dev-login").addEventListener("click", devLogin);
