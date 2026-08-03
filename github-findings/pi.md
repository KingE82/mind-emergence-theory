# GitHub 调研：earendil-works/pi

> 调研时间：2026-08-03 ｜ 仓库：TypeScript monorepo

## 一句话定位
一个通用 AI Agent **工具包（harness）**，核心能力是"统一多 provider LLM 调用 + agent 运行时 + 自扩展 coding agent + TUI"，主打给 agent 开发者当底层拼装件，而非开箱即用的个人助手。

## 中文精华（约 230 字）
Pi 拆成三层包，边界清晰：
- **@earendil-works/pi-ai**：统一多 provider LLM API（OpenAI/Anthropic/Google/DeepSeek/OpenRouter/xAI/ZAI 等 20+）。设计上只收录「支持 function calling」的模型（agentic 关键）；提供 provider 工厂、自动鉴权解析（环境变量/凭证仓库/OAuth）、token 与成本追踪、流式 tool call+部分 JSON 解析、消息序列化与**跨 provider 中途交接（hand-off）**。
- **@earendil-works/pi-agent-core**：agent 运行时，负责 tool calling 与状态管理（即 agent loop 的骨架）。
- **@earendil-works/pi-coding-agent / pi-tui**：交互式 coding CLI 与差分渲染 TUI。

值得注意：它**不做**内置权限系统，默认以当前用户权限裸跑，靠容器/沙箱兜底。跟 OpenClaw 的关系更像是「可复用组件库」vs「完整个人助手」，两者在统一 provider 抽象上有高度重叠。

## 可落地建议
1. **提炼统一 provider 抽象层**：pi-ai 的"provider 工厂 + 统一接口 + 自动鉴权"正是我们 deepseek/zai/gpt 多后端调用的解耦范式——抽一个 `provider.resolve()`，按模型名自动选后端、默认环境变量取 key。
2. **只收录支持 tool-call 的模型**：值得借鉴，agentic 场景下自动过滤掉无 function-calling 的模型，省踩坑。
3. **token/成本追踪内置**：每轮自动累计，对我们多 backend 混合调用的成本归因很有用。
4. **跨 provider 中途交接（hand-off）**：同一 session 换模型续聊——OpenClaw 已有 fallback 链，可参考其对上下文序列化的处理。
5. **权限边界先想清**：Pi 明确"无内置权限、靠容器"的态度，值得我们在给工具网关权限时参考其分层模型（host auth vs sandbox）。

> 注：README 抓取正常，未遇阻碍。
