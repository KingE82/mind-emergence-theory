# Claude-Mem 深扒报告（thedotmack/claude-mem）

> 抓取于 2026-08-03。来源：GitHub API + raw README + docs `.mdx`（database / hooks / search-architecture / progressive-disclosure / context-engineering）+ `mem-search/SKILL.md`。
> 数据：89,345 stars / 7,778 forks / Apache-2.0 / JavaScript+TypeScript / v13.4.0 / 活跃更新（2026-08-02 刚 push）。

---

## 一、它到底是什么

**Agent 跨会话持久上下文记忆引擎。** 典型工作流：
- 自动捕获 agent 每个会话的工具调用（PostToolUse）+ 用户提示词（UserPromptSubmit）
- 用 AI（Claude Agent SDK）把原始动作**压缩成结构化"观察记录"（observation）**和**会话摘要（summary）**
- 存到本地 SQLite + Chroma 向量库
- 下一次会话**启动时自动注入**相关性最高的过去上下文
- 通过 MCP 工具/`mem-search` skill 做按需检索

它其实是 "记忆 Agent harness"，同时针对 Claude Code / OpenClaw / Codex / Copilot / Gemini 等多个 agent 做了。

---

## 二、核心机制（关键）

### 1. 5 个生命周期 Hook（最重要的设计）
| Hook | 触发点 | 作用 |
|---|---|---|
| SessionStart | 会话打开 | 启动 worker + 注入过往上下文（`additionalContext`，静默） |
| UserPromptSubmit | 用户提交提示词 | 幂等建/取 session、递增 prompt 计数、存 user_prompt、去隐私标签 |
| PostToolUse | 每个工具调用后 | 跳过列表（TodoWrite/AskUserQuestion 等噪音）→ 洗掉 `<private>` 标签 → fire-and-forget 发给 worker |
| Stop | 用户暂停/问完 | 从 transcript 提取首尾消息 → 异步生成摘要 |
| SessionEnd | 会话结束 | 优雅标记完成（不强行杀 worker，等 pending 处理完） |

**关键模式**：Hook → HTTP 到本地 worker，**2 秒 timeout、fire-and-forget、绝不阻塞主 agent**。AI 压缩在 worker 里异步排队处理。

### 2. 存储：SQLite + FTS5 + Chroma（不是靠文件）
- **SQLite**（bun:sqlite）：`~/.claude-mem/claude-mem.db`
  - `sdk_sessions` 会话表、`observations` 观察记录表、`session_summaries` 摘要表、`user_prompts` 原始提示词表
  - **FTS5 全文检索虚拟表** + INSERT/UPDATE/DELETE 触发器自动同步
  - observation 结构化字段：`title/subtitle/narrative/text/facts/concepts/type/files_read/files_modified/created_at`
  - observation 类型：decision / bugfix / feature / refactor / discovery / change
- **Chroma 向量库**：语义检索（hybrid keyword+semantic）

### 3. 上下文注入（SessionStart）
worker 按 `project` 取最近 50 条 observation → 生成**紧凑索引 markdown** 注入下一个会话。不是全量历史，而是"目录+成本"。

### 4. 检索：Progressive Disclosure 三层工作流（token 省 10 倍）
- **L1 `search`**：紧凑索引，~50-100 tokens/条，只给 ID/标题/时间/类型
- **L2 `timeline`**：锚定观测前后的时间线上下文
- **L3 `get_observations`**：只对筛选后的 ID 取全文，~500-1000 tokens/条
- 强制规则：**先过滤再取全文**，给 agent 明确的检索成本信号

### 5. 概念亮点
- **隐私控制**：`<private>...</private>` 标签——被包住的内容不入库（还有 `<claude-mem-context>` 引导标签）
- **skip 列表**：识别低价值噪音工具，不浪费 token
- **Compaction（压实）**：上下文快满时用 AI 压缩历史，保留关键决策/bug/实现
- **模式/语言**：`CLAUDE_MEM_MODE`（code 默认 / code--zh 中文等）控制观察措辞语言

---

## 三、与 OpenClaw Memory 体系对比

| 维度 | Claude-Mem | OpenClaw（MEMORY.md + memory/*.md + memory_search） |
|---|---|---|
| 捕获方式 | **全自动**（hook 抓每次工具调用+提示词） | 半自动（AGENTS.md 引导手动"写文件"；记忆要主动写） |
| 压缩 | **AI 自动把原始动作压成结构化 observation** | 手工/人工 curate，无自动提取 |
| 存储 | SQLite 结构化 + FTS5 + 向量 | 纯 markdown 文本文件 |
| 注入 | **会话启动自动静默注入**目录 | memory_search 按需语义检索，不自动注入 |
| 遗忘/衰减 | 靠搜索过滤 + 阈值；无显式遗忘 | 无显式遗忘机制 |
| 相关性 | 时间+类型+向量 hybrid | 语义向量（memory_search 有） |
| 成本 | 三层渐进披露，token 省 10 倍 | 单次语义检索，缺少"索引先于全文" |
| 幂等/会话 | session+project 幂等关联，多 prompt 延续 | 无会话级结构 |

**结论：claude-mem 强在三点，OpenClaw 缺**
1. **全自动捕获 + AI 压缩**：OpenClaw 靠人工写 memory 文件，claude-mem 是钩子自动抓工具轨迹、AI 压成结构化观察。
2. **自动注入**：SessionStart 静默把上次的"目录"塞进新会话，OpenClaw 只提供按需检索。
3. **Progressive Disclosure 三层检索**：先给索引(低成本)→过滤→取全文，OpenClaw 检索一次性返回全文，缺"成本感知"。

**OpenClaw 反超的点**：OpenClaw 用内存级语义检索（`memory_search` 有向量 index、`memory_get` 精确读片段），且 markdown 人工可读可改、干净；claude-mem 是二进制 SQLite + 本地 daemon（node/bun+chroma），重且黑盒。

---

## 四、可移植进 OpenClaw 的思想（不靠装它的 daemon）

### ① 会话结束自动摘要（AI 压缩）
每次主会话结束/中途，用模型把今天的 `memory/YYYY-MM-DD.md` + 会话要点，**自动蒸馏成结构化 observation**（做成"决策/修的bug/发现/下一步"四段）。这是它最值的机制——把 raw log 变成可检索的 knowledge，而不是纯手写。

### ② SessionStart 自动注入"索引目录"
开新会话时，主动/由 HEARTBEAT 生成一页**紧凑索引**（过去 N 天按主题/标签，约 100 行内），供启动时扫一眼——比"搜不到就忘了"强。对应 claude-mem 的 context-hook + progressive disclosure index。

### ③ 三层检索成本意识
给 memory_search 上层套规则：先标题/摘要(索引层)→命中再 `memory_get` 读全文。省 token，比一次性全文灌入好。可在 AGENTS.md 里写"先索引后全文"的检索 SOP。

### ④ 结构化工具体（observation schema）
把 memory 记成带字段的小块（`title/type/context/next_steps`），而不是长篇流水账——让 `memory_search` 命中率更高、更可压缩。参考它 observation 的五种 type。

### ⑤ 隐私标签 + skip 列表
`<private>` 不记忆、敏感话题跳过，对应 AGENTS.md 的"不泄露私密数据"红线，做成软规则防误录。

### ⑥ 幂等会话延续
会话按 (session/project) 幂等归组，多 prompt 归属同一会话再排 prompt 号——OpenClaw 可给每条记忆记 context 标签，避免重复入库。

---

## 五、精华总结（150-300 字）

Claude-Mem 是 agent 跨会话记忆引擎（8.9 万星）：用 5 个生命周期 hook 全自动捕获每次工具调用和用户提示词，AI 把原始动作异步压成结构化 observation 和会话摘要，存进 SQLite+FTS5 全文检索 + Chroma 向量。核心设计：**fire-and-forget 不阻塞主 agent**、SessionStart 静默注入"紧凑目录"、Progressive Disclosure 三层检索（先索引→时间线→过滤后取全文，token 省 10 倍）、`<private>` 隐私标签与噪音工具 skip 列表。相比 OpenClaw 的 MEMORY.md+memory_search：它赢在**全自动捕获+AI压缩+自动注入+渐进披露**；OpenClaw 赢在人工可读可改、语义检索轻量、无 daemon 负担。不必照搬其重 SQLite/Chromadaemon，可移植其思想强化 OpenClaw 记忆。

---

## 六、可落地建议（openclaw 侧）

1. **会话结束自动摘要**：主会话收尾时跑一次模型，把 `memory/YYYY-MM-DD.md` 自动蒸馏成「做的/决策/修的bug/发现/下一步」结构化 nugget，落盘，供 memory_search 检索（替代纯手写）。
2. **SessionStart 注入"索引目录"**：开新会话先看过去若干天 memory 的紧凑索引（标签+标题，100 行内），再决定深挖——把"按需搜索"升级为"启动即知情"。
3. **三层渐进披露 SOP**：memory 检索先出标题/摘要，命中再用 `memory_get` 读全文；把这条写成 AGENTS.md/HEARTBEAT.md 检索规则，省 token。
4. **结构化记忆模板 + 隐私纪律**：记忆按「title/type/一句话/文件引用」小块记；敏感内容标 `<private>` 不落盘，红线前置。
5. **幂等归组**：记忆按主题/项目打 context 标签去重，避免跨会话重复入库，提升命中精度。

---
*注：README 说它已支持 OpenClaw（`curl install.cmem.ai/openclaw.sh` 作为持久记忆 plugin）。未实测本地安装，仅从源码/文档提取分析。*
