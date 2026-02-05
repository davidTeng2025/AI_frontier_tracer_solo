# Reference: whatsNewInAi Skill

## 独立性说明

本 skill 为 **whatsNewInAi** 的完整独立副本：

- 所有 Python 脚本位于 `scripts/`，可独立使用，不依赖上游项目
- 配置：`scripts/config.json`、`scripts/config.test.json`
- 数据库：`assets/data.db`（默认）、`assets/data.test.db`（测试）
- Coze 调用参数在 `scripts/utils.py` 中（token/workflow_id 需自行配置）

## Configuration

编辑 `scripts/config.json`：

```json
{
  "OPENAI_API_KEY": "sk-xxx",
  "OPENAI_BASE_URL": "https://api.openai.com/v1",
  "OPENAI_MODEL": "gpt-4o",
  "TEST_MODE": false,
  "EXTRACT_WORKERS": 5,
  "ANALYZE_WORKERS": 5,
  "EXTRACT_LIMIT": 200,
  "WINDOW_SIZE": 20
}
```

- **OPENAI_API_KEY** 为空则跳过阶段 3（LLM 分析）
- **TEST_MODE**：true=快速测试，false=全量运行

## Database Locations

- 正式库：`assets/data.db`（初始可从 ai-frontier-tracker 等上游复制）
- 测试库：`assets/data.test.db`

## Data Model

### raw_sources

| 字段 | 类型 | 说明 |
|------|------|------|
| source_id | TEXT PRIMARY KEY | 来源唯一 ID（aweme_id） |
| title | TEXT | 标题 |
| publish_time | INTEGER | 发布时间戳 |
| source_url | TEXT | 来源链接 |
| content_text | TEXT | 原始文案 |
| process_status | TEXT | pending/text_extracted/analyzed/error |
| is_top | INTEGER | 1=置顶，0=普通 |

### tech_insights

| 字段 | 类型 | 说明 |
|------|------|------|
| insight_id | INTEGER PRIMARY KEY | 自增 ID |
| source_id | TEXT | 关联 raw_sources.source_id |
| dimension | TEXT NOT NULL | 技术维度 |
| project_name | TEXT | 项目/产品名 |
| tech_node | TEXT | 核心进化点 |
| evolution_tag | TEXT | 标签 |
| impact_score | INTEGER | 影响力 1-5 |
| summary | TEXT | 摘要 |

## Useful SQL

按维度时间轴（旧→新）：

```sql
SELECT s.publish_time, i.project_name, i.tech_node, i.evolution_tag
FROM tech_insights i
JOIN raw_sources s ON i.source_id = s.source_id
WHERE i.dimension = 'AI编程/Vibe Coding'
ORDER BY s.publish_time ASC;
```

## Scripts 一览

| 脚本 | 说明 |
|------|------|
| main.py | 主流程：同步→提取→分析 |
| query_tech_insights.py | 按维度查时间轴、--list-dimensions |
| clear_db_data.py | 清空表数据（保留表结构） |
| install_deps.sh | pip install -r requirements.txt |
| run_full.sh | 全量运行（config.json + assets/data.db） |
| run_test.sh | 测试运行（config.test.json + assets/data.test.db） |
| list_dimensions.sh | 列出支持的维度 |
| timeline.sh | 查询某维度时间轴 |
| clear_db.sh | 清空指定或默认 DB |
