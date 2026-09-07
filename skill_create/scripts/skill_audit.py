#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-create · 交付前自审闸门 · 自动化校验脚本（仅标准库）

校验一个产出的 skill 目录，覆盖 SKILL.md Step 5 的【A 类】规则：
  A1 SKILL.md 存在；frontmatter 完整（name/title/description 非空）
  A2 必备章节齐全且顺序正确（触发词 → 工作流 → 内容铁律 → 参考文件 → 与既有 skill 的关系）
  A3 审查闸门完整（工作流内含「审查闸门」+ P0/P1 分级 + 降级方案）
  A4 无残留占位符 / TODO / {{}}；括号配平
  A5 SKILL.md 引用的本地脚本 / 参考文件实际存在
  A6 引用的 Python 脚本可编译

注：A4 占位符检测跳过含「占位符」一词的规则定义行（闸门规则描述里
    合法写着 TODO / {{}} 这类字样），只匹配强信号形式：
    {{xxx}} 非空模板 / TODO： / FIXME： / TBD： / 未填写 / 待补充 / 待完善 / <<< / >>>。

LLM 部分（B / C / D / E）由 agent 按 SKILL.md 5.2 清单自我审查后合并。

退出码：0 = 无阻断（pass / warn 均可）；2 = 有 fail（has_blocking=True）
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REQUIRED_SECTIONS = ["触发词", "工作流", "内容铁律", "参考文件", "与既有 skill 的关系"]


def _norm(s):
    return re.sub(r"\s", "", s)


def extract_h2(text):
    """提取 ## 标题（去空白），用于章节顺序比对。"""
    return [_norm(h.strip()) for h in re.findall(r"^##\s+(.+)$", text, re.M)]


# ----------------------------- 各检查项实现 -----------------------------

def check_a1(text):
    """SKILL.md 存在 + frontmatter 完整（P0）"""
    if text is None:
        return {"rule": "A1", "severity": "P0", "status": "fail",
                "detail": "SKILL.md 不存在"}
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not fm:
        return {"rule": "A1", "severity": "P0", "status": "fail",
                "detail": "frontmatter 缺失（文件必须以 --- 开头）"}
    body = fm.group(1)
    detail = []
    for key in ("name", "title", "description"):
        m = re.search(r"^%s:\s*(\S.*)$" % key, body, re.M)
        if not m or not m.group(1).strip():
            detail.append("frontmatter 缺 %s" % key)
    if detail:
        return {"rule": "A1", "severity": "P0", "status": "fail",
                "detail": "；".join(detail)}
    return {"rule": "A1", "severity": "P0", "status": "pass",
            "detail": "SKILL.md 存在，frontmatter 完整"}


def check_a2(text):
    """必备章节齐全且顺序正确（P1）"""
    h2 = extract_h2(text)
    detail = []
    positions = []
    for sec in REQUIRED_SECTIONS:
        found = [i for i, h in enumerate(h2) if h.startswith(_norm(sec))]
        if not found:
            detail.append("缺章节「%s」" % sec)
        else:
            positions.append(found[0])
    if positions and positions != sorted(positions):
        detail.append("章节顺序错乱：%s" % " → ".join(h2))
    status = "fail" if detail else "pass"
    return {"rule": "A2", "severity": "P1", "status": status,
            "detail": "；".join(detail) if detail else "必备章节齐全且顺序正确"}


def check_a3(text):
    """审查闸门完整（P0）：含审查闸门步骤 + P0/P1 分级 + 降级方案"""
    detail = []
    if "审查闸门" not in text:
        detail.append("缺「审查闸门」步骤")
    if not re.search(r"\bP0\b", text):
        detail.append("缺 P0 分级")
    if not re.search(r"\bP1\b", text):
        detail.append("缺 P1 分级")
    if "降级" not in text:
        detail.append("缺降级输出方案")
    status = "fail" if detail else "pass"
    return {"rule": "A3", "severity": "P0", "status": status,
            "detail": "；".join(detail) if detail else "审查闸门完整（含分级与降级方案）"}


def check_a4(text):
    """占位符（P0）/ 括号配平（P1）

    占位符检测跳过含「占位符」一词的规则定义行——SKILL.md 的闸门规则
    描述里合法地写着 TODO / {{}} 这类字样，不能自伤。真实残留占位符
    一般有具体内容（如 {{公司名}}、TODO：补数据），匹配强信号形式。
    """
    lines = [l for l in text.split("\n") if "占位符" not in l]
    body = "\n".join(lines)
    placeholder_pat = re.compile(
        r"\{\{[^{}\n]+\}\}|TODO[:：]|FIXME[:：]|TBD[:：]|未填写|待补充|待完善|<<<|>>>",
        re.I,
    )
    ph = placeholder_pat.findall(body)
    bracket_detail = []
    if text.count("（") != text.count("）"):
        bracket_detail.append("全角括号不配平（（=%d，）=%d）" % (text.count("（"), text.count("）")))
    if text.count("(") != text.count(")"):
        bracket_detail.append("半角括号不配平（(%d，)%d）" % (text.count("("), text.count(")")))
    if text.count("【") != text.count("】"):
        bracket_detail.append("【】不配平")
    results = []
    ph_status = "fail" if ph else "pass"
    results.append({"rule": "A4-placeholder", "severity": "P0", "status": ph_status,
                    "detail": "发现占位符：%s" % ", ".join(sorted(set(ph))) if ph else "无残留占位符/TODO/{{}}"})
    br_status = "fail" if bracket_detail else "pass"
    results.append({"rule": "A4-bracket", "severity": "P1", "status": br_status,
                    "detail": "；".join(bracket_detail) if bracket_detail else "括号配平"})
    return results


def check_a5(text, skill_dir):
    """SKILL.md 引用的本地脚本 / 参考文件实际存在（P0）"""
    # 排除 ../ 外部引用与目录名（如 scripts/ 裸目录）
    refs = set(re.findall(r"(?<![\w./])(?:scripts|references)/[\w\-.]+", text))
    missing = [r for r in refs if not (skill_dir / r).exists()]
    if missing:
        return {"rule": "A5", "severity": "P0", "status": "fail",
                "detail": "引用文件不存在：%s" % "、".join(sorted(missing))}
    return {"rule": "A5", "severity": "P0", "status": "pass",
            "detail": "引用的本地文件均存在（共 %d 个）" % len(refs)}


def check_a6(skill_dir):
    """引用的 Python 脚本可编译（P0）"""
    scripts_dir = skill_dir / "scripts"
    scripts = sorted(scripts_dir.glob("*.py")) if scripts_dir.exists() else []
    bad = []
    for p in scripts:
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            bad.append("%s：%s" % (p.name, e))
    if bad:
        return {"rule": "A6", "severity": "P0", "status": "fail",
                "detail": "脚本语法错误：%s" % "；".join(bad)}
    return {"rule": "A6", "severity": "P0", "status": "pass",
            "detail": "%d 个 Python 脚本可编译" % len(scripts)}


# ----------------------------- 主流程 -----------------------------

def run_checks(skill_dir):
    p = skill_dir / "SKILL.md"
    text = p.read_text(encoding="utf-8") if p.exists() else None
    checks = [check_a1(text)]
    if text is not None:
        checks.append(check_a2(text))
        checks.append(check_a3(text))
        checks.extend(check_a4(text))
        checks.append(check_a5(text, skill_dir))
        checks.append(check_a6(skill_dir))
    return checks


def main():
    ap = argparse.ArgumentParser(description="skill-create 交付前自审闸门（自动化部分）")
    ap.add_argument("--skill-dir", required=True, help="待审查的 skill 目录路径")
    ap.add_argument("--skill-name", default="", help="skill 名（写入记录）")
    ap.add_argument("--request", default="", help="用户原始请求（写入记录）")
    ap.add_argument("--out", default="", help="审查报告 JSON 输出路径（默认打印 stdout）")
    args = ap.parse_args()

    skill_dir = Path(args.skill_dir)
    if not skill_dir.exists():
        print(json.dumps({"error": "目录不存在", "skill_dir": str(skill_dir)},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

    checks = run_checks(skill_dir)
    has_blocking = any(c["status"] == "fail" for c in checks)

    report = {
        "tool": "skill-create/skill_audit.py",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "skill_dir": str(skill_dir),
        "skill_name": args.skill_name,
        "request": args.request,
        "has_blocking": has_blocking,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "warn": sum(1 for c in checks if c["status"] == "warn"),
            "fail": sum(1 for c in checks if c["status"] == "fail"),
        },
    }

    out_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(out_json, encoding="utf-8")
        print("审查报告已写入：%s" % args.out, file=sys.stderr)
    else:
        print(out_json)

    sys.exit(2 if has_blocking else 0)


if __name__ == "__main__":
    main()
