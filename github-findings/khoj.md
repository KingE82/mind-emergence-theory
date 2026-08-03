# 深扒 GitHub 项目：khoj-ai/khoj — AI 第二大脑

> 抓取方式：raw.githubusercontent.com + GitHub API（git tree）+ 官方 docs 源码（documentation/docs）。README（master 分支）✅ 抓取成功；docs 页源码 12 篇核心文档 ✅ 抓取；源码关键文件（text_search.py / text_to_entries.py / models）✅ 抓取。
> 数据时间戳：2026-08-03。已建目录 github_findings/khoj_docs/ 留存原始抓取。

---

## 一、概况

**Khoj（Khoj AI）= "Your AI second brain"——自托管的个人 AI 检索问答引擎。** 当前版本是「从 on-device 个人 AI 平滑扩容到 cloud-scale 企业 AI」的产品化 RAG 服务。

- **星数**：36k ⭐ / 协议 **AGPL-3.0** / 语言 Python（后端）+ TypeScript/React（前端）
- **一句话定位**：对你的笔记/文档做向量索引 + RAG，用自然语言聊、搜、找答案；支持纯本地（Ollama/GGUF）+ 商业模型（OpenAI/Anthropic/Gemini）
- **形态**：Django + FastAPI 服务器（默认 `localhost:42110`），**多端客户端**——Web、Obsidian 插件、Emacs、桌面 App、Whatsapp、Android
- **周边生态**：`khoj-ai/pipali`（付费 AI 同事桌面端，闭源商业模式）
- **第二大脑的本质**：不是记忆系统，是**「个人文档语义搜索引擎 + 基于索引的聊天助手」**——你把资料喂给它，它建好向量索引，你用自然语言检索/问答。

---

## 二、核心机制（深挖源码后）

### 1. 数据来源（能索引什么）
`processor/content/` 下按文件类型明确的解析器（EntryType 枚举）：
- **Markdown / Org-mode / Plaintext / PDF / DOCX / 图片（OCR）** — 本地文件
- **Notion pages**（notion_to_entries）、**GitHub repos**（github_to_entries）— 集成源
- **网页**（在线搜索/网页阅读，走 requests/Serper/Firecrawl/Exa/Olostep）
- **对话记忆**（EntryType.CONVERSATION）+ **UserMemory**（长期记忆表）
- 索引方式：每种来源一个 `*_to_entries.py` 解析器 → 转成统一 `Entry`（raw + compiled + heading + 文件路径 + url + 行号）→ 落库里。

### 2. 检索技术栈（核心，业内教科书级 RAG）
- **向量库**：PostgreSQL + **pgvector**（`Entry.embeddings = VectorField`），另有 `torch.save` 的 `.pt` 嵌入文件用于持久化。**不是** Chroma/FAISS/Qdrant。
- **Embedding（bi-encoder）**：`sentence-transformers` 模型（本地从 HuggingFace 下载，或走 OpenAI/任何 OpenAI 兼容 API）。默认本地模型免配置。
- **Rerank（cross-encoder）**：检索出 top_k=10 后用 **cross-encoder 重排**、再做相关性排序——这是比普通向量检索准得多的关键一步。
- **Chunking**：`RecursiveCharacterTextSplitter`（langchain），按 段落>句子>词>字符 切，`max_tokens=256`，**chunk 自动补 heading 前缀 + 记录精确行号**（`#line=`）——保证引用能跳回原文位置。
- **检索流程**：bi-encoder 把 query 编码 → `search_with_embeddings`（pgvector 距离检索，带 `bi_encoder_confidence_threshold` 置信阈值）→ cross-encoder 重排 → dedupe → 带引用（source/file/uri/heading）返回。
- **异步 + 计时**：全程 `asgiref.sync_to_async` + timer，性能有人管。

### 3. "自动每日笔记 / automated daily notes"
**源码里没有独立的 daily-notes 自动笔记功能。** 任务里提到的这个点对应的是：
- **Automations（自动化）**：按 crontab 定时跑查询，结果**发邮件**（周报/每日摘要/新闻/事件提醒）。自托管需配 Resend + 认证。
- **UserMemory**：从对话中**提炼长期记忆**存表（pgvector 向量化），这是它最接近"持续记忆"的东西。
- 结论：**"自动生成每日笔记"本身不存在**——它做的是「定时跑检索 + 结果推送」，不是「自动写 markdown 笔记」。这是与 Obsidian 类工具协作时才有的习惯（用户自己用 daily note 模板）。

### 4. 部署形态 / 资源 / 本地模型
- **两种装法**：Docker（`docker-compose.yml`，带 PostgreSQL）或 `pip install 'khoj[local]'`（[local] 含 GGUF 本地模型）。
- **本地离线要求**：最少 **8GB RAM，推荐 16GB VRAM，≥5GB 磁盘**，NVIDIA/AMD GPU 或 M1+ 显著加速。纯 CPU 也能跑但慢。
- **接本地模型**：✅ 支持 Ollama（走 OpenAI 兼容 API `http://localhost:11434/v1/`）、llama.cpp、vLLM、LMStudio；也可直接跑 HuggingFace GGUF。搜索 embedding 也可本地 sentence-transformers。
- **默认反向代理安全**：默认只绑 localhost；远程要设 `KHOJ_DOMAIN`/`KHOJ_NO_HTTPS`/尾网等。
- 背后：Django admin 面板配模型/数据源；`ServerChatSettings` 管中间模型（意图识别/网页搜索都用它）。

### 5. 与 Obsidian / 本地 Markdown 集成
- 官方 **Obsidian 插件**（community plugin `khoj`）：安装后设 Khoj URL + API key，**自动周期同步整个 vault**（或 Force Sync），侧边栏做 Chat/Search/**相似笔记**。
- **本地 Markdown**：桌面客户端/拖拽上传解析 markdown；检索结果每条带**原文行号 **，可跳回。
- Emacs、Web、桌面 App 同理。多端都是连同一个服务器。

---

## 三、与我们的 /kx 知识库（knowledgex_vault + kx_retriever.py）对比

| 维度 | Khoj | 我们 /kx（knowledgex_vault + kx_retriever） |
|---|---|---|
| 定位 | 全套产品：服务器+UI+多端+聊天 | 轻量知识库检索组件 |
| 检索 | bi-encoder(a) → pgvector → **cross-encoder 重排** | 向量检索（通常单段，无 cross-encoder 重排，若未见则无） |
| 引用溯源 | heading + **精确行号** + 文件 URL | 未知（评估时确认是否带出处/行号） |
| 部署体积 | 重：Django+PostgreSQL+pip 一堆依赖 | 轻：单脚本/文件库 |
| 模型 | 本地或云端均可，可 Ollama | 视 kx_retriever 而定 |
| 多端 | Web/Obsidian/Emacs/桌面/Whatsapp | 站点内 /kx 接口 |
| 协议 | **AGPL-3.0** | 自有 |
| 记忆 | UserMemory 从对话提炼 | 无 |

**Khoj 强项（值得借鉴）**
1. **两阶段检索（bi-encoder 召回 + cross-encoder 重排）**——单向量检索的上限提升最明显，且重排只在 top_k 上跑，成本可控。
2. **chunk 保留 heading + 精确行号**——回答/检索能精确引用到原文位置，信任感强。
3. **增量索引 + 按 SearchModel 粒度**——只对新 entry 建向量，改 embedding 模型才全重建，省算力。
4. **query filter（word/file/date filter）**——检索可限定来源，精准过滤。
5. **统一 Entry 模型 + 多格式解析器管线**——扩展新来源（org/pdf/notion/github）只需加一个解析器。

**我们更轻 / Khoj 不必要的地方**
- 我们的场景（一个站点的 /kx 检索）**不需要** Kafka 级别的服务、多用户认证、Dashboard、Whatsapp 集成。引入 Khoj = 引入 Django 后台 + PostgreSQL + 一堆它自带但用不到的组件。
- Khoj 是「完整产品」，不是「检索库」；我们只需要「检索这一件」。

---

## 四、落地建议

### 引入完整 Khoj（替换 /kx）
- **成本（高）**：Django + PostgreSQL + OpenCV/PyPDF/langchain/torch/sentence-transformers 全家桶；启动一个常驻服务(42110 端口)；至少 8GB 内存倾向；**AGPL-3.0 协议务实风险**——`kx_retriever.py` 若从 Khoj 抄代码/引用其内部逻辑，需整套代码开源（AGPL 传染到网络服务），这是最大的雷。
- **收益**：一步到位拿到成熟 RAG + 多端 + 自动邮件推送。**但**与我们"站内 /kx 轻量检索"的定位错配，多数功能用不上。
- **结论**：**不建议整体替换**，除非我们真要做一个独立的、多用户、多端的第二大脑产品。

### 更优路径：只借鉴设计（推荐）
1. **给 kx_retriever 加 cross-encoder 重排层**：检索 top_k（如 10-20）后用一个小 cross-encoder 重排再给前端。收益最大、改动最小、保持轻量。可用 sentence-transformers 或国产 embedding+rerank API。
2. **chunk 记录精确行号 + heading 前缀**：让我们 /kx 的生成结果能带"原文位置跳转"，提升可信任度。
3. **增量索引**：只对新文件建向量，不每次全量重建，省时省算力（Khoj 的 `id == -1` 天判断模式可直接学）。
4. **query 过滤**：支持 `file:xxx` / `word:xxx` / `date:xxx` 语法，用户可限定搜索范围。
5. **统一数据源解析器管线**：若将来要加 PDF/网页/Notion，按 Entry + 解析器模式扩展，别写死文件格式。

> ⚠️ 协议提醒：全程**只看不动用其代码**的话无协议问题；一旦复制 Khoj 实现（哪怕改变量名），AGPL-3.0 要求衍生作品以 AGPL 开源并公开源码。借鉴"思想/架构设计"（如两阶段检索、heading+行号）不受影响；若要借鉴，建议自己从零实现核心，不引入外部服务依赖。

---

## 五、精华总结（150-300 字）

Khoj（3.6 万星，AGPL-3.0，Python）是"自托管 AI 第二大脑"——一个成熟的文档语义检索 + RAG 聊天产品。核心机制是**教科书级两阶段检索**：bi-encoder(sentence-transformers)把文档 chunk 向量化存进 PostgreSQL+pgvector，查询时召回 top_k=10，再用 **cross-encoder 重排**提高精度；chunk 由 langchain 切分、自动补 heading 前缀并记录**精确行号**用于引用溯源；支持增量索引、query 过滤、Ollama/GGUF 本地模型、多端（Web/Obsidian/Emacs/桌面）。所谓"自动每日笔记"实为 **Automations**（crontab 定时跑检索发邮件），不是自动写笔记。相比我们的轻量 /kx：它强在**重排 + 行号引用 + 增量索引 + 统一解析器管线**，但整体是 Django+Postgres 的重产品，与站内轻量检索定位错配。**不建议整套替换**；应借鉴其两阶段检索和精确定位设计。

---

## 六、可落地建议（针对 /kx 轻量增强）

1. **加 cross-encoder 重排层**：检索先召回 top 10-20，再用小 rerank 模型重排，是性价比最高的精度提升（成本只在 top_k 上）。
2. **chunk 补 heading + 行号**：生成结果带"原文位置跳转"，增强可信任度与可用性。
3. **增量索引**：只对新文件建嵌入，模型不变不重建，省时省算力。
4. **query 过滤语法**：支持 file/word/date 限定范围，参考 Khoj 的 query-filters。
5. **统一数据源解析器管线**：用 Entry + 解析器插件式扩展 PDF/网页/Notion，而不是写死格式 —— 让以后扩容不伤筋动骨。

---
*注：整套 Khoj 未本地实测运行，仅从 GitHub 源码 + docs 源码提取分析。若真考虑引入，建议先在隔离环境 `docker-compose` 起一个试用，并重点评估 AGPL-3.0 对自有代码的影响。*
