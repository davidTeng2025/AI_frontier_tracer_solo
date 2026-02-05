---
name: whats-new-in-ai-skill
description: 独立封装的「AI 前沿信息追踪系统（产品君）」skill。从 Coze 同步视频列表、提取文案、LLM 结构化分析写入 tech_insights，支持按技术维度查询时间轴、清空本地 SQLite。在用户询问 AI 前沿动态、产品君视频、技术洞察时间轴时使用本 skill。
---

# whatsNewInAi Skill
自动化追踪抖音"产品君"账号视频，抽取文案并用 LLM 生成"技术进化节点"，支持按技术维度查询时间轴脉络。

## Quick Start

### 一键脚本（推荐）

```bash
# 安装依赖
bash scripts/install_deps.sh

# 快速测试（TEST_MODE=true）
bash scripts/run_test.sh

# 全量运行
bash scripts/run_full.sh
```

### 手动运行

```bash
# 1. 安装依赖
pip install -r scripts/requirements.txt

# 2. 配置（编辑 scripts/config.json）
#    - OPENAI_API_KEY: 可选，不填则跳过 LLM 分析
#    - TEST_MODE: true=快速测试，false=全量运行

# 3. 运行主流程
cd scripts
export DB_PATH="../assets/data.db"
python main.py
```

## Common Operations

### 查询技术维度时间轴

```bash
# 查看支持的维度
bash scripts/list_dimensions.sh

# 查询指定维度的时间轴（示例）
bash scripts/timeline.sh "LLM"
bash scripts/timeline.sh "AI编程/Vibe Coding" 50
```

### 清空数据库

```bash
# 清空默认数据库（assets/data.db）
bash scripts/clear_db.sh

# 清空指定数据库
bash scripts/clear_db.sh assets/data.test.db
```

## Workflow Stages

1. **同步** (`[sync]`): 从 Coze workflow 获取视频列表，写入 `raw_sources`
2. **提取** (`[extract]`): 提取视频文案，更新 `raw_sources.content_text`
3. **分析** (`[analyze]`): LLM 结构化分析，生成 `tech_insights`

## 数据与配置位置

- **数据库**：`assets/data.db`（默认，初始可从 ai-frontier-tracker 等上游复制）；测试库 `assets/data.test.db`
- **配置**：`scripts/config.json`（全量）、`scripts/config.test.json`（测试）
- **参考文档**：`references/REFERENCE.md`、`references/LLM技术演进总结.md`

## Additional Resources

- 详细配置和故障排查：见 [references/REFERENCE.md](references/REFERENCE.md)


