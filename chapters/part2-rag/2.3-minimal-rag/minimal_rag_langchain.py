"""
章节 2.3 · 最小 RAG：把检索和生成串成完整问答
==========================================================
2.1 切块、2.2 向量化检索。本章补上最后一步：把"检索到的内容"交给模型，
让它基于这些内容回答，文档没有答案时说"不知道"。这就是一个完整的最小 RAG。

知识点：
1. retriever：把向量库包装成"可插拔的检索器"，还能用 MMR 提升结果多样性
2. 用 LCEL 把 检索 → 拼接 → 提示 → 模型 → 取文本 串成一条链
3. RunnableParallel（字典写法）和 RunnablePassthrough 是怎么配合的
4. 怎么用 prompt 抑制幻觉（没检索到就拒答）

前置：2.2；DEEPSEEK_API_KEY；本地 embedding 模型
运行：python tools/run_chapter.py 2.3（调用真实模型，会产生少量费用）
输出：四个问题的回答，其中最后一个资料外问题应回答"我不知道"
==========================================================
"""

import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from common import EMBED_MODEL_PATH, SAMPLE_DOC

load_dotenv()

# ---------- 1. 建库：加载 → 切割 → 向量化（2.1 + 2.2 的合并）----------
# 加载用 open() + Document，避开 langchain_community 里 TextLoader 的弃用警告
with open(SAMPLE_DOC, encoding="utf-8") as f:
    text = f.read()
docs = [Document(page_content=text, metadata={"source": SAMPLE_DOC.name})]

splitter = RecursiveCharacterTextSplitter(
    chunk_size=120, chunk_overlap=20,
    separators=["\n\n", "\n", "。", "，", " ", ""],
)
chunks = splitter.split_documents(docs)

embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_PATH)   # 路径见 common.py
# 将文档切片进行向量化，构建FAISS向量索引，封装成vectorstore
vectorstore = FAISS.from_documents(chunks, embeddings)


# ---------- 2. 检索器：这次用 MMR 提升多样性 ----------
# as_retriever 把向量库标准化成可插拔的检索组件。
# search_type="mmr"（最大边际相关性）：先粗取 fetch_k 条候选，再在"相关性"和
#   "多样性"之间权衡挑出 k 条，避免召回的几块内容高度重复、信息冗余。
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 3,               # 最终返回 3 条
        "fetch_k": 10,        # 先取 10 条候选再筛
        "lambda_mult": 0.5,   # 1=只看相关性，0=只看多样性，0.5 居中
    },
)


# 把检索到的多个块拼成一段上下文文本
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# ---------- 3. 提示词：限定"只根据上下文回答"，没答案就拒答（抑制幻觉）----------
prompt = ChatPromptTemplate.from_template("""
你是一个严谨的知识库问答助手。
请只根据下面的上下文回答问题。如果上下文里没有答案，就说：我不知道。

上下文：
{context}

问题：
{question}
""")

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


# ---------- 4. 用 LCEL 组装完整 RAG 链 ----------
# 开头那个字典就是 RunnableParallel（并行）：输入的问题同时走两条路——
#   context 路：问题 → retriever 检索 → format_docs 拼成文本
#   question 路：问题 → RunnablePassthrough() 原样透传
# 两路汇成 {"context": ..., "question": ...}，再依次进 prompt → llm → 取纯文本。
rag_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)


# ---------- 5. 测试：3 个文档相关问题 + 1 个无关问题（验证拒答）----------
questions = [
    "RAG 是什么？",
    "Embedding 是干嘛的？",
    "FAISS 有什么作用？",
    "本节天气怎么样？",   # 文档里没有 → 应该回答"我不知道"
]
for q in questions:
    print("=" * 40)
    print("问题：", q)
    print("回答：", rag_chain.invoke(q))


# ----------------------------------------------------------
# 小结：一个完整 RAG = 检索（找相关块）+ 生成（基于块回答）
# - MMR 让召回的块更多样、信息更全
# - 字典写法 = RunnableParallel 并行，RunnablePassthrough 负责原样透传问题
# - "没答案就说不知道"这条 prompt 指令能有效抑制幻觉，是 RAG 质量的关键
#
# 下一步：2.4 起为 RAG 建立评测集，量化答错率和幻觉率，并做回归测试。
# ----------------------------------------------------------
