# P07 项目二 — 阶段 2A：可复现 RAG 语料库 + Chunking + BM25 评测

目标：把原来只有 5 篇、431 字符的内存知识库，升级为**独立、可追踪、带检索真值标签的合成文档数据集**。不覆盖 P07 原来的 `DOCS`、`search_docs`、`agent_mvp.py` 或 Structured Trace。

## 如何安装（WSL）

在 `~/projects/data_engineering_book/code/zh/project_7_agent_tooluse` 中：

```bash
unzip -o P07_RAG_corpus_phase2a.zip
python3 -m unittest discover -s tests -p 'test_rag_phase2a.py' -v
python3 scripts/run_rag_phase2a.py
python3 scripts/inspect_rag_failures.py
```

全部使用 Python 标准库；**不需要下载 Embedding 模型、启动 Qdrant、配置 API Key，也不会调用 Qwen**。

## 产出

- `data/rag/documents.jsonl`：120 篇合成业务文档，含 `doc_id`, `domain`, `brand`, `topic`, `effective_date`, `version`, `content_sha256` 等元数据。
- `data/rag/chunks.jsonl`：基于字符/段落边界的分块结果，保留 `chunk_id`、`start_char` 和 `end_char`，保证每一段文本可精确定位到源文档。
- `data/rag/questions.jsonl`：240 条中英文双语检索查询，含 `gold_doc_ids`、`expected_answer`、`split`。
- `data/rag/corpus_manifest.json`：版本哈希、数据量、切分规则及 Chunk 参数。
- `data/rag/bm25_dev_report.json`：开发集 60 条查询上的 Recall@1/5、MRR@10 与逐题 Top-5。
- `scripts/inspect_rag_failures.py`：查看开发集中没有排到 Top-1 的查询，后续分析向量检索可能弥补的缺陷。

## 如何理解数据

- 数据均由确定性规则合成，**不是真实公司的政策信息**；邮箱使用 `example.invalid`。
- 24 个虚构品牌 × 5 类文档（退货、续费、席位、支持、安全）= 120 篇文档；5 类任务 × 中英文 2 种问法 = 240 条标注查询。
- 训练/开发/测试按照 **品牌实体**分组，确保同一个品牌不跨分割；train/dev/test 查询各 120/60/60。
- 生成器固定模板与问题形式，**不同品牌的切分并不能证明真正的 OOD 泛化**。开发集适合调试；测试集要冻结后才用于最终汇报。
- BM25 分词是简单 Latin 正则 + 中文 bigram，不是成熟中文分词器；标题加权只是小规模基线。查询和文档共享生成模板，分数可能偏乐观。
- `Recall@K` 当前按**文档 ID**判断：检索到目标文档任一 Chunk 就算命中。后续可增加真正的 Chunk-level 标注和 grounded-answer 验证。

## Structured Trace 衔接

运行后取得 `index_version`：

```bash
export P07_INDEX_VERSION=$(python3 -c 'import json; print(json.load(open("data/rag/corpus_manifest.json"))["index_version"])')
echo "$P07_INDEX_VERSION"
```

版本哈希包含语料内容、Chunk 大小/重叠、分块算法和 BM25 基线版本。当前这只是**未来实验的版本标识**：它不会自动把原版 Agent `search_docs` 连接到新语料库；真正的接入应在下一阶段统一检索器接口完成。

## 下一阶段（2B）

1. 使用多语言 Embedding 模型生成每个 Chunk 的 Dense Vector。
2. 将 Chunk 文本、向量、Metadata 持久化到 Qdrant。
3. 在同一语料和标注查询上比较 BM25、Dense 和 Hybrid（RRF）。
4. 实现与 P07 `search_docs(query, domain, top_k)` 兼容的 Retrieval Adapter，添加 `doc_id/chunk_id` 证据到 Structured Trace。
5. 最后在相同模型、相同提示词和相同查询上测 Agent 端到端效果，再引入 LangGraph；不要同时改变检索与编排。

Qdrant 官方资料：https://qdrant.tech/documentation/search/hybrid-queries/ ；本补丁尚未安装/调用 Qdrant。
