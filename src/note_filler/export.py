from __future__ import annotations

from dataclasses import asdict

from note_filler.citation_formatter import build_reference_lines
from note_filler.correction import CorrectionDoc
from note_filler.retrieve.models import Source


def _source_to_dict(src: Source) -> dict:
    """Source dataclass → 純 dict(含 fetched_date/doc_date/level/distance)。"""
    return asdict(src)


def to_json(doc: CorrectionDoc) -> dict:
    """序列化整份 CorrectionDoc；原文 immutable，僅讀不改。"""
    return {
        "source_path": doc.original.source_path,
        "full_text": doc.original.full_text,
        "segments": [
            {
                "type": seg.type,
                "text": seg.text,
                "anchor_idx": seg.anchor_idx,
                "confidence": seg.confidence,
                "sources": [_source_to_dict(s) for s in seg.sources],
            }
            for seg in doc.segments
        ],
    }


def to_markdown(doc: CorrectionDoc) -> str:
    """
    C3 鎖定格式：
      - original 段：原樣輸出(原文 immutable)。
      - supplement 段：'> 【補充】{text}' 後接 [^n] 註腳(每個來源一個)。
      - pending_evidence 段：【補充】後加 '⚠待補證 '(sources 空則無 footnote)。
    文末以 build_reference_lines(所有被引用 sources) 產參考區塊(C7 內含 Date)。
    footnote 編號與 cited 順序一致，交給 T11 重新列 [^1..n]。
    """
    body: list[str] = []
    cited: list[Source] = []
    counter = 0

    for seg in doc.segments:
        if seg.type == "original":
            body.append(seg.text)
            continue

        # supplement：依序為每個來源配一個 footnote，並蒐集到 cited
        marks = ""
        for src in seg.sources:
            counter += 1
            cited.append(src)
            marks += f"[^{counter}]"

        prefix = "> 【補充】"
        if seg.confidence == "pending_evidence":
            prefix += "⚠待補證 "
        body.append(f"{prefix}{seg.text}{marks}")

    md = "\n\n".join(body)

    # 文末參考區塊：只放實際被引用(有進 body 的)sources，順序即 footnote 順序
    ref_block = build_reference_lines(cited)
    if ref_block:
        md = f"{md}\n\n{ref_block}"

    return md
