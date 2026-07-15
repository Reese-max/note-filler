"""研究問題生成:依主題與領域,請 LLM 產出該主題應涵蓋的關鍵問題清單。"""
from __future__ import annotations

from note_filler.domain import Domain
from note_filler.llm import LLMClient

_DOMAIN_LABEL: dict[str, str] = {
    "law": "法律法規",
    "admin": "行政公文與行政法",
    "exam": "考試準備",
    "other": "一般主題",
}


def generate_questions(full_text: str, domain: Domain, llm: LLMClient) -> list[str]:
    """針對筆記主題,產生「該主題應涵蓋的關鍵研究問題」清單。

    合約(C1):呼叫 llm.complete 恰一次;要求「每行一題」;
    以 splitlines()+strip() 去空行解析成 list[str];不解析 JSON。
    """
    domain_label = _DOMAIN_LABEL.get(domain, "一般主題")
    prompt = (
        f"你是一位「{domain_label}」領域的研究助理。\n"
        "以下是一份筆記的完整內容。請針對這份筆記的主題,\n"
        "列出「該主題應該被涵蓋、但筆記可能缺漏的關鍵研究問題」。\n\n"
        "嚴格輸出格式:\n"
        "1. 每一行只寫一個問題。\n"
        "2. 不要編號、不要項目符號、不要任何前綴或縮排。\n"
        "3. 只輸出問題本身,不要開場白、標題或結語。\n"
        "4. 問題需具體且可查證,聚焦於法規/制度/事實層面的補充重點。\n\n"
        f"筆記內容:\n{full_text}"
    )
    messages = [{"role": "user", "content": prompt}]

    raw = llm.complete(messages)  # 恰一次呼叫

    lines = [line.strip() for line in raw.splitlines()]
    return [line for line in lines if line]
