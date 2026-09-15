#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skillHub · 更新时间索引 · 从 git 提交时间刷新 README 的「最近更新」（仅标准库）

对仓库根下每个含 SKILL.md 的 skill 目录，取其最后一次提交时间，写回 README 中
以目录名为键的标记位置：

    <!-- upd:job_search -->2026-09-07<!-- /upd -->

同一处标记按所在行自动选择呈现格式：
  表格行内     → 2026-09-07
  其余（详情节）→ 2026-09-07（6be78d2）

目录存在未提交改动时，按当前日期并标注未提交，不把工作区状态冒充成提交时间。

用法：
    python scripts/update_index.py            # 刷新 README
    python scripts/update_index.py --check    # 只比对不写入（提交前核验）

退出码：0 = README 与 git 一致且无异常；1 = 有待刷新内容或存在标记异常
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# 不属于 skill 的根级目录；点开头的隐藏目录（工具自身的配置目录等）一律跳过
SKIP_DIRS = {"scripts", "node_modules"}

# <!-- upd:<dir> -->值<!-- /upd -->
MARKER_RE = re.compile(r"(<!--\s*upd:([\w\-.]+)\s*-->)(.*?)(<!--\s*/upd\s*-->)")


def git(args, cwd):
    """跑一条 git 命令，返回 stripped stdout；失败返回空串。"""
    try:
        r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_root():
    out = git(["rev-parse", "--show-toplevel"], Path.cwd())
    if not out:
        print("错误：当前目录不在 git 仓库中（或未安装 git）", file=sys.stderr)
        sys.exit(2)
    return Path(out)


def discover_skills(root):
    """仓库根下含 SKILL.md 的目录名，即 skill 目录名。"""
    return sorted(p.parent.name for p in root.glob("*/SKILL.md")
                  if p.parent.name not in SKIP_DIRS
                  and not p.parent.name.startswith("."))


def skill_labels(root, name):
    """返回该 skill 目录在两种格式下应显示的文本。"""
    iso = git(["log", "-1", "--format=%cI", "--", name], root)
    short = git(["log", "-1", "--format=%h", "--", name], root)
    dirty = bool(git(["status", "--porcelain", "--", name], root))

    if dirty:
        today = date.today().isoformat()
        return today + "*", "%s（未提交）" % today
    if not iso:
        return "—", "未提交（无提交记录）"
    day = iso[:10]
    return day, "%s（%s）" % (day, short)


def refresh_text(text, labels):
    """逐行替换标记内的值；表格行用紧凑格式，其余用完整格式。"""
    out = []
    for line in text.splitlines(keepends=True):
        compact = line.lstrip().startswith("|")

        def repl(m):
            key = m.group(2)
            if key not in labels:
                return m.group(0)
            value = labels[key][0 if compact else 1]
            return "%s%s%s" % (m.group(1), value, m.group(4))

        out.append(MARKER_RE.sub(repl, line))
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(
        description="skillHub 更新时间索引：从 git 提交时间刷新 README 的「最近更新」")
    ap.add_argument("--check", action="store_true",
                    help="只比对不写入（提交前核验，有差异则退出码 1）")
    ap.add_argument("--readme", default="README.md", help="README 路径（默认仓库根 README.md）")
    args = ap.parse_args()

    root = repo_root()
    readme = root / args.readme
    if not readme.exists():
        print("错误：找不到 %s" % readme, file=sys.stderr)
        sys.exit(2)

    # newline="" 读写：原样保留 README 的换行符，避免 Windows 上被改写成 CRLF
    with open(readme, "r", encoding="utf-8", newline="") as f:
        original = f.read()

    skills = discover_skills(root)
    if not skills:
        print("警告：仓库根下没有找到含 SKILL.md 的 skill 目录", file=sys.stderr)

    labels = {name: skill_labels(root, name) for name in skills}

    used = set()
    for line in original.splitlines():
        used.update(m.group(2) for m in MARKER_RE.finditer(line))

    warnings = []
    for name in skills:
        if name not in used:
            warnings.append("skill 目录 %s/ 在 README 中没有 <!-- upd:%s --> 标记，未纳入索引"
                            % (name, name))
    for key in sorted(used - set(skills)):
        warnings.append("README 中的标记 <!-- upd:%s --> 找不到对应 skill 目录" % key)

    new_text = refresh_text(original, labels)
    changed = new_text != original

    for name in skills:
        print("%-20s %s" % (name, labels[name][1]))

    if args.check:
        if changed:
            print("\nREADME 与 git 不一致：请运行 python scripts/update_index.py 刷新后提交")
        else:
            print("\nREADME 已是最新")
    elif changed:
        with open(readme, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        print("\nREADME 已刷新：%s" % readme)
    else:
        print("\nREADME 无变化")

    for w in warnings:
        print("警告：%s" % w, file=sys.stderr)

    sys.exit(1 if (changed or warnings) else 0)


if __name__ == "__main__":
    main()
