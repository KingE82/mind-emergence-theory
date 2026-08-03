#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记忆自动蒸馏脚本 · 借鉴 claude-mem 的 observation 思想

把每天 memory/YYYY-MM-DD.md 的原始日志，自动压成结构化 nugget（决策/修复/发现/下一步），
落进 memory/_index/，让 memory_search 命中率更高、上下文更省。

用法:
    python3 memory_distill.py                # 蒸馏今天
    python3 memory_distill.py 2026-08-02     # 蒸馏指定日期
    python3 memory_distill.py --all          # 蒸馏所有缺失的日期

产物: memory/_index/YYYY-MM-DD.nuggets.md  （结构化，带 type/title/一句话/引用）
"""
import os
import re
import sys
import subprocess
from datetime import date, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE, "memory")
INDEX_DIR = os.path.join(MEMORY_DIR, "_index")
TODAY = date.today().isoformat()

# 可被识别的标题行（## 等），作为 nugget 切分锚点
HEADING_RE = re.compile(r"^#{1,3}\s+(.+)")
# 事件/决策类关键词，判定该段是否值得蒸馏
VALUABLE_KEYWORDS = [
    "修复", "完成", "上线", "推送", "部署", "决策", "安装", "重建",
    "创建", "升级", "解决", "发现", "结论", "落地", "开通", "整理",
    "拆分", "重构", "里程碑", "突破", "教训", "踩坑", "经验",
]

def get_dates(target):
    """决定要蒸馏哪些日期文件"""
    if target == "--all":
        files = [f[:-3] for f in os.listdir(MEMORY_DIR)
                 if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f)]
        return sorted(files)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", target):
        return [target]
    # 默认今天
    if target == "today" or target is None:
        return [date.today().isoformat()]
    raise ValueError(f"无法识别的目标: {target}")

def split_sections(text):
    """按 markdown 标题切成 (标题, 内容块) 列表"""
    sections, cur_head, cur_lines = [], None, []
    for line in text.splitlines():
        m = HEADING_RE.match(line.strip())
        if m:
            if cur_head is not None:
                sections.append((cur_head, "\n".join(cur_lines)))
            cur_head, cur_lines = m.group(1), []
        elif line.strip():
            cur_lines.append(line)
    if cur_head is not None:
        sections.append((cur_head, "\n".join(cur_lines)))
    return sections

def valuable(block):
    """判断一段内容是否值得蒸馏"""
    if len(block) < 15:
        return False
    return any(kw in block for kw in VALUABLE_KEYWORDS)

def extract_nuggets(date_str):
    """从某天日志提取结构化 nugget"""
    fp = os.path.join(MEMORY_DIR, f"{date_str}.md")
    if not os.path.isfile(fp):
        return None, f"无日志文件 {date_str}.md"
    with open(fp, encoding="utf-8") as f:
        text = f.read()
    sections = split_sections(text)
    nuggets = []
    seen_titles = set()
    for head, block in sections:
        if head in seen_titles:
            continue  # 跳过重复标题的段落（防多段同标题重复蒸馏）
        if not valuable(block):
            continue
        seen_titles.add(head)
        lines = [l for l in block.splitlines() if l.strip()]
        title = head.strip()
        # 取第一句作为一句话摘要
        one_liner = lines[0][:60] if lines else ""
        # 判定类型
        ntype = "change"
        if any(k in head for k in ["修复", "bug", "踩坑", "教训"]):
            ntype = "bugfix"
        elif any(k in head for k in ["决策", "确认", "钦定", "定"]):
            ntype = "decision"
        elif any(k in head for k in ["上线", "推送", "部署", "上架"]):
            ntype = "release"
        elif any(k in head for k in ["发现", "结论", "突破", "milestone"]):
            ntype = "discovery"
        # 找下一步/待办
        next_steps = []
        for l in lines:
            if l.startswith("- [ ]") or "待办" in l or "下一" in l or "TODO" in l.upper():
                next_steps.append(l.strip())
        nuggets.append({
            "date": date_str,
            "type": ntype,
            "title": title,
            "one_liner": one_liner,
            "next_steps": next_steps[:3],
            "ref": f"memory/{date_str}.md",
        })
    return nuggets, None

def render(nuggets):
    """渲染成 markdown"""
    lines = ["<!-- 自动蒸馏：memory_distill.py 生成，勿手改 -->", ""]
    for n in nuggets:
        lines.append(f"- **[{n['type']}]** {n['title']} — {n['one_liner']}（`{n['ref']}`）")
        for ns in n["next_steps"]:
            lines.append(f"  - ↳ {ns}")
    return "\n".join(lines)

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "today"
    dates = get_dates(target)
    os.makedirs(INDEX_DIR, exist_ok=True)
    made = 0
    for dstr in dates:
        nuggets, err = extract_nuggets(dstr)
        if err:
            print(f"[跳过] {dstr}: {err}")
            continue
        if not nuggets:
            print(f"[空] {dstr}: 无可蒸馏内容")
            continue
        out = os.path.join(INDEX_DIR, f"{dstr}.nuggets.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(nuggets))
        made += 1
        print(f"[蒸馏] {dstr}: {len(nuggets)} nuggets → {out}")
    print(f"\n完成，共蒸馏 {made} 天。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
