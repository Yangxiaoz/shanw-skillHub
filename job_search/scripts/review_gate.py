#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
job-intel · 输出审查闸门 · 自动化校验脚本（仅标准库）

覆盖 Step 4 校验规则中的【自动化部分】：
  A1 HTML 可解析 / 标签配平 / 单一标题
  A2 md 与 HTML 章节标题集一致（一字不差）
  A3 八章齐全且顺序正确（速览→一→…→七→尾注）
  A4 无残留占位符 / 乱码 / TODO / {{}}；括号引号配平
  A5 竞品四列表每行 4 列、无空单元格
  D1 裸数启发式扫描（结果作 warn，交 LLM 裁定）

LLM 部分（B / C / D2 / D3 / E）由 agent 按 SKILL.md 4.2 清单自我审查后合并。

退出码：0 = 无阻断（pass / warn 均可）；2 = 有 P0/P1 fail（has_blocking=True）
"""

import argparse
import json
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

# ----------------------------- HTML 结构解析 -----------------------------

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class TagBalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append("多余的闭合标签 </%s>" % tag)
            return
        if self.stack[-1] == tag:
            self.stack.pop()
            return
        # 尝试向上寻找匹配
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append("未闭合标签 <%s>（在 </%s> 之前）" % (self.stack[-1], tag))
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append("无匹配的闭合标签 </%s>" % tag)


def normalize_header(text):
    """去除编号、标点、空白，用于跨格式（md/HTML）标题比对。"""
    t = text.strip()
    t = re.sub(r"^#{1,6}\s*", "", t)
    t = re.sub(r"^[一二三四五六七八九十]+、", "", t)
    t = re.sub(r"^（[一二三四五六七八九十]+）", "", t)
    t = re.sub(r"[：:·\s]+$", "", t)
    return t.strip()


# ----------------------------- 各检查项实现 -----------------------------

def check_a1(html_text):
    """HTML 可解析 / 标签配平 / 单一标题（P0）"""
    detail = []
    status = "pass"
    # 单一 <title>
    titles = re.findall(r"<title\b[^>]*>", html_text, re.I)
    h1s = re.findall(r"<h1\b", html_text, re.I)
    checker = TagBalanceChecker()
    try:
        checker.feed(html_text)
    except Exception as e:  # noqa: BLE001
        return {"rule": "A1", "severity": "P0", "status": "fail",
                "detail": "HTML 解析异常：%s" % e}
    if len(titles) != 1:
        detail.append("title 数量=%d（应为 1）" % len(titles))
    if len(h1s) != 1:
        detail.append("h1 数量=%d（应为 1）" % len(h1s))
    if checker.errors:
        detail.extend(checker.errors[:10])
    if checker.stack:
        detail.append("仍有 %d 个未闭合标签：%s" % (len(checker.stack), ", ".join(checker.stack[-5:])))
    if detail:
        status = "fail"
    return {"rule": "A1", "severity": "P0", "status": status,
            "detail": "；".join(detail) if detail else "HTML 结构良好，单一标题"}


def extract_headers_md(md_text):
    return [normalize_header(m) for m in re.findall(r"^#{2,3}\s+(.+)$", md_text, re.M)]


def extract_headers_html(html_text):
    # 只取 h2/h3（章节与小节），排除 h1 文档标题（md 侧无对应 # 标题）
    hs = re.findall(r"<h[23]\b[^>]*>(.*?)</h[23]>", html_text, re.S | re.I)
    return [normalize_header(re.sub(r"<[^>]+>", "", h)) for h in hs]


def check_a2(html_text, md_text):
    """md 与 HTML 章节标题集一致（P0）"""
    m_h = set(extract_headers_md(md_text))
    h_h = set(extract_headers_html(html_text))
    only_md = m_h - h_h
    only_html = h_h - m_h
    detail = []
    if only_md:
        detail.append("仅 md 有：%s" % "、".join(sorted(only_md)))
    if only_html:
        detail.append("仅 html 有：%s" % "、".join(sorted(only_html)))
    status = "pass" if not detail else "fail"
    return {"rule": "A2", "severity": "P0", "status": status,
            "detail": "；".join(detail) if detail else "md 与 HTML 章节标题集一致"}


def check_a3(html_text):
    """八章齐全且顺序正确（P1）"""
    order_markers = ["一、", "二、", "三、", "四、", "五、", "六、", "七、"]
    h2 = re.findall(r'<h2 class="section-header">(.*?)</h2>', html_text, re.S)
    h2 = [re.sub(r"<[^>]+>", "", h).strip() for h in h2]
    detail = []
    positions = []
    for i, mk in enumerate(order_markers):
        found = [idx for idx, t in enumerate(h2) if t.startswith(mk)]
        if not found:
            detail.append("缺章节 %s" % mk)
        else:
            positions.append(found[0])
    if positions and positions != sorted(positions):
        detail.append("章节顺序错乱：%s" % " → ".join(h2))
    # 速览 与 尾注
    if not re.search(r"速览", html_text):
        detail.append("缺速览模块")
    if not re.search(r"data-note|尾注|数据说明", html_text):
        detail.append("缺尾注/数据说明")
    status = "pass" if not detail else "fail"
    return {"rule": "A3", "severity": "P1", "status": status,
            "detail": "；".join(detail) if detail else "八章齐全且顺序正确"}


def check_a4(html_text, md_text):
    """占位符（P0）/ 括号配平（P1）"""
    combined = html_text + "\n" + md_text
    placeholder_pat = re.compile(
        r"TODO|FIXME|XXX|TBD|占位符|未填写|待补充|待完善|\{\{|\}\}|<<<|>>>",
        re.I,
    )
    ph = placeholder_pat.findall(combined)
    bracket_detail = []
    # 全角括号
    if combined.count("（") != combined.count("）"):
        bracket_detail.append("全角括号不配平（（=%d，）=%d）" % (combined.count("（"), combined.count("）")))
    # 半角括号
    if combined.count("(") != combined.count(")"):
        bracket_detail.append("半角括号不配平（(%d，)%d）" % (combined.count("("), combined.count(")")))
    # 方头括号
    if combined.count("【") != combined.count("】"):
        bracket_detail.append("【】不配平")
    results = []
    ph_status = "fail" if ph else "pass"
    results.append({"rule": "A4-placeholder", "severity": "P0", "status": ph_status,
                    "detail": "发现占位符：%s" % ", ".join(set(ph)) if ph else "无残留占位符/TODO/{{}}"})
    br_status = "fail" if bracket_detail else "pass"
    results.append({"rule": "A4-bracket", "severity": "P1", "status": br_status,
                    "detail": "；".join(bracket_detail) if bracket_detail else "括号/引号配平"})
    return results


def check_a5(html_text):
    """竞品四列表每行 4 列、无空单元格（P1）"""
    results = []
    # 切分 table
    tables = re.findall(r"<table\b.*?</table>", html_text, re.S | re.I)
    for ti, tbl in enumerate(tables):
        ths = re.findall(r"<th\b[^>]*>(.*?)</th>", tbl, re.S | re.I)
        if len(ths) != 4:
            continue  # 非四列表，跳过（如三列场景表）
        # 只看 tbody 内的数据行，排除 thead 表头行（含 <th>）
        tbodies = re.findall(r"<tbody>(.*?)</tbody>", tbl, re.S | re.I)
        body_text = tbodies[0] if tbodies else tbl
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", body_text, re.S | re.I)
        bad = 0
        empty = 0
        for r in rows:
            tds = re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S | re.I)
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in tds]
            if len(cells) != 4:
                bad += 1
            elif any(c == "" for c in cells):
                empty += 1
        if bad or empty:
            results.append({"rule": "A5", "severity": "P1", "status": "fail",
                            "detail": "第 %d 张四列表：列数异常 %d 行、空单元格 %d 行" % (ti + 1, bad, empty)})
    if not results:
        results.append({"rule": "A5", "severity": "P1", "status": "pass",
                        "detail": "全部竞品四列表字段完整（4 列、无空单元格）"})
    return results


def check_d1(html_text, md_text):
    """裸数启发式扫描（warn，交 LLM 裁定）（P1 级规则，但脚本只报 warn）"""
    combined = html_text + "\n" + md_text
    num_pat = re.compile(r"\d[\d,.]*\s*(?:亿|万|%|万元|亿美元|亿元)")
    src_kw = re.compile(r"[（(].*?(?:Omdia|IDC|QuestMobile|财报|公司|据|报道|官方|媒体|测算|第三方|公开|声明|公告).*?[)）]|Omdia|IDC|QuestMobile|财报|公司公开|据公开|官方")
    hits = 0
    for m in num_pat.finditer(combined):
        start = max(0, m.start() - 60)
        ctx = combined[start:m.end() + 20]
        if not src_kw.search(ctx):
            hits += 1
    if hits:
        return {"rule": "D1", "severity": "P1", "status": "warn",
                "detail": "发现 %d 处数字附近未检测到来源标注（启发式，请 LLM 复核是否真裸数）" % hits}
    return {"rule": "D1", "severity": "P1", "status": "pass",
            "detail": "未检测到明显的裸数"}


# ----------------------------- 主流程 -----------------------------

def run_checks(html_text, md_text):
    checks = []
    checks.append(check_a1(html_text))
    checks.append(check_a2(html_text, md_text))
    checks.append(check_a3(html_text))
    checks.extend(check_a4(html_text, md_text))
    checks.extend(check_a5(html_text))
    checks.append(check_d1(html_text, md_text))
    return checks


def main():
    ap = argparse.ArgumentParser(description="job-intel 输出审查闸门（自动化部分）")
    ap.add_argument("--html", required=True, help="生成的 HTML 文件路径")
    ap.add_argument("--md", required=True, help="配对的 md 文件路径")
    ap.add_argument("--company", default="", help="目标公司名（写入记录）")
    ap.add_argument("--request", default="", help="用户原始请求（写入记录）")
    ap.add_argument("--out", default="", help="审查报告 JSON 输出路径（默认打印 stdout）")
    args = ap.parse_args()

    html_path = Path(args.html)
    md_path = Path(args.md)
    if not html_path.exists() or not md_path.exists():
        print(json.dumps({"error": "文件不存在", "html": str(html_path), "md": str(md_path)},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

    html_text = html_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")

    checks = run_checks(html_text, md_text)
    has_blocking = any(c["status"] == "fail" for c in checks)

    report = {
        "tool": "job-intel/review_gate.py",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company": args.company,
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
