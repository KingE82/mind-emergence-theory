# 深扒 GitHub 项目：EverMind-AI/EverOS

> 抓取时间：2026-08-03。来源：main 分支 raw README.md + README.zh-CN.md + `docs/how-memory-works.md` + `docs/storage_layout.md` + `docs/migration-to-1.0.0.md`（curl 全抓成功）。
> 星数：⭐1.2万（任务提供）· Apache-2.0 · Python 3.12+ · 活跃（2026-08 仍在持续演进到 1.0.0 架构）。

---

## 一、它是什么

**"给每个 AI agent 一个便携记忆层"的本地优先记忆运行时（local-first memory runtime），面向 agents 和 makers。**

- **一句话定位**：把 conversations / files / agent trajectories 存成**可读 Markdown（唯一真相源）**，再用本地 SQLite + LanceDB 索引做快速检索和**自进化复用（self-evolving reuse）**。
- **设计哲学**：三层本地栈，**零外部服务**——不需要 MongoDB / Elasticsearch / Redis / Milvus / Kafka；不装 Docker Compose（1.0.0 整体抹掉旧的容器化架构）。
- **运行时形态**：`everos server` HTTP 服务（OpenAI 协议兼容），CLI 叫 `everos demo`（记忆生命周期可视化 TUI：conversation → memory sphere → recall → source proof → confetti）。
- **接入对象**：Claude Code / Codex / OpenCode 等 CLI coding agent、App、设备、工作流——典型用法是给 coding agent 当"跨会话持久上下文层"（`evermemos-mcp` / `evermem-claude-code` 插件）。
- **配套生态（EverMind）**：Raven 自改进 agent harness、EverAlgo 无状态提取算法引擎、HyperMem 超图记忆、EverMemBench/EvoAgentBench 评测、MSA 百万 token 稀疏注意力研究、EverMe 个人记忆层。==> EverOS 是"研究到运行时"的落地核心。

## 二、核心机制（关键）

### 1. "Markdown 唯一真相源"怎么做到？——三层栈 + 可重建索引
这是整份文档的第一卖点，也是与我们最相关的设计：

| 层 | 承载 | 可重建？ |
|---|---|---|
| **Markdown + YAML frontmatter** | 记忆内容本体——唯一可移植、人可编辑的资产 | ——（它**就是**真相） |
| **SQLite**（aiosqlite） | 系统状态、审计日志、cascade 队列（`md_change_state` 表）、boundary buffer、OME 引擎状态 | ✅ 可从 md 重建 |
| **LanceDB**（Arrow） | 向量 + BM25 全文 + 标量列，做检索 | ✅ 可从 md 重建 |

- **一招鲜规则**：`rm -rf .index/` 一条命令删光所有索引，**一条记忆都不丢**——因为索引是派生品，从 `.md` 树重建。**Markdown 本身就是"导出"**，没有单独的 export，也不用手动 reindex。
- **可移植性**：整个 memory-root（默认 `~/.everos/`）就是**一个目录**，可直接 copy / 备份 / 把用户可见部分 checkout 进 git。
- **目录布局**：`<app_id>/<project_id>/` 先分空间（`default` 落盘成 `default_app/default_project`），下分 `users/`、`agents/`、`knowledge/`；`.index/`、`.tmp/` 是系统托管可重建部分（gitignore）。

### 2. 三种"落盘策略"（storage strategies）——组织记忆的骨架
8 种业务记忆 kind，各自挑一种路径模式：

| 策略 | 形状 | 为什么 | 实例 |
|---|---|---|---|
| **Daily-log append** 每日日志追加 | `<prefix>-<YYYY-MM-DD>.md`，每条记忆 append 一条 entry | 把几千个碎文件压成一个"每天一个文件" | episode / atomic_fact / foresight / agent_case |
| **Single-file rewrite** 单文件覆写 | 固定文件名原地覆盖 | 单个**持续演化**的文档 | user profile（`user.md`） |
| **Skill-named dir** 技能目录 | `skills/skill_<name>/SKILL.md`（+ 可选 references/ scripts/） | 技能是更丰富的单元 | agent skills（程序性记忆） |

- **frontmatter 底盘**（每一份 md 都有 YAML）：`id / type / schema_version / user_id 或 agent_id / track(user|agent) / entry_count / last_appended_at`。**scope（app/project）不进 frontmatter，而由路径段承载**——cascade 路径解析器恢复。
- **entry 用 HTML 注释包夹**：`<!-- entry:ep_20260601_00000001 -->…<!-- /entry:... -->`，让原始 markdown 对人类保持干净（VSCode/Obsidian/Vim 直接编辑可用）。entry_id = `前缀_YYYYMMDD_NNNNNNNN`，**按文件内序号而非全局**，跨表 join 必须用 `(owner_id, entry_id)`。
- **原子写语义**：同目录临时文件 + `os.replace`，POSIX 原子 rename。

### 3. 用户轨迹 vs Agent 轨迹"双轨"——episodes/profile vs cases/skills
**核心创新点：把"关于用户的记忆"和"agent 干过什么/会怎么干"分成两个一等记忆表面。**

| 轨 | Owner | kind | 存储 | 谁产生 |
|---|---|---|---|---|
| **用户轨迹** | user | `episode`（发生了什么） | `users/<uid>/episodes/episode-<date>.md` daily-log | extraction（同步写盘） |
| | user | `atomic_fact`（单句事实） | `.atomic_facts/`（隐藏） | OME |
| | user | `foresight`（预期/前瞻笔记） | `.foresights/`（隐藏） | OME |
| | user | `profile`（聚合画像 `user.md`） | 单文件覆写 | OME |
| **Agent 轨迹** | agent | `agent_case`（可复用 agent 轨迹） | `agents/<aid>/.cases/`（隐藏） | OME（仅当轨迹"够实质"，薄轨迹刻意跳过） |
| | agent | `agent_skill`（程序性技能） | `agents/<aid>/skills/skill_<name>/SKILL.md` | OME（聚类 cases 成技能） |

- **设计意图**：`episodes/profile` 告诉 agent"用户是谁、发生过什么"；`cases/skills` 告诉 agent"我（agent）过去怎么把事做成，下次还能怎么做"——**记忆既当上下文，也当可复用能力**。这在任务背景里正是我们"claude-mem 思想 + 想吸收的部分"里最缺的一块。

### 4. "自演化复用 / self-evolving reuse"怎么实现？——Offline Memory Engine（OME）
记忆不是请求路径上现提取的，而是**事后由一个进程内异步策略引擎**派生：
- 提取出一颗 **MemCell**（boundary 账本，SQLite-only，无 md 文件）→ 发事件 → OME 各策略异步写各自的 md。
- **OME 策略清单**：`extract_atomic_facts`、`extract_foresight`、`extract_user_profile`（聚合 user.md）、`extract_agent_case`（可复用轨迹，薄轨迹跳过）、`extract_agent_skill`（把相关 cases **聚类成一个命名技能**）、`trigger_profile_clustering`、`trigger_skill_clustering`、**`reflect_episodes`（cron 离线记忆整合，默认关）**。
- **Reflection（离线条块整合）**：每周一 02:00 cron，选出多成员的 cluster → LLM 把碎片 episode **合并成一个连贯叙事** → 写回 md → 重新提取 atomic facts → 原条目标 `deprecated_by` 弃用。合并后的 episode `parent_type=cluster`、`session_id=None`。
- **配置无需改码**：`ome.toml` 可开关/调每个策略（约 2 秒热重载），例如 `[strategies.extract_foresight] enabled=false`。

**这就是"自进化"的落地：episodes →（聚类)→ cases →（聚类）→ skills；散乱会话每周被合并成 coherent 记忆，旧条目走 deprecation 而非删除（保审计）。**

### 5. Knowledge Wiki 跟记忆啥关系？
`knowledge/` 是**全局/共享**的第三表面（与 users/、agents/ 平级），不属于任何单个 user 或 agent：
- kind：`knowledge_document`（`knowledge/<category>/<title>/index.md`）、`knowledge_topic`（`<category>/<title>/<N>_<topic_slug>.md`）——**有 taxonomy（分类）的知识树**。
- 可编辑、可溯源（source-backed）Markdown 知识页 + CRUD API + topic search。
- **与记忆的区别**：记忆是"个人/agent 的经历与画像"，Wiki 是"共享 / 全局的、可分类沉淀的知识资产"；Wiki 也会被 cascade 建成 LanceDB 索引可检索。可以理解为：**记忆回答"我是谁/发生过什么"，Wiki 回答"我们共同知道什么"**。我们现在用 get_goal / update_plan 临时存项目知识，但没有这种显式的共享知识树。

### 6. 正交检索（user_id / agent_id / app_id / project_id / session_id）
- 目录结构 = 隐含的检索分片：`<app_id>/<project_id>/users/<user_id>/`、`.../agents/<agent_id>/`。
- 检索不是单一 namespace/thread 作用域，而是**可在五个正交维度上独立过滤**：`user_id`、`agent_id`、`app_id`、`project_id`、`session_id`。
- 每个 kind 一个 LanceDB Arrow 表，一条查询里同时做向量 ANN + BM25 全文 + 标量过滤（嵌入 LanceDB，单进程）。
- **取舍**：scope 编进 **路径**（而非 frontmatter），跨表 join 靠 `(owner_id, entry_id)` 复合键。

### 7. 一致性模型（很干净）
| Path | 保证 |
|---|---|
| **写** /add、/flush | **强一致**：flush 返回 `extracted` 时 episode md **已落盘**；绝不阻塞 LanceDB |
| **读** /search、/get | **最终一致**：读 LanceDB，滞后 md 约 sub-second ~ 10–15s |

- flush 后立刻 search 可能查不到——md 已持久，索引没跟上；要 read-your-write 就退避重试或 `everos cascade sync` 强制排空队列。
- 这条"**写 markdown 强一致 + 读索引最终一致**"的设计，正是我们 memory 体系可以对照的黄金套路。

## 三、与 OpenClaw 的 memory 体系对比

我们（OpenClaw）：`MEMORY.md` 长期精炼记忆 + `memory/YYYY-MM-DD.md` 每日日志 + `memory_search` 语义检索 + `memory_distill.py` 蒸馏脚本（claude-mem 思想）。EverOS 是 Python 库 + HTTP server 的完整运行时。

### EverOS 有、我们缺、值得移植的设计 ✅
1. **双轨组织（user trajectory vs agent trajectory）**：我们几乎只有"用户/工作上下文日志"单轨。EverOS 的 **cases/skills（agent 行为轨迹 → 聚类成可复用技能）** 我们完全没有——我们的技能靠 Skill Workshop，但**没有"从记忆里自动沉淀出技能"**的机制。这是最值得借鉴的核心思想。
2. **"记忆 → 技能/画像"的异步自演化引擎**：EverOS 把"提取原子事实 / 前瞻 / 画像 / 合并整合 / 聚类技能"全部做成**离线后台策略**，不阻塞请求路径。我们的 memory_distill.py 已经有蒸馏雏形，但对标 EverOS 可以升级成"**定期跑 distillery：把散日志聚合进 MEMORY.md / 沉淀出可复用 SOP**"的调度任务。
3. **三种落盘策略**：我们其实已经自然用到了 daily-log（memory/YYYY-MM-DD.md）和 single-file rewrite（MEMORY.md）——但**缺"skill-named dir"这一档**：给明确、稳定、可复用的东西（如周报流程、常用命令、SOP）开独立 markdown 文件，而不是塞进 MEMORY 或散日志。
4. **"索引可重建、md 即真相"**：我们天然就是 md 即真相（memory_search 是从文件建索引），EverOS 把它提到了"删索引不丢记忆"的最高原则。我们可固化一条约定：**memory_search 索引坏/重建前绝不碰 .md 源文件**。
5. **消费侧强/最终一致分离**：我们的 memory 写到核心里，读靠 memory_search，基本同理，但没显式文档化"**写后立即可用 vs 检索可能滞后**"这条一致性契约——建议写进 TOOLS.md/HEARTBEAT.md。

### 我们已更好 / 更轻的地方 🟢
1. **更轻**：EverOS 是 Python 3.12 + `uv pip install everos` + 起 HTTP server + OpenRouter/DeepInfra API key + LanceDB 依赖。我们**零外部依赖**——纯 markdown + 既有 memory_search，更符合"随手可维护、不用常驻 server"。
2. **更贴近"人格/灵魂"**：我们的 MEMORY.md / USER.md / SOUL.md / GUEST.md 体系是**叙事性长期记忆 + 身份锚定**；EverOS 对"用户是谁"只有聚合 `user.md` 画像，没有我们这种"who I am / who I'm helping / how to treat guests"的分角色叙事人格。在 DeepSeek/心哥这类长期陪伴场景里我们的更细。
3. **语义检索已内建**：memory_search 直接用；EverOS 要自建 LanceDB 向量管 + embedding/rerank API key 才可语义检索。
4. **身份安全分轨**：我们的 AGENTS.md 有 guest-mode / 身份验证设计；EverOS 是工程范式，不解决"谁在说话、能不能看私密记忆"。

## 四、精华总结

EverOS 的核心思想一句话：**"Markdown 是唯一真相源，SQLite/LanceDB 都是可重建的派生索引"**——删光 `.index/` 一条记忆不丢，md 即导出。真正的杀招是**三档落盘策略（每日日志追加 / 单文件覆写画像 / 技能命名目录）** + **双轨组织（用户轨迹 episodes/profile 存"用户是谁"，agent 轨迹 cases/skills 存"agent 怎么把事做成、下次怎么复用"）** + **离线的 Offline Memory Engine**：提取原子事实、前瞻、聚合画像、聚类 skills、每周把碎片 episodes 合并成连贯叙事并标 deprecated 而非删除。外加一个干净的一致性契约：**写 markdown 强一致、读索引最终一致**。知识 Wiki 是独立于个人的全局共享知识树（taxonomy + CRUD）。对我们最有价值的是"**从记忆自演化沉淀出可复用技能/画像**"和"**索引可重建、md 即真相**"两条，跟我们 memory_distill.py + MEMORY.md 的蒸馏思路同源，但 EverOS 把它工程化成完整的运行时与后台策略引擎。

## 五、可落地建议（不装它的 Python/LanceDB 整套）

1. **引入"技能命名目录"落盘档**：在 workspace 下新增 `skills_reuse/`（或沿用 Skill Workshop 但采用"一条稳定 SOP 一个 md 文件"），把明确、可复用的流程（周报、常用命令、开会纪要模板）沉淀成独立 markdown，而不是塞进 MEMORY.md 或散日志——对标 EverOS 的 `skills/skill_<name>/SKILL.md`。
2. **把 memory_distill.py 升级成"双轨蒸馏"**：现在它大致做 daily→MEMORY 的精炼（≈user track）。参照 EverOS 的 agent track，在 distillation 里**额外输出"cases.md / 沉淀 SOP"**——把本次会话里"agent 成功做成的步骤"提炼成可复用条，供下次直接调用。
3. **固化"md 即真相、索引可重建"契约**：在 TOOLS.md 或 HEARTBEAT.md 写一条红线——memory_search 索引异常时**先重建索引、绝不改写/删除 .md 源文件**；Md 文件永远可读可编辑、可 git 版本化，索引只是加速层。同时补一条"写 mem 立即可用、检索可能滞后"的一致性说明，避免"刚写查不到"误判。
4. **给记忆加显式分片/正交头**（简化版正交检索）：虽不照搬 app_id/project_id 全套，但可在 memory 文件 frontmatter 或文件名里带 `track: user|agent` 和 `skill:` 标签，让 memory_search 能按"用户轨迹 vs agent 可复用技能"过滤——低成本获得 EverOS 双轨检索的大部分收益。
5. **模仿 OME/reflection 的"周汇总"节奏**：把 memory 维护从"心跳顺手做"升级为可用 cron 的**离线合并任务**（对标每周一 02:00 reflect_episodes）：每周把本周 memory/*.md 里散碎的同类事件合成一个连贯篇目并入 MEMORY.md，旧条目标注/替换而非硬删，保持改编历史和审计。我们已在做 memory 维护，这里补上"定期压舱 + 合并去重"的显式调度即可。

---
*引用：`everos_readme.md` / `everos_readme_zh.md` / `everos_how_memory_works.md` / `everos_storage_layout.md` / `everos_migration.md`（同目录 raw 缓存）。*
