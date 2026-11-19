#!/usr/bin/env python3
"""阶段门禁检查。

用法:
    python gate.py . --episode EP01 --stage S6
    python gate.py . --stage S1 --check-deps
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STAGE_REQUIRED = {
    "S0": ["course.yaml"],
    "S1": ["content/knowledge-map.md", "content/glossary.md", "content/lectures"],
    "S1.5": ["content/prerequisites.md"],
    "S2": ["tooling/skills.lock.md"],
    "S3": ["plan/episodes.yaml", "plan/{ep}.md"],
    "S4": [
        "manuscript/{ep}/script.md",
        "manuscript/{ep}/examples.md",
        "manuscript/{ep}/shots.yaml",
    ],
    "S5": ["reviews/{ep}-author.md"],
    "S6": ["reviews/{ep}-learner-r*.md"],
    "S7": ["video/{ep}.mp4"],
    "S8": ["reviews/{ep}-watch-r*.md"],
    "S9": ["delivery/manifest.json"],
}

NEXT_STEP = {
    "S0": "S1 拆课：建 knowledge-map.md",
    "S1": "S1.5 先修诊断：建 prerequisites.md",
    "S1.5": "S2 找技能：建 skills.lock.md",
    "S2": "S3 分集：填 episodes.yaml",
    "S3": "S4 写稿：script.md / examples.md / shots.yaml",
    "S4": "运行 check_script.py，然后 S5 作者审稿",
    "S5": "S6 学生试读（新开 subagent）",
    "S6": "S7 制作（交给 code-course-video）",
    "S7": "S8 学生试看（新开 subagent）",
    "S8": "S9 定稿：manifest.json",
    "S9": "交付",
}


def expand(pattern: str, ep: str) -> str:
    return pattern.replace("{ep}", ep or "EP01")


def latest(root: Path, pattern: str):
    matches = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def check_author_review(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"blocking[^\n]{0,12}?[:：]\s*(\d+)", text, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return n == 0, f"blocking={n}"
    if "结论" in text and "通过" in text and "不通过" not in text:
        return True, "结论含通过"
    return False, "未找到 blocking 计数或通过结论"


def check_learner_review(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    notes = []

    score = re.search(r"理解均分[^\n]{0,8}?[:：]\s*([\d.]+)", text)
    if score:
        v = float(score.group(1))
        notes.append(f"理解均分={v}")
        if v < 2.5:
            return False, "；".join(notes) + "，低于 2.5"

    acc = re.search(r"例题正确率[^\n]{0,8}?[:：]\s*(\d+(?:\.\d+)?)\s*%", text)
    if acc:
        v = float(acc.group(1))
        notes.append(f"正确率={v:g}%")
        if v < 80:
            return False, "；".join(notes) + "，低于 80%"

    blocking = re.search(r"blocking\s*数[^\n]{0,8}?[:：]\s*(\d+)", text, re.IGNORECASE)
    if blocking:
        n = int(blocking.group(1))
        notes.append(f"blocking={n}")
        if n != 0:
            return False, "；".join(notes)

    if "不通过" in text:
        return False, "；".join(notes) + "；结论为不通过"
    if "结论" in text and "通过" in text:
        return True, "；".join(notes) or "结论含通过"
    return False, "未找到可判定的指标或结论"


def check_watch_review(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    notes = []
    if "blocking" in text.lower() and re.search(
        r"blocking[^\n]{0,12}?[:：]\s*[1-9]", text, re.IGNORECASE
    ):
        return False, "存在 blocking"
    if "不通过" in text:
        return False, "结论为不通过"
    if "结论" in text and "通过" in text:
        return True, "结论含通过"
    return False, "未找到通过结论"


def check_deps(root: Path) -> tuple[bool, list[str]]:
    km = root / "content" / "knowledge-map.md"
    if not km.exists():
        return False, ["找不到 knowledge-map.md"]
    text = km.read_text(encoding="utf-8", errors="replace")
    edges = re.findall(r"(K-\d+-\d+)\s*依赖\s*(K-\d+-\d+)", text)
    if not edges:
        return True, ["未找到依赖边（若课程无先修关系可忽略）"]

    graph: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)

    state: dict[str, int] = {}
    cycles: list[str] = []

    def dfs(node: str, stack: list[str]) -> None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt, 0) == 0:
                dfs(nxt, stack)
            elif state.get(nxt) == 1 and nxt in stack:
                idx = stack.index(nxt)
                cycles.append(" -> ".join(stack[idx:] + [nxt]))
        stack.pop()
        state[node] = 2

    for node in list(graph):
        if state.get(node, 0) == 0:
            dfs(node, [])

    if cycles:
        return False, [f"依赖成环: {c}" for c in cycles]
    return True, [f"依赖边 {len(edges)} 条，无环"]


def main() -> int:
    parser = argparse.ArgumentParser(description="阶段门禁检查")
    parser.add_argument("project", help="工程根目录")
    parser.add_argument("--episode", default="EP01", help="集号，如 EP01")
    parser.add_argument("--stage", required=True, help="S0/S1/S1.5/.../S9")
    parser.add_argument("--check-deps", action="store_true", help="额外检查知识图谱依赖环")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    stage = args.stage.upper()
    if stage not in STAGE_REQUIRED:
        print(f"[ERROR] 未知阶段: {stage}")
        return 2

    print(f"# 门禁 {stage} / {args.episode}")
    print()

    ok = True
    for pattern in STAGE_REQUIRED[stage]:
        rel = expand(pattern, args.episode)
        if "*" in rel:
            hit = latest(root, rel)
            if hit:
                print(f"  [OK]   {hit.relative_to(root)}")
            else:
                print(f"  [MISS] {rel}")
                ok = False
        else:
            p = root / rel
            if p.exists() and (p.is_dir() or p.stat().st_size > 0):
                extra = "" if p.is_dir() else f" ({p.stat().st_size} bytes)"
                print(f"  [OK]   {rel}{extra}")
            else:
                print(f"  [MISS] {rel}")
                ok = False

    if stage == "S5":
        hit = latest(root, f"reviews/{args.episode}-author.md")
        if hit:
            passed, note = check_author_review(hit)
            print(f"  [{('OK' if passed else 'FAIL')}] 审稿结论: {note}")
            ok = ok and passed

    if stage == "S6":
        hit = latest(root, f"reviews/{args.episode}-learner-r*.md")
        if hit:
            passed, note = check_learner_review(hit)
            print(f"  [{('OK' if passed else 'FAIL')}] 试读结论: {note}")
            ok = ok and passed

    if stage == "S8":
        hit = latest(root, f"reviews/{args.episode}-watch-r*.md")
        if hit:
            passed, note = check_watch_review(hit)
            print(f"  [{('OK' if passed else 'FAIL')}] 试看结论: {note}")
            ok = ok and passed

    if args.check_deps:
        passed, notes = check_deps(root)
        for n in notes:
            print(f"  [{('OK' if passed else 'FAIL')}] {n}")
        ok = ok and passed

    print()
    if ok:
        print(f"结论: 通过 -> {NEXT_STEP.get(stage, '继续')}")
    else:
        print("结论: 不通过 -> 补齐缺失产物或修改后重跑")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
