"""
章节 5.1 · 把 RAG 包成生产级 HTTP 服务（FastAPI + 5.4 数据层）
==========================================================
本节把命令行问答包装成 HTTP 服务边界；真实交付还需认证、部署和运行验收。

"能返回答案"只是及格线。一个能上生产的 LLM 服务还必须回答四个问题：
  ① 出问题了怎么查？        → trace_id 贯穿请求、日志、数据库
  ② 上游挂了服务会不会死？  → 启动降级 + 异常兜底，永远不裸奔 500
  ③ 这个月花了多少钱？      → 每次请求落库 token / cost / latency（章节 5.4）
  ④ 答得好不好？            → /feedback 收集点赞点踩 → 导评测集 → 回归测试

所以本文件在最简版（只有 /chat + /health）之上补齐：
  /chat      问答，并把 trace_id / 耗时 / token / 成本 / 引用来源全部落库
  /feedback  用户点赞点踩 —— 数据飞轮的入口
  /stats     按天的请求数 / 失败率 / 成本 / p95 —— 一句 SQL 出运营看板
  /history   按用户查历史（游标分页）
  /health    存活探针（不查依赖，永远秒回）
  /ready     就绪探针（查依赖，没准备好就返回 503）

  /chat/stream  同一个问答的 SSE 流式版本：先发 trace_id，再逐段发文本，最后发 usage 与来源

前置：2.6（RAG 检索）、5.2（超时与带抖动的重试）；本章使用 5.4 的 sqlite_persistence 保存问答记录，先当黑盒用，5.4 再详细讲
依赖：fastapi、uvicorn；原生 openai SDK 调用真实模型（DEEPSEEK_API_KEY）和本地 embedding 模型
运行：python tools/run_chapter.py 5.1 run_server.py [--host 0.0.0.0] [--port 8000]
调试：浏览器打开 http://127.0.0.1:8000/docs
==========================================================
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import common
import sqlite_persistence as store
from common import SAMPLE_DOC
from reliability import call_with_retry  # 5.2：只重试瞬时错误，带抖动

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("support.api")

DOC_PATH = os.getenv("RAG_DOC_PATH", str(SAMPLE_DOC))

# ---- 成本单价：示例值，务必换成你模型的真实价格 ----
# 单位：美元 / 100 万 token。价格会变，所以做成环境变量可覆盖，
# 而不是写死在代码里——线上调价时不用重新发版。
PRICE_IN = float(os.getenv("PRICE_IN_PER_M", "0.27"))
PRICE_OUT = float(os.getenv("PRICE_OUT_PER_M", "1.10"))


# ============================================================
# 【一】RAG 链：一次检索同时拿到 答案 + 来源 + token 用量
# ============================================================
# 生产要把"答案 + 来源 + token 用量"一起落库，所以直接用原生客户端：
# 响应里自带 usage，检索到的文档也由我们自己拿着，不需要额外框架对象。
# 注意只检索【一次】：先 retriever.invoke 再拼 prompt，不要为了拿来源再查一遍。

PROMPT = """
你是严谨的知识库助手。请依据下面的上下文回答问题：
- 只要有相关信息（哪怕只是部分），就基于它尽量回答，并在结尾用【来源】标注出处；
- 只有完全没有相关信息时，才回答"文档中没有提到"。

上下文：
{context}

问题：
{question}
"""


def _format_docs(docs) -> str:
    parts = []
    for d in docs:
        src = d.metadata.get("source", "未知")
        page = d.metadata.get("page")
        tag = f"[来源：{src}" + (f" 第{page}页]" if page else "]")
        parts.append(f"{tag}\n{d.page_content}")
    return "\n\n".join(parts)


def _doc_ref(d) -> str:
    """把文档压成一个可追溯的短标识，存进 sources 字段。"""
    src = d.metadata.get("source", "未知")
    page = d.metadata.get("page")
    return f"{src}#p{page}" if page is not None else str(src)


def _messages(docs, question: str) -> list[dict]:
    return [{"role": "user", "content": PROMPT.format(context=_format_docs(docs), question=question)}]


def build_answer_fn(retriever, client, model: str):
    """返回一个 answer(question) -> dict 的可调用对象。

    拆成工厂函数是为了【可测】：测试时传一个假 retriever / 假 client 进来，
    整条接口链路不碰真 LLM 也能跑。
    超时在客户端上设（common.get_openai_client(timeout=...)）；
    重试只在这一层做（客户端的 max_retries 保持 0，避免两层重试相乘）。
    """
    def answer(question: str) -> dict:
        docs = retriever.invoke(question)
        resp = call_with_retry(lambda: client.chat.completions.create(
            model=model, messages=_messages(docs, question)))
        usage = resp.usage
        return {
            "answer": resp.choices[0].message.content or "",
            "sources": [_doc_ref(d) for d in docs],
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        }
    return answer


def build_stream_fn(retriever, client, model: str):
    """返回 stream(question) -> 生成器，逐个产出 ("delta", 文本) 或 ("done", 汇总字典)。

    原生 stream=True；stream_options.include_usage 让最后一块带上 token 用量。
    建立连接这一步可以重试（还没有任何内容发给用户）；
    一旦开始产出文本就不能重试，否则用户会看到重复内容。
    """
    def stream(question: str):
        docs = retriever.invoke(question)
        chunks = call_with_retry(lambda: client.chat.completions.create(
            model=model, messages=_messages(docs, question),
            stream=True, stream_options={"include_usage": True}))
        parts: list[str] = []
        usage = None
        for chunk in chunks:
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                parts.append(chunk.choices[0].delta.content)
                yield "delta", chunk.choices[0].delta.content
        yield "done", {
            "answer": "".join(parts),
            "sources": [_doc_ref(d) for d in docs],
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        }
    return stream


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        prompt_tokens / 1_000_000 * PRICE_IN
        + completion_tokens / 1_000_000 * PRICE_OUT,
        8,
    )


# ============================================================
# 【二】启动：lifespan + 优雅降级
# ============================================================
# 原版把 build_retriever 写在模块顶层。三个问题：
#   1. 建库失败 → 整个模块 import 失败 → 服务根本起不来，日志还很难看
#   2. uvicorn --reload 每次改代码都重新 embedding 一遍，开发体验极差
#   3. 没有对应的关闭动作（连接、线程池都没地方清理）
# 生产写法是 lifespan：yield 之前是启动，之后是关闭。
# 并且【建库失败不让进程退出】——服务照常起、/health 正常、/ready 返 503，
# 运维能看到"服务活着但没就绪"，而不是面对一个反复重启的容器。

STATE: dict = {"answer_fn": None, "stream_fn": None, "error": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.migrate()                      # 建表 / 升级 schema，幂等
    log.info("数据库就绪：%s", store.DB_PATH)
    try:
        from pdf_sources import build_retriever
        retriever = build_retriever(DOC_PATH)
        client = common.get_openai_client(timeout=20.0, max_retries=0)
        model = common.chat_model_name()
        STATE["answer_fn"] = build_answer_fn(retriever, client, model)
        STATE["stream_fn"] = build_stream_fn(retriever, client, model)
        STATE["model"] = model
        log.info("知识库就绪：%s", DOC_PATH)
    except Exception as e:               # noqa: BLE001
        STATE["error"] = str(e)
        log.error("知识库构建失败，服务以未就绪状态启动：%s", e)
    yield
    store.close_conn()
    log.info("服务关闭")


app = FastAPI(title="RAG 知识库问答服务", version="2.0", lifespan=lifespan)

# 前端跨域调用必须开 CORS。生产把 allow_origins 收窄成你的域名，别用 "*"。
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 【三】中间件：trace_id 贯穿全链路
# ============================================================
# 用户来投诉"刚才那个回答不对"，你要能立刻定位到那一次请求。
# 做法：每个请求生成 trace_id → 写进响应头 → 写进日志 → 存进数据库。
# 三处用同一个 id，出事时一秒对上号。这是可观测性最低成本的一步。
@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = int((time.perf_counter() - t0) * 1000)
    response.headers["X-Trace-Id"] = trace_id
    log.info("%s %s -> %s %dms trace=%s",
             request.method, request.url.path, response.status_code, elapsed, trace_id)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    """兜底异常处理：绝不把堆栈吐给用户，但要留下 trace_id 让自己能查。"""
    trace_id = getattr(request.state, "trace_id", "-")
    log.exception("未处理异常 trace=%s", trace_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务内部错误", "trace_id": trace_id},
        headers={"X-Trace-Id": trace_id},
    )


# ============================================================
# 【四】请求/响应模型：把校验挡在业务代码之前
# ============================================================
# Field 的约束不是装饰：max_length 直接挡住"超长 prompt 打爆成本"这类
# 最常见的滥用，而且 FastAPI 会自动返回 422 + 清晰错误，不用自己写 if。
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000, description="用户问题")
    user_id: str = Field(default="anonymous", max_length=64)
    session_id: str | None = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    conversation_id: int          # 前端拿它提交反馈
    trace_id: str
    latency_ms: int


class FeedbackRequest(BaseModel):
    conversation_id: int
    rating: int = Field(description="1=赞, -1=踩")
    comment: str | None = Field(default=None, max_length=500)


# ============================================================
# 【五】接口
# ============================================================
@app.get("/health")
def health():
    """存活探针（liveness）：只证明进程还在，不查任何依赖，永远秒回。

    为什么不查依赖：liveness 失败 k8s 会【重启容器】。
    如果这里查数据库，数据库抖一下就会引发一轮无意义的重启风暴。
    """
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """就绪探针（readiness）：查依赖，没好就返 503 —— 流量不会打进来。

    liveness 管"要不要重启"，readiness 管"要不要给流量"，
    分开是 k8s 部署的基本功。
    """
    if STATE["answer_fn"] is None:
        raise HTTPException(503, detail=f"知识库未就绪：{STATE['error']}")
    return {"status": "ready", "doc": DOC_PATH}


# 注意这里是 def 而不是 async def —— 这是【故意的】。
# RAG 调用是同步阻塞的（网络 IO + 本地 embedding）。写成 async def 会把它
# 直接跑在事件循环线程上，一个慢请求就卡死【所有】并发请求。
# 写成普通 def，FastAPI 会自动丢进线程池执行，不阻塞事件循环。
# 配合 章节 5.4 的 thread-local 连接：线程池默认 40 线程 = 最多 40 个 SQLite
# 连接，可控且被复用，正好接上 章节 5.4 讲的"连接不能每次新建也不能全局共享"。
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    trace_id = request.state.trace_id
    answer_fn = STATE["answer_fn"]
    if answer_fn is None:
        raise HTTPException(503, detail="知识库未就绪，请稍后重试")

    session_id = req.session_id or f"{req.user_id}:default"
    t0 = time.perf_counter()
    try:
        result = answer_fn(req.question)
    except Exception as e:                       # noqa: BLE001
        # 关键：失败【也要落库】。只记成功的话，失败率永远是 0%，
        # /stats 会给你一个岁月静好的假象。失败样本才是改进的原料。
        latency = int((time.perf_counter() - t0) * 1000)
        store.save_qa(
            trace_id=trace_id, user_id=req.user_id, session_id=session_id,
            question=req.question, answer="", status="error",
            error=f"{type(e).__name__}: {e}"[:500], latency_ms=latency,
        )
        log.error("RAG 调用失败 trace=%s: %s", trace_id, e)
        raise HTTPException(502, detail="上游模型调用失败，请稍后重试") from e

    latency = int((time.perf_counter() - t0) * 1000)
    cost = estimate_cost(result["prompt_tokens"], result["completion_tokens"])
    conversation_id = store.save_qa(
        trace_id=trace_id, user_id=req.user_id, session_id=session_id,
        question=req.question, answer=result["answer"],
        model=STATE.get("model", ""),
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        cost_usd=cost, latency_ms=latency, sources=result["sources"],
    )
    return ChatResponse(
        answer=result["answer"], sources=result["sources"],
        conversation_id=conversation_id, trace_id=trace_id, latency_ms=latency,
    )


def _sse(event: str, data: dict) -> str:
    """SSE 帧：event 行 + data 行 + 空行。ensure_ascii=False 让中文可读。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, request: Request):
    """SSE 流式问答。事件顺序：meta（trace_id）→ delta（多次）→ done（来源、耗时）或 error。

    流结束后才落库——和 /chat 一样，成功和失败都记。
    trace_id 同时在响应头 X-Trace-Id 和第一个 meta 事件里，前端断流时也能拿到它去报障。
    """
    trace_id = request.state.trace_id
    stream_fn = STATE["stream_fn"]
    if stream_fn is None:
        raise HTTPException(503, detail="知识库未就绪，请稍后重试")
    session_id = req.session_id or f"{req.user_id}:default"

    def events():
        t0 = time.perf_counter()
        yield _sse("meta", {"trace_id": trace_id})
        try:
            for kind, payload in stream_fn(req.question):
                if kind == "delta":
                    yield _sse("delta", {"text": payload})
                    continue
                latency = int((time.perf_counter() - t0) * 1000)
                cid = store.save_qa(
                    trace_id=trace_id, user_id=req.user_id, session_id=session_id,
                    question=req.question, answer=payload["answer"], model=STATE.get("model", ""),
                    prompt_tokens=payload["prompt_tokens"], completion_tokens=payload["completion_tokens"],
                    cost_usd=estimate_cost(payload["prompt_tokens"], payload["completion_tokens"]),
                    latency_ms=latency, sources=payload["sources"],
                )
                yield _sse("done", {"conversation_id": cid, "sources": payload["sources"], "latency_ms": latency})
        except Exception as e:  # noqa: BLE001
            latency = int((time.perf_counter() - t0) * 1000)
            store.save_qa(
                trace_id=trace_id, user_id=req.user_id, session_id=session_id,
                question=req.question, answer="", status="error",
                error=f"{type(e).__name__}: {e}"[:500], latency_ms=latency,
            )
            log.error("流式 RAG 调用失败 trace=%s: %s", trace_id, e)
            # 响应头已经发出（200），只能在流里告知前端；只给 trace_id，不给堆栈
            yield _sse("error", {"trace_id": trace_id, "message": "上游模型调用失败"})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """收集用户点赞/点踩 —— 整个服务里最便宜、最有价值的一个接口。

    攒下来的踩 → store.export_eval_set() 导成评测集 → 章节 5.8 pytest 回归
    → 7.6 / step1 的 CI 门禁。自己编的用例永远不如线上真实翻车的问题有价值。
    """
    try:
        fid = store.save_feedback(req.conversation_id, req.rating, req.comment)
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e
    except Exception as e:                       # noqa: BLE001
        # 外键约束拦下了不存在的 conversation_id（章节 5.4 里 foreign_keys=ON 才生效）
        raise HTTPException(404, detail="对话不存在") from e
    return {"feedback_id": fid}


@app.get("/stats")
def stats(days: int = 7):
    """运营看板：按天的请求数 / 失败率 / 成本 / 平均与 p95 延迟。

    生产上这个接口要加鉴权（见 capstone/auth.py），别裸奔对外。
    """
    return {"days": days, "rows": store.daily_stats(days)}


@app.get("/history")
def history(user_id: str, limit: int = 20, before_id: int | None = None):
    """按用户查历史，游标分页（章节 5.4 讲过为什么不用 OFFSET）。"""
    return {"items": store.get_history(user_id, limit=limit, before_id=before_id)}


# ----------------------------------------------------------
# 小结：
# 0. SSE 一旦开始发送，状态码就已经是 200：中途失败只能在流里发 error 事件，
#    并且重试只能发生在"尚未向用户输出任何内容"之前。
# 1. 启动逻辑放 lifespan，不放模块顶层：依赖挂了服务仍能起，/ready 返 503，
#    运维看到的是"活着但未就绪"，而不是一个反复重启的容器。
# 2. liveness(/health) 与 readiness(/ready) 必须分开：前者管重启、后者管流量，
#    /health 里绝不能查数据库，否则依赖一抖就是重启风暴。
# 3. trace_id 三处一致（响应头 + 日志 + 数据库），用户一投诉就能定位到那一次。
# 4. 阻塞型 LLM 调用用 def 不用 async def，让 FastAPI 丢进线程池，
#    否则一个慢请求卡死整个事件循环。
# 5. 成功和失败【都要落库】。只记成功 = 失败率永远 0%，等于没有监控。
# 6. Pydantic 的 max_length 是第一道成本防线，挡住超长 prompt。
# 7. 兜底 exception_handler 只回 trace_id，不回堆栈（堆栈泄漏是安全问题）。
# 8. /feedback 是数据飞轮入口：点踩 → 评测集 → 回归测试 → CI 门禁。
#
# 本文件不重复造的部分（各有归属，别平行造第二套）：
# - 超时 / 带抖动的重试 / 主备切换 → 5.2 的 call_with_retry / chat_with_fallback，已在上面用了
# - 鉴权 / 限流 / 文档级权限 → capstone/auth.py、capstone/permissions.py
# - 流式的 Agent 事件与审批 → 4.11；本章只做最小的 RAG 文本流
# - 容器化与部署 → 5.5、7.6 / step2
#
# 动手练习：用 locust（7.7 / step2 容量与压测）压 /chat，观察 /stats 里的 p95 怎么变；
#           再把并发调到线程池上限以上，看请求是排队还是超时。
# ----------------------------------------------------------
