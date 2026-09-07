# shanw-skillHub

个人 skill 收录仓库。skill 是 Claude Code 的可复用指令包（`SKILL.md` + 辅助文件）；本仓库每个子目录是一个独立可取的 skill，结构统一、带审查闸门，可单独复制到其他环境使用，也可用 skill-create 继续生产新 skill。

## Skill 一览（路由表）

| skill | 目录 | 用途 | 触发词（节选） |
|---|---|---|---|
| skill-create | [skill_create/](skill_create/) | Skill 生产专家：把可复用场景制作成完整、可执行、带审查闸门的 skill。本仓库其他 skill 的生产工具，是仓库的元 skill | 「帮我把这个场景做成 skill」「做一个 XX 的 skill」 |
| job-intel | [job_search/](job_search/) | 销售求职背景调查：对目标公司生成求职情报手册（HTML 为主 + md 配对） | 「对 XX 公司做背景调查（求职用）」「研究 XX 公司准备面试」 |

## 各 skill 详情

### skill-create — Skill 生产专家

- 定位：理解「可复用场景」描述，按 job-intel 设计思想生产完整 skill；先做十要素完整性核查与双方核对，再进入细节设计。本仓库后续 skill 均由此生产
- 入口：[skill_create/SKILL.md](skill_create/SKILL.md)
- 校验脚本：[skill_create/scripts/skill_audit.py](skill_create/scripts/skill_audit.py)（交付前自审闸门自动化部分，仅标准库）
- 设计思想：[skill_create/references/golden-example.md](skill_create/references/golden-example.md)（job-intel 八项机制提炼）
- 关系：通用可复用场景归本 skill；飞书 API 封装走 lark-skill-maker；设计思想对齐 job-intel

### job-intel — 销售求职背景调查

- 定位：资深 B2B 销售求职者对目标公司的背景调查，产出固定八章结构情报手册；全程口径标注，外部求职者视角。本仓库第一个 skill，是 skill-create 设计思想的对齐对象
- 入口：[job_search/SKILL.md](job_search/SKILL.md)
- 校验脚本：[job_search/scripts/review_gate.py](job_search/scripts/review_gate.py)（输出审查闸门自动化部分，仅标准库）
- 完整示例：[job_search/references/example-volcano-engine.html](job_search/references/example-volcano-engine.html)（火山引擎手册 2026-08 版；md 配对见同目录 `example-volcano-engine.md`）
- 关系：取代早期 company-sales-intel（未收录于本仓库），两者同时命中时优先用本 skill

## 使用方式

1. 按上方路由表选择需要的 skill
2. 复制整个目录到目标环境：
   - Claude Code 个人级：`~/.claude/skills/<skill-name>/`
   - 项目级：`<project>/.claude/skills/<skill-name>/`
3. 在本仓库工作区中也可直接使用

## 收录标准与维护约定

- 统一目录结构：`SKILL.md` + `scripts/`（校验脚本仅 Python 标准库）+ `references/` + `logs/`
- 每个 skill 满足 skill-create 十要素：场景用途、触发词、目标用户与视角、工作流步骤、固定产出结构、审查闸门规则、内容铁律、边界、参考示例、与既有 skill 的关系
- 目录名与 frontmatter `name` 保持一致（`job_search` 为历史命名）
- 新 skill 收录：根目录建 `<skill-name>/`，并同步更新本 README 的路由表与详情节
- 生产新 skill 用 skill-create：先完整性核查与双方核对，再细节设计，交付前过自审闸门
