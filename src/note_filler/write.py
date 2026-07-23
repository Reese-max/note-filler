"""Q3:綜合撰寫補充。只根據 sources 回答 gap.question,論點標 [^n] 引用。

硬合約:單次 llm.complete、可測(FakeLLM);解析 text 內 [^n] → used_source_ids
(對映 sources[n-1].id,依出現序去重);越界 n 之標記從 text 移除、不計入 used;
來源不足時 LLM 以「【待補證】」開頭,used_source_ids=[]。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .gap import Gap
from .llm import LLMClient
from .retrieve.models import Source

logger = logging.getLogger(__name__)

_MARKER = re.compile(r"\[\^(\d+)\]")

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


def _sources_block(sources: list[Source]) -> str:
    return "\n".join(f"[{i + 1}] {s.title}:{s.content}" for i, s in enumerate(sources))


def write_supplement(gap: Gap, sources: list[Source], llm: LLMClient) -> WrittenSupplement:
    prompt = _PROMPT.format(question=gap.question, sources_block=_sources_block(sources))
    raw = llm.complete([{"role": "user", "content": prompt}]).strip()

    if raw.startswith("【待補證】"):
        return WrittenSupplement(text=raw, used_source_ids=[])

    n = len(sources)
    used: list[str] = []

    def _sub(m: re.Match) -> str:
        idx = int(m.group(1))
        if 1 <= idx <= n:
            sid = sources[idx - 1].id
            if sid not in used:            # 依出現序去重
                used.append(sid)
            return m.group(0)              # 有效標記保留
        logger.warning(
            "question=%r out-of-range citation marker [^%d] removed (only %d sources available)",
            gap.question,
            idx,
            n,
        )
        return ""                          # 越界標記移除

    text = _MARKER.sub(_sub, raw)
    return WrittenSupplement(text=text, used_source_ids=used)
