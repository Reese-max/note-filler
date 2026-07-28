"""Q3:綜合撰寫補充。只根據 sources 回答 gap.question,論點標 [^n] 引用。

硬合約:單次 llm.complete、可測(FakeLLM);解析 text 內 [^n] → used_source_ids
(對映 sources[n-1].id,依出現序去重);越界 n 之標記從 text 移除、不計入 used;
來源不足時 LLM 以「【待補證】」開頭,used_source_ids=[]。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .audit import audit_event
from .gap import Gap
from .llm import LLMClient
from .retrieve.models import Source

logger = logging.getLogger(__name__)

_MARKER = re.compile(r"\[\^(\d+)\]")
CITATION_SPAN_KEYS = ("source_id", "span_start", "span_end", "marker_text")

_PROMPT = """你是嚴謹的法律補充撰寫員。只根據下列「來源」回答問題,寫成通順的一段。\
請盡量根據手上的來源(尤其是 Level A 的法條原文)回答問題,不要因為來源不完美就輕易放棄。
每個論點都要就近 inline 標註引用來源,格式為 [^n](n 為來源序號):把 [^n] 放在該論點後面,\
不要把所有註腳全堆在整段句尾,也不要對同一個論點重複標同一個 n。嚴禁引入來源以外的任何資訊。
只有當這些來源與問題「完全無關、無從作答」時,才讓整段以「【待補證】」開頭,說明缺了什麼,並且不要標任何 [^n]。

=== 問題 ===
{question}

=== 來源(依序號引用) ===
{sources_block}
"""


@dataclass
class WrittenSupplement:
    text: str
    used_source_ids: list  # list[str]
    citation_spans: list[dict] | None = None
    omitted_source_ids: list[str] | None = None  # 檢索到但未被引用的來源 ID

    def __post_init__(self) -> None:
        # 既有呼叫端可只傳 text + used_source_ids；在寫作資料模型這一層解析，
        # 避免輸出層日後只看 source_ids 反向猜測引用位置。
        if self.citation_spans is None:
            self.citation_spans = _infer_citation_spans(
                self.text, self.used_source_ids
            )
        if self.omitted_source_ids is None:
            self.omitted_source_ids = []


def _span(source_id: str, match: re.Match) -> dict:
    """建立固定鍵序的引用範圍。"""
    return {
        "source_id": source_id,
        "span_start": match.start(),
        "span_end": match.end(),
        "marker_text": match.group(0),
    }


def _infer_citation_spans(text: str, used_source_ids: list[str]) -> list[dict]:
    """相容既有 WrittenSupplement fixture 的最小解析。

    used_source_ids 的既有契約是依不同有效 marker 首次出現順序排列，故可在
    WrittenSupplement 建立時逐一對回；正式 writer 會直接傳入精確 spans。
    """
    marker_sources: dict[str, str] = {}
    source_iter = iter(used_source_ids)
    spans: list[dict] = []
    for match in _MARKER.finditer(text):
        marker = match.group(1)
        if marker not in marker_sources:
            source_id = next(source_iter, None)
            if source_id is None:
                continue
            marker_sources[marker] = source_id
        spans.append(_span(marker_sources[marker], match))
    return spans


def citation_span_issues(
    text: str,
    source_ids: list[str],
    citation_spans: object,
) -> list[str]:
    """檢查引用範圍的固定結構、字面、邊界與來源覆蓋。"""
    if not isinstance(citation_spans, list):
        return ["citation_spans 必須為 list"]

    issues: list[str] = []
    valid: list[dict] = []
    for index, item in enumerate(citation_spans):
        where = f"citation_spans[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{where} 必須為 dict")
            continue
        if tuple(item) != CITATION_SPAN_KEYS:
            issues.append(f"{where} 欄位或序列漂移")
            continue
        source_id = item["source_id"]
        start = item["span_start"]
        end = item["span_end"]
        marker = item["marker_text"]
        if not isinstance(source_id, str) or not source_id.strip():
            issues.append(f"{where}.source_id 必須為非空字串")
            continue
        if type(start) is not int or type(end) is not int:
            issues.append(f"{where} 範圍必須為 int")
            continue
        if not isinstance(marker, str) or _MARKER.fullmatch(marker) is None:
            issues.append(f"{where}.marker_text 不是有效 inline 引用")
            continue
        if not (0 <= start < end <= len(text)):
            issues.append(f"{where} 範圍越界")
            continue
        if text[start:end] != marker:
            issues.append(f"{where} 範圍與 marker_text 不一致")
            continue
        valid.append(item)

    ordered = sorted(valid, key=lambda item: (item["span_start"], item["span_end"]))
    for previous, current in zip(ordered, ordered[1:]):
        if current["span_start"] < previous["span_end"]:
            issues.append("citation_spans 不得重疊")
            break

    expected = set(source_ids)
    actual = {item["source_id"] for item in valid}
    missing = expected - actual
    extra = actual - expected
    if missing:
        issues.append(f"citation_spans 遺漏來源: {sorted(missing)}")
    if extra:
        issues.append(f"citation_spans 含未知來源: {sorted(extra)}")
    return issues


def _sources_block(sources: list[Source]) -> str:
    return "\n".join(f"[{i + 1}] {s.title}:{s.content}" for i, s in enumerate(sources))


def write_supplement(gap: Gap, sources: list[Source], llm: LLMClient) -> WrittenSupplement:
    prompt = _PROMPT.format(question=gap.question, sources_block=_sources_block(sources))
    raw = llm.complete([{"role": "user", "content": prompt}]).strip()

    if raw.startswith("【待補證】"):
        audit_event(
            logger,
            "supplement_writing_deferred",
            gap.question,
            level=logging.INFO,
            reason="LLM returned pending evidence marker",
        )
        return WrittenSupplement(
            text=_MARKER.sub("", raw),
            used_source_ids=[],
            citation_spans=[],
        )

    n = len(sources)
    def _sub(m: re.Match) -> str:
        idx = int(m.group(1))
        if 1 <= idx <= n:
            return m.group(0)              # 有效標記保留
        audit_event(
            logger,
            "out-of-range citation marker removed",
            gap.question,
            marker=idx,
            available_sources=n,
        )
        return ""                          # 越界標記移除

    text = _MARKER.sub(_sub, raw)
    used: list[str] = []
    citation_spans: list[dict] = []
    for match in _MARKER.finditer(text):
        source_id = sources[int(match.group(1)) - 1].id
        citation_spans.append(_span(source_id, match))
        if source_id not in used:
            used.append(source_id)
        else:
            audit_event(
                logger,
                "citation_source_deduplicated",
                source_id,
                level=logging.INFO,
                question=gap.question,
            )
    if not used:
        audit_event(
            logger,
            "supplement_has_no_forwardable_sources",
            gap.question,
            reason="generated text cited no valid source IDs",
            outcome="pending_evidence",
        )
    return WrittenSupplement(
        text=text,
        used_source_ids=used,
        citation_spans=citation_spans,
    )
