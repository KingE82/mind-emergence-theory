# obra/superpowers — 调研笔记

> 抓取时间：2026-08-03（Asia/Shanghai）
> 数据源：`https://raw.githubusercontent.com/obra/superpowers/main/README.md`（HTTP 200）+ GitHub API
> 作者：Jesse Vincent（fsck.com）及 Prime Radiant 团队。License: MIT

## 项目概况

- **定位**：「An agentic skills framework & software development methodology that works.」
- **规模**：265,172 ⭐，23,681 forks，323 open issues，活跃维护（pushed 2026-08-02）
- **多运行时**：Claude Code、Antigravity、Codex App/CLI、Cursor、Factory Droid、Gemini CLI、GitHub Copilot CLI、Kimi Code、OpenCode、Pi —— 一套 skills 通过插件/扩展机制适配所有主流编码 agent。

---

## 核心机制：什么是 "Superpowers"

一句话：**极简启动指令 + 一套可按需自动触发的组合式 skills，把编码 agent 约束成「先澄清→出方案→写计划→子代理分步驱动→TDD→审查」的流程机器。**

关键设计点：

1. **自动触发（不是靠用户喊）**：agent 每次在动手写代码前，"checks for relevant skills before any task"。`using-superpowers` 这个 meta-skill 是 session-start 注入的引导器，让后续 skills 自动加载。**「Mandatory workflows, not suggestions.」**——不是建议，是强制流程。

2. **技能是参考手册，不是叙事**：Skill = "reference guide for proven techniques, patterns, tools"（可复用技术/模式/参考），**明确排除**「讲一次怎么解决问题的叙事」。

3. **技能组织**：`skills/<skill-name>/SKILL.md`（必需）+ 可选辅助文件 + `references/` 子目录。作者不轻易收新技能，改动必须跨所有支持运行时兼容。

4. **技能三分法**：
   - **Technique**：具体有步骤的方法（如 condition-based-waiting、root-cause-tracing）
   - **Pattern**：看待问题的思维方式（如 flatten-with-flags、test-invariants）
   - **Reference**：API 文档、语法速查、工具文档

---

## 软件开发方法论（七步主流程）

1. **brainstorming** — 写代码前激活。用苏格拉底式提问澄清需求、探索备选方案、分块呈现设计给人确认，落盘 design document。
2. **using-git-worktrees** — 设计获批后。新建分支隔离工作区、跑项目初始化、验证干净的测试基线。
3. **writing-plans** — 用获批设计。把工作拆成 **2–5 分钟一粒的小任务**，每粒含精确文件路径、完整代码、验证步骤。
4. **subagent-driven-development / executing-plans** — 用计划。每个任务派一个新的子代理，做**两阶段评审**（先查需求符合，再查代码质量）；或批量执行+人工检查点。可自主跑数小时。
5. **test-driven-development** — 实现中生效。强制 RED-GREEN-REFACTOR：先写失败测试→看它失败→写最小代码→看它通过→提交。**删掉测试之前写的代码。**
6. **requesting-code-review** — 任务间进行。对照计划评审，按严重度上报问题，严重问题阻断进度。
7. **finishing-a-development-branch** — 任务完成。验证测试，给 merge/PR/keep/discard 选项，清理 worktree。

**哲学**：TDD 优先、系统化优于临时凑、简化为首要目标、用证据不用空话（验证后再宣称完成）。

---

## 亮点：writing-skills（TDD 应用到写技能）

这页对 skill 体系的启发最大，核心思想：

> **「Writing skills IS Test-Driven Development applied to process documentation.」**
> **「If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.（没看过 agent 没有该技能时怎么失败，就不知道技能教的对不对）」**

| TDD | 写技能 |
|-----|--------|
| 测试用例 | 压力场景 + 子代理 |
| 生产代码 | 技能文档 SKILL.md |
| RED | 没技能时 agent 违规（记 baseline 行为） |
| GREEN | 有技能后 agent 遵守 |
| Refactor | 堵漏洞且保持合规 |

**先跑 baseline 再写技能，记录 agent 的「合理化辩解」**，然后写针对这些具体违规的最小化文档，验证通过后再堵新漏洞。

何时不写技能：一次性方案、别处已充分文档化的标准做法、项目特定约定（放 instructions 文件）、机械性约束（能用 regex/正则自动强制的就去自动化，别浪费文档）。

---

## 与 OpenClaw skills / skill-workshop 的异同

| 维度 | obra/superpowers | OpenClaw（我方） |
|------|------|------|
| 组织形式 | `skills/<name>/SKILL.md` + references/ | SKILL.md + 可带脚本/示例/引用文件（技能带版本 hash 校验） |
| 生命周期 | 手工写 + 跨运行时社区维护 | skill-workshop 提案→apply/reject/quarantine 流程化管理 |
| 触发 | session-start 注入 `using-superpowers` 引导器，**强制自动触发** | agent 扫描 available_skills 按描述匹配，无强制流程概念 |
| 可移植性 | 一套 skills 适配 10 种运行时 | 强绑定 OpenClaw 环境 |
| 评审 | 两阶段子代理评审（规格符合→代码质量） | 无内建多阶段评审流程 |
| 方法论 | 完整 SDLC 流程（brainstorm→plan→subagent→TDD→review） | 无统一开发方法论，各技能独立 |
| onboarding | 无技能版本概念，skill 少而精 | 有版本 hash + memory 维护 |

**最大的差距**（可借鉴点）：
1. OpenClaw 的 skills 是**工具库**，superpowers 把一个 skills 集组织成了**完整方法论**（从想法到交付的强制管道）。
2. OpenClaw 的触发是被动按描述匹配；superpowers 用引导技能 **主动注入** + 强制检查。
3. superpowers 的 **TDD-based skill authoring**（先看没技能时怎么失败再写文档、记 rationalizations）是工坊流程没有的思路。
4. 两阶段子代理评审、2–5 分钟可测试粒度、YAGNI/DRY 铁律。

---

## 150–300 字中文精华总结

Superpowers 是 Jesse Vincent 团队开源（26.5 万星）的一套「Agentic 技能框架 + 软件开发方法论」。核心是把一个编码 agent 变成强制流程机：每次动工前先自动检查并按需加载对应 skills，严格执行「头脑风暴澄清需求→Git worktree 隔离→写 2–5 分钟粒度计划→子代理按任务分步实现（两阶段评审）→TDD 红绿重构→代码评审→收尾交付」七步管道。关键设计有三：一是技能用 session 注入的引导技能 `using-superpowers` 自动触发，二是技能被定义为「可复用的技术/模式/参考手册」而非问题解决叙事，三是作者用 TDD 方法写技能——先跑 baseline 看无技能时 agent 如何失败、记录其合理化辩解，再写最小化文档封堵，最后补漏洞。这套体系最大的启发是把零散 skills 组装成完整可落地的工程方法论，而不是工具堆砌。

---

## 可落地建议（给 OpenClaw 体系）

1. **引入「流程引导技能」**：借鉴 `using-superpowers`，增加一个 session 启动即加载的 meta-skill 或 AGENTS 流程约定，让复杂跨技能任务（→见 taskflow）自动走「澄清→计划→执行→审查」管道，而不只是按描述被动匹配单个技能。

2. **引入 TDD 式技能编写**：在 skill-workshop 提案中增加「先跑 baseline 场景、记录无技能时的失败/合理化、再写最小 SKILL.md」的强制步骤，提升技能质量与受众真实体验。

3. **技能三分法落地**：给 SKILL.md metadata 标注 type=technique / pattern / reference，便于 agent 调用时判断该「按步骤做」「换思路」还是「查资料」。

4. **两阶段子代理评审**：为多步开发任务（如代码类 taskflow 任务）内置「先查需求符合、再查质量」的双层评审 gate，符合 OpenClaw 已有的 subagent/taskflow 机制。

5. **YAGNI/DRY/「不写叙事只写手册」「机械约束用自动化而非文档」**：写进 skill-creator / skill-workshop 的技能编写规范，作为红线。

---

*原始材料：README.md（281 行）、repo API、skills 目录列表（14 个技能）、writing-skills/SKILL.md（部分）。如后续需要，可再深挖单个 skill 的 SKILL.md 与 references/。*
