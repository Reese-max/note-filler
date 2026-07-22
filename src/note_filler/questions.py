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
        "內容邊界(最重要):\n"
        "- 所有問題必須緊扣筆記「實際出現的概念與術語」,用來深化或釐清\n"
        "  筆記已提到的內容:定義、原理、機制、要件、防禦做法、\n"
        "  或該標準/法規/制度本身的細節。\n"
        "- 不要引入筆記未提及的外部法規、合規框架或無關主題。\n"
        "  例如筆記在談技術題材時,不要硬扯 GDPR、個資法、PCI DSS、\n"
        "  ISO 27001、NIST 等未出現於筆記的合規標準;筆記在談法律題材時,\n"
        "  則應圍繞筆記實際涉及的法條與概念深入,而非跳到無關領域。\n\n"
        "嚴格輸出格式:\n"
        "1. 每一行只寫一個問題。\n"
        "2. 不要編號、不要項目符號、不要任何前綴或縮排。\n"
        "3. 只輸出問題本身,不要開場白、標題或結語。\n"
        "4. 問題需具體且可查證,聚焦於筆記已出現概念的補充與釐清。\n\n"
        f"筆記內容:\n{full_text}"
    )
    messages = [{"role": "user", "content": prompt}]

    raw = llm.complete(messages)  # 恰一次呼叫

    if raw.lstrip().startswith(("[", "{")):
        return []

    lines = [line.strip() for line in raw.splitlines()]
    return [line for line in lines if line]
