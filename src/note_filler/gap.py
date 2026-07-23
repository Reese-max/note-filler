"""缺口偵測:判定筆記是否涵蓋各問題,只回報 partial / missing 的缺口。

硬合約(C1):對「全部問題」一次性呼叫 llm.complete;要求回 JSON 陣列;
只保留 status ∈ {partial, missing};解析失敗則保守把全部問題當 missing。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Literal

from .audit import audit_event
from .llm import LLMClient

logger = logging.getLogger(__name__)


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
        audit_event(
            logger,
            "gap_detection_skipped",
            "questions:empty",
            level=logging.INFO,
            reason="no questions",
        )
        return []

    questions_block = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    prompt = _PROMPT_TEMPLATE.format(note_text=note_text, questions_block=questions_block)

    # C1:對全部問題「一次」呼叫。
    raw = llm.complete([{"role": "user", "content": prompt}])

    try:
        data = json.loads(_strip_fence(raw))
        if not isinstance(data, list):
            raise ValueError("回應不是 JSON 陣列")
    except (json.JSONDecodeError, ValueError) as exc:
        # 保守 fallback:全部當 missing。
        logger.warning(
            "gap detection for questions=%r failed, treating all as missing. raw=%.200s error=%s",
            questions,
            raw,
            exc,
        )
        return _all_missing(questions, reason="LLM 回應解析失敗,保守標為 missing")

    gaps: list[Gap] = []
    returned_questions: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            audit_event(
                logger,
                "gap_item_skipped",
                repr(item),
                reason="item is not a dict",
            )
            continue
        status = item.get("status")
        question = str(item.get("question", "")).strip()
        if status == "covered":  # 已涵蓋是預期排除，但仍留下問題識別碼
            audit_event(
                logger,
                "gap_item_filtered",
                question or repr(item),
                level=logging.INFO,
                reason="status covered",
            )
            returned_questions.add(question)
            continue
        if status not in ("partial", "missing"):
            audit_event(
                logger,
                "gap_item_skipped",
                question or repr(item),
                reason=f"invalid status: {status!r}",
            )
            continue
        if not question:
            audit_event(
                logger,
                "gap_item_skipped",
                repr(item),
                reason="gap item has no question",
            )
            continue
        returned_questions.add(question)
        reason = str(item.get("reason", "")).strip()
        if not reason:
            reason = "LLM 未提供缺口原因"
            audit_event(
                logger,
                "gap_reason_defaulted",
                question,
                reason=reason,
            )
        gaps.append(
            Gap(
                question=question,
                status=status,
                reason=reason,
            )
        )
    for question in questions:
        if question not in returned_questions:
            audit_event(
                logger,
                "gap_question_recovered",
                question,
                reason="LLM response omitted question; treating as missing",
            )
            gaps.append(
                Gap(
                    question=question,
                    status="missing",
                    reason="LLM 回應漏列問題，保守標為 missing",
                )
            )
    return gaps
