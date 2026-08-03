# GitHub 调研：deepseek-ai/DeepSeek-VL2

> 调研时间：2026-08-03 ｜ 仓库：DeepSeek 官方视觉语言模型（MoE）

## 一句话定位
DeepSeek 官方第二代 **MoE 视觉语言模型**，主打识图问答/OCR/文档图表理解/视觉定位（visual grounding），本地可部署，并非商业 API。

## 中文精华（约 260 字）
架构上是有语言部分（DeepSeek-MoE）+ 混合视觉编码器的 MoE VLM。三档规格，均 **4096 序列长度**：
- **DeepSeek-VL2-Tiny**：1.0B 激活参数
- **DeepSeek-VL2-Small**：2.8B 激活参数
- **DeepSeek-VL2**：4.5B 激活参数

能力覆盖：视觉问答、OCR / 文档 / 表格 / 图表理解、视觉定位（输出 `<|det|>[[x,y,w,h]]` 坐标框，支持 grounded captioning）。推理用 `transformers` + `trust_remote_code`，bfloat16，通过 HF 下载权重。**资源门槛偏高**：官方明确 single-image 脚本跑 small/完整版需 **80GB 显存**；用 incremental prefilling 技巧可压到 **~40GB** 跑 small。有 Gradio demo（HF Space）和 VLMEvalKit 支持。许可证：代码 MIT / 模型遵循专属 Model Agreement。

## 关键评估：能否做我们"视觉模型"自主备份/长期方案？
**结论：不适合做线上主力，仅具备"离线本地备份"的理论可能。**
- 硬伤：无托管 API，只能本地自部署；最小 Tiny 也要高显存（40–80GB 级）且单卡 A100/H100 级别，OpenClaw 运行环境根本扛不动。
- 我们当前 `glm-4v-flash` 免费 API、零成本、即用即取，延迟和运维远优于本地 VL2。
- 价值点：如果哪天真要"离线+自主"跑图理解，VL2 是可选开源底子；否则继续用 API 更务实。DeepSeek 官方也可能有更新的 open-source VLM（如需可再查），VL2 已偏旧（2024-12 发布）。

## 可落地建议
1. **维持 glm-4v-flash 为主**：免费 API + 零资源 + 已通，短期内无替代必要。
2. **本地 VL2 仅当"离线兜底"考虑**：需给到 Tiny 级别 + 40GB 显存 + vLLM/增量 prefilling，我们当前无此硬件，先搁置。
3. **兜底优先级**：若 `glm-4v-flash` 失效，优先找其他免费/低成本 VLM API（如 DeepSeek 生态若有新模型、或开源 API 网关转发），而非自扛显存。
4. **可做概念验证**：若后续有 GPU 条件，用 VL2-Tiny 对任意图文跑一次推理，验证文档/表格理解能力是否够 OpenClaw 场景用。
5. **别依赖单一视觉通道**：即使是 API 方案，也应保留图片模型 fallback 链（现有双保险思路），VL2 仅作为最后一条可选兜底。

> 注：README 抓取正常，未遇阻碍。
