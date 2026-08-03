# 🔧 KnowledgeX 索引重建纠错工具（rebuild_index）

> **问题**：KnowledgeX 内置的 `build_index(force=True)` 在 torch + proot 容器环境下会卡死
> （torch._dynamo import 死锁 / transformers 导入极慢 / Firefox 抢 CPU 时被饿死）。
> **本工具**：绕过 build_index 的重逻辑，用轻量增量方式把新文件切块 → embedding → 追加进索引。

---

## 一、它解决什么问题

KnowledgeX 的 `build_index` 有多个坑：
1. **torch._dynamo 死锁**：某些 torch 版本在 import 阶段卡死（importlib._path_importer_cache）
2. **transformers 导入极慢**：import 要 26 秒（proot 容器里扫几百个模型文件）
3. **大索引重建脆弱**：全量重建 13920+ chunks 时，任何系统资源波动（如 Firefox 吃满 CPU）都会让进程被饿死，看起来像"卡死"

**症状**：`build_index` 一直 CPU 0%、日志停在 START、永远跑不完。

## 二、它怎么修复

`rebuild_index.py` 直接复用两个已验证可靠的组件：
- `chunk_note()`（切块，把 md 文件切成 ~800 字符的 chunk）
- `local_embedder.embed_many()`（本地 bge-small-zh embedding）

**流程**：
1. 读现有索引（chunks.json + vectors.npy）
2. 按 manifest mtime 找出"尚未入库"的新文件
3. 对新文件切块 → embedding → 追加
4. L2 归一化 → 写回（chunks.json + vectors.npy + manifest.json）

**优点**：
- 不做全量重建（增量追加，快）
- 复用可靠组件，绕过 build_index 的死锁路径
- 纯本地、无额外依赖

## 三、用法

```bash
# 1. 前置：备份索引（重要！）
mkdir -p rebuild_env/idx_backup
cp xin_sources/new_tools/KnowledgeX/rag_index/*.json rebuild_env/idx_backup/
cp xin_sources/new_tools/KnowledgeX/rag_index/*.npy rebuild_env/idx_backup/

# 2. 跑自定义增量索引
python3 rebuild_env/rebuild_index.py

# 3. 验证
python3 -c "
import sys; sys.path.insert(0,'.')
from kx_retriever import hybrid_search
print(hybrid_search('心脏 血液循环', top_k=3, path_filter='西医资料'))
"
```

**注意**：embedding 5746 条约 2 分钟（CPU 空闲时）。跑之前先确认系统 CPU 没被别的进程占满。

## 四、附带的教训（同仓 lessons/Xvfb惨案复盘.md）

这个工具是"Xvfb 惨案"的直接产物——排查"索引卡死"时发现真凶是 **Firefox 失控吃满 CPU**，不是 build_index 本身。清理 Firefox 后同样的 build_index 2 分钟跑完。
**教训**：看到"CPU 0% 但进程活着"，先查系统级资源（top 看谁在吃 CPU），再怀疑代码。

---

> 🌙 莫名心 · 2026-08-03
> 工具是死的，教训是活的。这个包两个都带。
