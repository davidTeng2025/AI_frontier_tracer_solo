from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Literal, Optional

import requests
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator  # type: ignore[import-not-found]


DIMENSIONS = [
    "LLM",
    "VLM",
    "视频生成",
    "音频/TTS/ASR",
    "具身智能",
    "AI编程/Vibe Coding",
    "AI应用",
]


class InsightItem(BaseModel):
    """
    对应 Prompt 的单条输出：
    {
      "dimension": "...",
      "project_name": "...",
      "tech_node": "...",
      "evolution_tag": "...",
      "impact_signal": "...",
      "raw_context": "..."
    }
    """

    model_config = ConfigDict(extra="ignore")

    dimension: str
    project_name: str | None = None
    tech_node: str
    evolution_tag: str | None = None
    impact_signal: str | None = None
    raw_context: str | None = None

    @field_validator("dimension")
    @classmethod
    def _normalize_dimension(cls, v: str) -> str:
        v = (v or "").strip()
        return v


_InsightListAdapter = TypeAdapter(list[InsightItem])


class InsightBatch(BaseModel):
    """分析结果（多条洞察）。"""

    model_config = ConfigDict(extra="ignore")

    items: list[InsightItem] = Field(default_factory=list)

    def to_db_rows(self, *, source_id: str) -> list[dict]:
        """
        转为 database.TechInsightRow 所需字段（用 dict，避免 analyzer ↔ database 的硬耦合）。
        """
        rows: list[dict] = []
        for it in self.items:
            impact_score = infer_impact_score(it.impact_signal, it.evolution_tag)
            summary = (it.raw_context or "").strip()
            rows.append(
                {
                    "source_id": source_id,
                    "dimension": it.dimension,
                    "project_name": it.project_name,
                    "tech_node": it.tech_node,
                    "evolution_tag": it.evolution_tag,
                    "impact_score": impact_score,
                    "summary": summary,
                }
            )
        return rows


def infer_impact_score(impact_signal: str | None, evolution_tag: str | None) -> int:
    """
    影响力等级 (1-5)，根据“爆火”等关键词推断。
    - 这里用启发式规则，避免要求模型额外输出 impact_score。
    """
    s = f"{impact_signal or ''} {evolution_tag or ''}".strip()
    if not s:
        return 1
    s_lower = s.lower()

    strong = ("爆火", "刷屏", "现象级", "彻底改变", "颠覆", "破圈", "最强", "sota", "breakthrough")
    high = ("大幅提升", "显著提升", "重大更新", "发布", "上线", "重磅", "最强", "hot")
    mid = ("开源", "新增", "更新", "增强", "优化", "支持", "推出")

    if any(k in s for k in strong) or any(k in s_lower for k in ("viral", "game changer")):
        return 5
    if any(k in s for k in high):
        return 4
    if any(k in s for k in mid):
        return 3
    return 2


class LlmError(RuntimeError):
    pass


class LlmRetryableError(LlmError):
    pass


@dataclass(frozen=True)
class OpenAIAnalyzerConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    timeout_s: float = 60.0
    max_retries: int = 2
    backoff_initial_s: float = 0.8
    backoff_max_s: float = 10.0


class OpenAIAnalyzer:
    """
    使用 OpenAI 兼容 Chat Completions 接口的分析器（如 GPT-4o）。

    配置来源：
    - 推荐从本项目 config.json 读取（见 config.py / main.py）
    - 仍保留 from_env 以兼容其他调用方式
    """

    def __init__(self, config: OpenAIAnalyzerConfig):
        self.config = config
        self.session = requests.Session()

        self.base_url = config.base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_env(cls) -> "OpenAIAnalyzer":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LlmError("缺少环境变量 OPENAI_API_KEY，无法进行 AI 分析。")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4.1")
        return cls(OpenAIAnalyzerConfig(api_key=api_key, base_url=base_url, model=model))

    @classmethod
    def from_config(cls, *, api_key: str | None, base_url: str, model: str) -> "OpenAIAnalyzer":
        if not api_key or not str(api_key).strip():
            raise LlmError("缺少 OPENAI_API_KEY，无法进行 AI 分析。")
        return cls(
            OpenAIAnalyzerConfig(
                api_key=str(api_key).strip(),
                base_url=base_url,
                model=model,
            )
        )

    def analyze(self, *, title: str | None, content_text: str) -> InsightBatch:
        prompt = self._build_prompt(title=title, content_text=content_text)
        raw = self._chat(prompt)
        parsed = self._parse_json_any(raw)
        items = self._validate_items(parsed)
        if not items:
            raise LlmError("LLM 未返回任何洞察条目（空列表）")
        return InsightBatch(items=items)

    def _build_prompt(self, *, title: str | None, content_text: str) -> str:
        title_part = (title or "").strip()
        body = (content_text or "").strip()
        return (
            "# Role\n"
            "你是一位 AI 行业进化史记录专家，擅长从碎片化的快讯中捕捉技术的“进化节点”。\n\n"
            "# Task\n"
            "分析输入的新闻/快讯，提炼技术进展。即使信息模糊，也要根据功能描述推断其所属的最相关维度。\n\n"
            '# Strategy: "Relaxed & Insightful"\n'
            "1. **多重归类**：如果一个项目既是AI编程又涉及视频生成（如：全自动写脚本做动画），请同时记录在两个维度下。\n"
            "2. **捕捉 Vibe Coding 信号**：关注那些“动动嘴”、“不会代码也能做”、“全自动生成页面”的描述，这些归入 [AI编程/Vibe Coding]。\n"
            "3. **推断缺失信息**：未提及机构时记录为“开源/个人项目”。\n\n"
            "# Dimensions Definition\n"
            "- LLM: 文本、代码逻辑、长文本理解、模型架构。\n"
            "- VLM: 视觉理解、OCR、4D/3D感知、物体分割。\n"
            "- 视频生成: 视频模型、数字人、特效、3D重建。\n"
            "- 音频/TTS/ASR: 声音克隆、转录、实时对话、情感语音。\n"
            "- 具身智能: 机器人、自动操作电脑(Desktop Agent)、自动驾驶、物理交互。\n"
            "- AI编程/Vibe Coding: 自然语言编程、全自动代码生成、Figma2Code、自进化编程助手。\n"
            "- AI应用: 除去编程外的垂直行业工具（如：教育、表格、医疗助手）。\n\n"
            "# Output Format (JSON ONLY)\n"
            "[\n"
            "  {\n"
            '    "dimension": "维度名称",\n'
            '    "project_name": "项目/产品名",\n'
            '    "tech_node": "核心技术点（描述进化脉络，例如：从代码补全到UI全自动生成）",\n'
            '    "evolution_tag": "标签（如：开源 / 突破性体验 / 商业落地 / VibeCoding）",\n'
            '    "impact_signal": "文中提到的热度信息（如：爆火、彻底改变产品开发流程等）",\n'
            '    "raw_context": "简短原始摘要"\n'
            "  }\n"
            "]\n\n"
            "要求：只输出 JSON 数组，不要输出任何额外文字。\n"
            f"输入标题：{title_part}\n"
            f"输入正文：{body}\n"
        )

    def _chat(self, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个严格按要求输出 JSON 的信息抽取助手。",
                },
                {"role": "user", "content": user_prompt},
            ],
        }

        last_err: Optional[BaseException] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                resp = self.session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.config.timeout_s,
                )

                if resp.status_code == 429 or 500 <= resp.status_code <= 599:
                    raise LlmRetryableError(
                        f"retryable status={resp.status_code} body={resp.text[:500]}"
                    )

                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if not isinstance(content, str) or not content.strip():
                    raise LlmError(f"LLM 返回空内容：{str(data)[:500]}")
                return content
            except (requests.RequestException, LlmRetryableError, ValueError) as e:
                last_err = e
                if attempt >= self.config.max_retries:
                    break
                self._sleep_backoff(attempt)

        raise LlmError("LLM 调用失败") from last_err

    def _sleep_backoff(self, attempt: int) -> None:
        base = min(
            self.config.backoff_max_s,
            self.config.backoff_initial_s * (2**attempt),
        )
        jitter = random.uniform(0, base * 0.2)
        time.sleep(base + jitter)

    def _validate_items(self, parsed: Any) -> list[InsightItem]:
        # 允许模型包一层 {"items": [...]}
        if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
            parsed = parsed["items"]
        return _InsightListAdapter.validate_python(parsed)

    def _parse_json_any(self, text: str) -> Any:
        t = text.strip()
        # 1) 直接解析
        try:
            obj = json.loads(t)
            if isinstance(obj, (dict, list)):
                return obj
        except Exception:  # noqa: BLE001
            pass

        # 2) 处理 ```json ... ``` 包裹
        if "```" in t:
            t2 = t.replace("```json", "```").replace("```JSON", "```")
            parts = [p.strip() for p in t2.split("```") if p.strip()]
            # 优先选包含 JSON 的块
            for p in parts:
                if ("[" in p and "]" in p) or ("{" in p and "}" in p):
                    try:
                        obj = json.loads(p)
                        if isinstance(obj, (dict, list)):
                            return obj
                    except Exception:  # noqa: BLE001
                        continue

        # 3) 尝试截取 [...] 或 {...}
        start_arr = t.find("[")
        end_arr = t.rfind("]")
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            snippet = t[start_arr : end_arr + 1]
            try:
                return json.loads(snippet)
            except Exception:  # noqa: BLE001
                pass

        start_obj = t.find("{")
        end_obj = t.rfind("}")
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            snippet = t[start_obj : end_obj + 1]
            try:
                return json.loads(snippet)
            except Exception as e:  # noqa: BLE001
                raise LlmError(f"无法解析 LLM JSON 输出：{text[:500]}") from e

        raise LlmError(f"无法解析 LLM 输出为 JSON：{text[:500]}")

