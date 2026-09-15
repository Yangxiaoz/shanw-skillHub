# shanw-skillHub

个人 skill 收录仓库。skill 是 agent 工具的可复用指令包（`SKILL.md` + 辅助文件），格式通用、不绑定具体工具；本仓库每个 skill 子目录是一个独立可取的 skill，结构统一、带审查闸门，可单独复制到任意 agent 工具使用。仓库根 `scripts/` 存放仓库级维护脚本，不属于任何 skill。

## Skill 一览（路由表）

| skill | 目录 | 用途 | 触发词（节选） | 最近更新 |
|---|---|---|---|---|
| job-intel | [job_search/](job_search/) | 销售求职背景调查：对目标公司生成求职情报手册（HTML 为主 + md 配对） | 「对 XX 公司做背景调查（求职用）」「研究 XX 公司准备面试」 | <!-- upd:job_search -->2026-09-07<!-- /upd --> |

## 各 skill 详情

### job-intel — 销售求职背景调查

- 最近更新：<!-- upd:job_search -->2026-09-07（6be78d2）<!-- /upd -->
- 定位：资深 B2B 销售求职者对目标公司的背景调查，产出固定八章结构情报手册；全程口径标注，外部求职者视角
- 入口：[job_search/SKILL.md](job_search/SKILL.md)
- 校验脚本：[job_search/scripts/review_gate.py](job_search/scripts/review_gate.py)（输出审查闸门自动化部分，仅标准库）
- 完整示例：[job_search/references/example-volcano-engine.html](job_search/references/example-volcano-engine.html)（火山引擎手册 2026-08 版；md 配对见同目录 `example-volcano-engine.md`）
- 关系：取代早期 company-sales-intel（未收录于本仓库），两者同时命中时优先用本 skill

## 使用方式

1. 按上方路由表选择需要的 skill
2. 把整个目录复制到目标 agent 工具的 skill 目录，一般分两级：
   - 个人级：对该工具全局生效
   - 项目级：仅对当前项目生效

   具体路径各工具自有约定，以所用工具的文档为准
3. 在本仓库工作区中也可直接使用

## 收录标准与维护约定

- 统一目录结构：`SKILL.md` + `scripts/`（校验脚本仅 Python 标准库）+ `references/` + `logs/`
- 结构自审：收录前跑 `python scripts/skill_audit.py --skill-dir <skill-name>`，有 fail 不得收录；「skill 该有哪些章节」以该脚本为准，本 README 不另立一份
- 目录名与 frontmatter `name` 保持一致（`job_search` 为历史命名）
- 新 skill 收录：根目录建 `<skill-name>/`，在 README 路由表与详情节各加一处 `<!-- upd:<dir> -->…<!-- /upd -->` 标记，然后跑 `python scripts/update_index.py`
- 修改已有 skill 后：跑 `python scripts/update_index.py` 刷新更新时间，与改动一起提交
- 更新时间由 `scripts/update_index.py` 从 git 提交时间生成，标记内的日期禁止手工编辑
