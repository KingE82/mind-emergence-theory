#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自定义增量索引工具 · 绕过 build_index（它 torch import 死锁）

直接把"尚未入库"的文件（按 manifest mtime 判断）切块 → embedding → 追加进现有索引。
复用 chunk_note（切块）+ local_embedder.embed_many（embedding），两者均验证可靠。
"""
import sys
import os
import json
import time

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # workspace 根（rebuild_env/ 的上一级）
KX = os.path.join(WS, "xin_sources/new_tools/KnowledgeX")
RAG = os.path.join(KX, "rag_index")
VAULT = os.path.join(WS, "knowledgex_vault")

sys.path.insert(0, KX)
sys.path.insert(0, WS)
os.environ["VAULT_ROOT"] = VAULT

CHUNKS_FILE = os.path.join(RAG, "chunks.json")
VECTORS_FILE = os.path.join(RAG, "vectors.npy")
MANIFEST_FILE = os.path.join(RAG, "manifest.json")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def iter_note_paths():
    """扫描 01-笔记/02-领域/03-资源 下所有 .md"""
    from pathlib import Path
    paths = []
    for d in ["01-笔记", "02-领域", "03-资源"]:
        base = Path(VAULT) / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            rel = p.relative_to(VAULT)
            if any(part.startswith(".") for part in rel.parts):
                continue
            paths.append(str(rel))
    return paths


def load_index():
    """加载现有索引"""
    if os.path.exists(CHUNKS_FILE) and os.path.exists(VECTORS_FILE):
        import numpy as np
        chunks = json.load(open(CHUNKS_FILE, encoding="utf-8"))
        vecs = np.load(VECTORS_FILE)
        return chunks, vecs
    return [], None


def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        return json.load(open(MANIFEST_FILE, encoding="utf-8"))
    return {}


def get_mtime(rel_path):
    st = os.stat(os.path.join(VAULT, rel_path))
    return st.st_mtime


def main():
    import numpy as np
    from web.rag.chunker import chunk_note
    import local_embedder

    log("加载现有索引…")
    chunks, vecs = load_index()
    existing_count = len(chunks)
    log(f"现有 {existing_count} chunks")

    # 找出需要入库的新文件（mtime 变化或不在 manifest）
    note_paths = iter_note_paths()
    new_notes = [p for p in note_paths if get_mtime(p) > 0]
    manifest = load_manifest()
    need = []
    for p in note_paths:
        mt = get_mtime(p)
        if manifest.get(p) != mt:
            need.append(p)
    log(f"待入库 {len(need)} 个文件")

    # 只处理西医资料（本次目标），避免重复处理其他已入库的
    # 更精确：所有 manifest 里没有的文件都处理
    new_chunks = []
    note_titles = {}
    for rp in need:
        try:
            cs = chunk_note(rp, max_chars=800)
            # chunk_note 返回的 chunk 有 text/section，构造 dict
            for c in cs:
                new_chunks.append({
                    "note_path": rp,
                    "note_title": getattr(c, "note_title", ""),
                    "section": getattr(c, "section", ""),
                    "text": c.text,
                    "chunk_id": f"{rp}#{len(new_chunks)}",
                })
        except Exception as e:
            log(f"  切块失败 {rp}: {e}")
    log(f"切出 {len(new_chunks)} 新 chunks")

    if not new_chunks:
        log("无新 chunks，无需处理")
        return

    # embedding
    log(f"开始 embedding {len(new_chunks)} 条…")
    texts = [c["text"] for c in new_chunks]
    t0 = time.time()
    new_vecs = local_embedder.embed_many(texts, concurrency=64)
    log(f"embedding 完成 {len(new_vecs)} 条，耗时 {time.time()-t0:.0f}s")
    new_vecs = np.array(new_vecs, dtype=np.float32)

    # 合并 + L2 归一化
    all_chunks = chunks + new_chunks
    if vecs is not None and vecs.shape[0]:
        all_vecs = np.vstack([vecs, new_vecs])
    else:
        all_vecs = new_vecs
    norms = np.linalg.norm(all_vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    all_vecs = all_vecs / norms

    # 持久化
    np.save(VECTORS_FILE, all_vecs.astype(np.float32))
    json.dump(all_chunks, open(CHUNKS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    new_manifest = {p: get_mtime(p) for p in note_paths}
    json.dump(new_manifest, open(MANIFEST_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    log(f"✅ 完成: {existing_count} → {len(all_chunks)} chunks (+{len(new_chunks)})")


if __name__ == "__main__":
    main()
