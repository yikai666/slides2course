#!/usr/bin/env python3
"""检查讲稿的密度与结构。

用法:
    python check_script.py manuscript/EP01/script.md --minutes 45
    python check_script.py script.md --minutes 45 --json report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CJK = re.compile(r"[\u4e00-\u9fff]")
SENTENCE = re.compile(r"[^。！？!?]+[。！？!?]?")

FORBIDDEN = [
    "显然",
    "易知",
    "不难看出",
    "众所周知",
    "不再赘述",
    "留作练习",
    "略去",
    "自行证明",
]
PLACEHOLDER = ["待补", "待定", "TODO", "TBD", "XXX"]

WHY_MARKERS = [
    "为什么",
    "因为",
    "由于",
    "之所以",
    "原因是",
    "依据",
    "保证了",
    "才能",
    "成立",
    "前提是",
]
CHECK_MARKERS = [
    "想一想",
    "先猜",
    "你来判断",
    "你来选",
    "判断一下",
    "会怎样",
    "会变成什么",
    "停顿",
]
CHECK_PAUSE = re.compile(r"停\s*\d+(?:\.\d+)?\s*秒")

MAX_SENTENCE = 60
MIN_CPM = 180
MAX_CPM = 300
TARGET_CPM = (200, 280)


@dataclass
class Section:
    title: str
    line_no: int
    chars: int = 0
    why: int = 0
    checks: int = 0
    long_sentences: list = field(default_factory=list)
    forbidden: list = field(default_factory=list)
    placeholders: list = field(default_factory=list)


def count_cjk(text: str) -> int:
    return len(CJK.findall(text))


def split_sentences(text: str):
    for m in SENTENCE.finditer(text):
        s = m.group(0).strip()
        if s:
            yield s


def main() -> int:
    parser = argparse.ArgumentParser(description="讲稿密度与结构检查")
    parser.add_argument("script", help="script.md 路径")
    parser.add_argument("--minutes", type=float, required=True, help="目标时长（分钟）")
    parser.add_argument("--json", default=None, help="把结果写成 JSON")
    args = parser.parse_args()

    path = Path(args.script)
    if not path.exists():
        print(f"[ERROR] 找不到文件: {path}")
        return 2

    lines = path.read_text(encoding="utf-8").splitlines()

    sections: list[Section] = []
    current = Section(title="（开头）", line_no=1)
    sections.append(current)

    in_fence = False
    in_ignore = False
    prose_lines: list[tuple[int, str]] = []

    for i, raw in enumerate(lines, start=1):
        if "<!-- check-ignore-start -->" in raw:
            in_ignore = True
            continue
        if "<!-- check-ignore-end -->" in raw:
            in_ignore = False
            continue
        if in_ignore:
            continue
        if raw.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw.startswith("## "):
            current = Section(title=raw[3:].strip(), line_no=i)
            sections.append(current)
            continue
        prose_lines.append((i, raw))

        text = raw.strip()
        if not text:
            continue

        current.chars += count_cjk(text)
        for marker in FORBIDDEN:
            if marker in text:
                current.forbidden.append((i, marker, text))
        for marker in PLACEHOLDER:
            if marker in text:
                current.placeholders.append((i, marker, text))

        current.why += sum(text.count(m) for m in WHY_MARKERS)
        check_hits = sum(text.count(m) for m in CHECK_MARKERS) + len(CHECK_PAUSE.findall(text))
        current.checks += check_hits

        for sent in split_sentences(text):
            if count_cjk(sent) > MAX_SENTENCE:
                current.long_sentences.append((i, count_cjk(sent), sent))

    total_chars = sum(s.chars for s in sections)
    total_why = sum(s.why for s in sections)
    total_checks = sum(s.checks for s in sections)
    total_forbidden = sum(len(s.forbidden) for s in sections)
    total_placeholders = sum(len(s.placeholders) for s in sections)
    all_long = [x for s in sections for x in s.long_sentences]
    total_sentences = sum(
        1 for _, line in prose_lines for _ in split_sentences(line.strip())
    )

    cpm = total_chars / args.minutes if args.minutes > 0 else 0.0
    required_checks = max(1.0, args.minutes / 10.0)

    errors: list[str] = []
    warnings: list[str] = []

    if total_forbidden:
        errors.append(f"禁用词 {total_forbidden} 处（出现的地方就是讲稿的洞）")
    if total_placeholders:
        errors.append(f"占位符 {total_placeholders} 处（未完成稿不允许进 S5）")
    if cpm < MIN_CPM:
        errors.append(f"语速 {cpm:.0f} 字/分钟，低于 {MIN_CPM}，基本是在念提纲")
    elif cpm > MAX_CPM:
        errors.append(f"语速 {cpm:.0f} 字/分钟，高于 {MAX_CPM}，实际念不完")
    elif not (TARGET_CPM[0] <= cpm <= TARGET_CPM[1]):
        warnings.append(f"语速 {cpm:.0f} 字/分钟，建议落在 {TARGET_CPM[0]}–{TARGET_CPM[1]}")
    if total_checks < required_checks:
        errors.append(
            f"检查点 {total_checks} 个，按 {args.minutes:.0f} 分钟至少需要 {required_checks:.0f} 个"
        )
    if total_chars and total_why / (total_chars / 500) < 2:
        warnings.append(
            f"「为什么」密度 {total_why / (total_chars / 500):.1f}/500 字，低于 2，像在报结论"
        )
    if all_long:
        ratio = len(all_long) / max(1, total_sentences)
        if ratio > 0.10:
            errors.append(f"超长句 {len(all_long)} 句，占 {ratio:.0%}，口播会断气")
        else:
            warnings.append(f"超长句 {len(all_long)} 句，占 {ratio:.0%}")

    body = "\n".join(line for _, line in prose_lines)
    if "变式" not in body:
        warnings.append("没有找到「变式」，例题可能只讲了原题")
    if not any(k in body for k in ("检验", "检查", "验证")):
        warnings.append("没有找到结果检验段")

    print(f"# 讲稿检查: {path.name}")
    print()
    print(f"- 目标时长: {args.minutes:g} 分钟")
    print(f"- 中文旁白: {total_chars} 字")
    print(f"- 语速: {cpm:.0f} 字/分钟（建议 {TARGET_CPM[0]}–{TARGET_CPM[1]}）")
    print(f"- 检查点: {total_checks} 个（至少 {required_checks:.0f}）")
    print(f"- 为什么类表述: {total_why} 处")
    print(f"- 超长句: {len(all_long)} / {total_sentences} 句")
    print()

    print("| 段落 | 行 | 字数 | 为什么 | 检查点 | 超长句 |")
    print("| --- | --- | --- | --- | --- | --- |")
    for s in sections:
        if s.chars == 0 and not s.long_sentences:
            continue
        print(
            f"| {s.title} | {s.line_no} | {s.chars} | {s.why} | {s.checks} | {len(s.long_sentences)} |"
        )
    print()

    if errors:
        print("## 不通过")
        for e in errors:
            print(f"- [ERROR] {e}")
    if warnings:
        print("## 提醒")
        for w in warnings:
            print(f"- [WARN] {w}")
    if not errors and not warnings:
        print("## 通过\n- 密度与结构均达标")

    if total_forbidden:
        print("\n## 禁用词位置")
        for s in sections:
            for line_no, marker, text in s.forbidden:
                print(f"- L{line_no} 「{marker}」: {text[:60]}")
    if total_placeholders:
        print("\n## 占位符位置")
        for s in sections:
            for line_no, marker, text in s.placeholders:
                print(f"- L{line_no} 「{marker}」: {text[:60]}")
    if all_long:
        print("\n## 超长句（前 10 条）")
        for line_no, n, sent in all_long[:10]:
            print(f"- L{line_no}（{n} 字）: {sent[:70]}")

    if args.json:
        payload = {
            "script": str(path),
            "minutes": args.minutes,
            "chars": total_chars,
            "cpm": round(cpm, 1),
            "checks": total_checks,
            "why": total_why,
            "long_sentences": len(all_long),
            "forbidden": total_forbidden,
            "placeholders": total_placeholders,
            "errors": errors,
            "warnings": warnings,
            "passed": not errors,
        }
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print()
    print("结论: " + ("通过" if not errors else "不通过"))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
