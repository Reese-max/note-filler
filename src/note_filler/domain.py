import logging
from typing import Literal

from note_filler.audit import audit_event
from note_filler.llm import LLMClient

logger = logging.getLogger(__name__)

Domain = Literal["law", "admin", "exam", "other"]

# 順序即抽取優先序:law > admin > exam > other
_VALID: tuple[Domain, ...] = ("law", "admin", "exam", "other")

_SYSTEM_PROMPT = (
    "你是文件領域分類器。閱讀使用者提供的筆記文字,"
    "只回一個標籤,不要任何解釋、標點、引號或多餘文字。\n"
    "可選標籤(四選一):\n"
    "law   = 法律、法規、法條、判決、釋字相關\n"
    "admin = 行政、公文、機關內部作業、簽核流程相關\n"
    "exam  = 考試、考古題、應試準備、申論作答相關\n"
    "other = 以上皆非\n"
    "只輸出 law、admin、exam、other 其中之一。"
)


def detect_domain(text: str, llm: LLMClient) -> Domain:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    raw = llm.complete(messages)
    token = raw.strip().lower()

    # 1) 乾淨回應直接命中
    if token in _VALID:
        return token  # type: ignore[return-value]

    # 2) 回應含雜訊/標點時,依優先序抽出第一個出現的合法標籤
    for label in _VALID:
        if label in token:
            return label

    # 3) 完全無法辨識 → 無來源閘精神:不硬猜,回 "other"
    audit_event(
        logger,
        "domain_detection_defaulted",
        token[:50] or "llm-response:empty",
        reason="LLM response unparseable",
        outcome="other",
    )
    return "other"
