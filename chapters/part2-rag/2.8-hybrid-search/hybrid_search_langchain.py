"""
章节 2.8 · 混合检索：向量 + BM25 关键词
==========================================================
向量检索擅长"语义相近"，但对专有名词、编号、型号这种"必须精确匹配"的词
常常召回不准（比如问"FAISS"，它可能给你一堆"向量库"的近义内容却漏了正主）。
BM25 是经典的关键词检索，正好和向量互补。这节把两者合起来（hybrid）。

知识点：
1. BM25Retriever：基于关键词频率的检索（不靠 embedding）
2. EnsembleRetriever：按权重合并多个检索器的结果
3. 为什么专有名词向量召回差、混合怎么救

依赖：pip install rank_bm25
注意（langchain 1.x）：EnsembleRetriever 已从 langchain.retrievers 迁到 langchain_classic.retrievers。
注意（2026-06）：langchain-community 仓库已归档停维护（官方 issue #674）。BM25Retriever
  暂无独立包，仍从 community 导入可用。迁移方向：
  主流集成 → 各自独立包（langchain-chroma / langchain-openai…），legacy → langchain-classic。

★中文大坑：BM25Retriever 默认按【空格】分词，中文整句会被当成一个 token，
  检索直接失效（本文件因为混了向量检索，坏了也看不出来——这更危险）。
  生产必须传 preprocess_func（jieba 分词或字符 bigram），见下方代码。

前置：2.7；rank_bm25；langchain-classic；本地 embedding 模型
运行：python tools/run_chapter.py 2.8（离线，不调用聊天模型）
输出：同一个问题下，纯向量检索与混合检索各自召回的片段
==========================================================
"""

import os
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from common import LONG_DOC, get_embeddings, ZH_SEPARATORS


def build_retrievers(path=LONG_DOC):
    """建三种检索器：纯向量、纯 BM25、混合。返回 (向量, 混合) 供对比。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    docs = [Document(page_content=text, metadata={"source": os.path.basename(path)})]
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=120, chunk_overlap=20, separators=ZH_SEPARATORS,
    ).split_documents(docs)

    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # 1) 向量检索：靠语义相似度
    vector_ret = vectorstore.as_retriever(search_kwargs={"k": 4})

    # 2) BM25 检索：靠关键词匹配，直接从 chunks 构建，不需要 embedding
    #    ★必须给中文传 preprocess_func：默认按空格分词，中文整句=1 个 token，检索失效。
    #    这里用字符 bigram（零依赖）；要更准可换 jieba.lcut。
    def _tok_zh(text: str) -> list[str]:
        text = "".join(text.split())
        return [text[i:i + 2] for i in range(len(text) - 1)] or [text]

    bm25_ret = BM25Retriever.from_documents(chunks, preprocess_func=_tok_zh)
    bm25_ret.k = 4

    # 3) 混合检索：EnsembleRetriever 把两者结果按权重融合
    #    weights=[0.5, 0.5] 表示两者各占一半，可按场景调（专有名词多就给 BM25 高一点）
    hybrid_ret = EnsembleRetriever(retrievers=[vector_ret, bm25_ret], weights=[0.5, 0.5])
    return vector_ret, hybrid_ret


if __name__ == "__main__":
    vector_ret, hybrid_ret = build_retrievers()

    # 对比：只含一个专有名词的查询，纯向量 vs 混合。
    # 文章里只有一句提到 Sharpe（金融指标），它在语义上和其他句子都不像，向量检索容易漏掉；
    # BM25 按词精确匹配，能直接命中。★ 标出召回结果里含有查询词的片段。
    query = "Sharpe"
    print(f"查询：{query}\n")

    def show(title, retriever):
        docs = retriever.invoke(query)
        print(title)
        for d in docs:
            mark = "★" if query in d.page_content else " "
            print(f" {mark}", d.page_content[:40].replace("\n", " "))
        print(f"  → 含 {query!r} 的片段：{sum(query in d.page_content for d in docs)} 个\n")

    show("【纯向量检索】", vector_ret)
    show("【混合检索（向量 + BM25）】", hybrid_ret)


# ----------------------------------------------------------
# 小结：
# - 向量检索懂语义但对精确词（专有名词/编号）不敏感；BM25 正好补上
# - EnsembleRetriever 按权重融合多路检索；权重要按你的文档/问题类型调
# - 判断要不要混合：如果你的领域有大量型号、缩写、编号，混合通常明显更好
#
# 动手练习：把 query 换成文章里另一个只出现一次的词（如 Obsidian、Milvus），
#          比较纯向量和混合的结果；再把 weights 调成 [0.8, 0.2]，看结果如何变化
# ----------------------------------------------------------
