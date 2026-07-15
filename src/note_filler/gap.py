"""缺口偵測:判定筆記是否涵蓋各問題,只回報 partial / missing 的缺口。

硬合約(C1):對「全部問題」一次性呼叫 llm.complete;要求回 JSON 陣列;
只保留 status ∈ {partial, missing};解析失敗則保守把全部問題當 missing。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .llm import LLMClient


@dataclass
class Gap:
    question: str
    status: Literal["covered", "partial", "missing"]
    reason: str


_PROMPT_TEMPLATE = """你是筆記涵蓋度審查員。以下是一份筆記,以及一組問題。
請逐一判斷筆記是否已涵蓋每個問題,status 只能三選一:
- covered:筆記已完整回答此問題。
- partial:筆記有部分提及但不完整。
- missing:筆記完全沒有涉及。

只輸出 JSON 陣列,不要任何額外文字、說明或 markdown 圍欄。
每個元素格式:
{{"question": "<照抄原問題文字>", "status": "covered|partial|missing", "reason": "<簡短理由>"}}

=== 筆記全文 ===
{note_text}

=== 問題清單 ===
{questions_block}
"""


def _strip_fence(raw: str) -> str:
    """剝除 LLM 可能包上的 ```json ... ``` 圍欄,回傳純內容。"""
    s = raw.strip()
    if s.startswith("```"):
        # 去掉第一行圍欄(```或```json)
        s = s.split("\n", 1)[1] if "\n" in s else ""
        # 去掉結尾圍欄
        if s.rstrip().endswith("```"):
            s = s.rstrip()[: s.rstrip().rindex("```")]
    return s.strip()


def _all_missing(questions: list[str], reason: str) -> list[Gap]:
    return [Gap(question=q, status="missing", reason=reason) for q in questions]


def detect_gaps(questions: list[str], note_text: str, llm: LLMClient) -> list[Gap]:
    if not questions:
        return []

    questions_block = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    prompt = _PROMPT_TEMPLATE.format(note_text=note_text, questions_block=questions_block)

    # C1:對全部問題「一次」呼叫。
    raw = llm.complete([{"role": "user", "content": prompt}])

    try:
        data = json.loads(_strip_fence(raw))
        if not isinstance(data, list):
            raise ValueError("回應不是 JSON 陣列")
    except (json.JSONDecodeError, ValueError):
        # 保守 fallback:全部當 missing。
        return _all_missing(questions, reason="LLM 回應解析失敗,保守標為 missing")

    gaps: list[Gap] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status not in ("partial", "missing"):  # 只留缺口,covered 濾掉
            continue
        gaps.append(
            Gap(
                question=str(item.get("question", "")),
                status=status,
                reason=str(item.get("reason", "")),
            )
        )
    return gaps
