# AI 前沿信息追踪系统（whatsNewInAi Skill 版）

本目录是 **whatsNewInAi** 的独立 skill 封装：所有脚本、配置、数据均在本目录内，可独立使用，不依赖上游项目路径。

## 目录结构

```
whatsNewInAi_skill/
├── SKILL.md           # Skill 说明（Cursor 用）
├── README.md          # 本说明
├── scripts/           # 全部可执行脚本与配置
│   ├── main.py        # 主流程（同步→提取→分析）
│   ├── config.py      # 配置加载
│   ├── config.json    # 本地配置（需填写 OPENAI_API_KEY 等）
│   ├── config.test.json
│   ├── database.py    # SQLite schema + CRUD
│   ├── sync_engine.py # 同步引擎
│   ├── coze_client.py # Coze workflow 客户端
│   ├── utils.py       # Coze 调用（视频列表/文案提取）
│   ├── analyzer.py    # LLM 分析器
│   ├── clear_db_data.py
│   ├── query_tech_insights.py
│   ├── crawler_one.py
│   ├── requirements.txt
│   ├── install_deps.sh
│   ├── run_full.sh / run_test.sh
│   ├── list_dimensions.sh / timeline.sh / clear_db.sh
├── assets/             # 数据文件（如 data.db）
└── references/        # 参考文档
    ├── REFERENCE.md
    └── LLM技术演进总结.md
```

## 安装与运行

```bash
# 安装依赖
bash scripts/install_deps.sh

# 编辑 scripts/config.json（OPENAI_API_KEY、TEST_MODE 等）

# 快速测试
bash scripts/run_test.sh

# 全量运行
bash scripts/run_full.sh
```

## 配置说明

- **OPENAI_API_KEY**：不填则跳过阶段 3（仅同步+提取）
- **TEST_MODE**：`true` 仅抓 1 页、提取/分析各 1 条；`false` 全量
- Coze workflow 的 token/workflow_id 在 `scripts/utils.py` 中（请注意密钥安全）

## 数据库

- 默认库：`assets/data.db`（初始数据来自 `ai-frontier-tracker/assets/data.db` 的复制）
- 测试库：`assets/data.test.db`（由 run_test.sh 使用）

清空数据：`bash scripts/clear_db.sh` 或 `bash scripts/clear_db.sh assets/data.db`

## 查询时间轴

```bash
bash scripts/list_dimensions.sh
bash scripts/timeline.sh "LLM"
bash scripts/timeline.sh "AI编程/Vibe Coding" 50
```

更多细节见 `references/REFERENCE.md`。
