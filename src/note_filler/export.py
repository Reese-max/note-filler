from __future__ import annotations

from dataclasses import asdict

from note_filler.citation_formatter import build_reference_lines
from note_filler.correction import CorrectionDoc
from note_filler.retrieve.models import Source


def _source_to_dict(src: Source) -> dict:
    """Source dataclass → 純 dict(含 fetched_date/doc_date/level/distance)。"""
    return asdict(src)


def _trace_text(seg) -> str:
    labels = {
        "original_input": "原始輸入",
        "source": "來源識別碼",
        "processing_record": "處理紀錄",
    }
    items: list[str] = []
    for ref in getattr(seg, "traceability", []):
        ref_id = ref.get("id")
        if ref.get("kind") == "original_input":
            ref_id = f"{ref_id}#paragraph-{ref.get('paragraph_idx')}"
        items.append(f"{labels.get(ref.get('kind'), ref.get('kind'))} {ref_id}")
    return "、".join(items)


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
                "conflict_note": getattr(seg, "conflict_note", None),
                "traceability": list(getattr(seg, "traceability", [])),
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
    original_traces: list[str] = []
    counter = 0

    for seg in doc.segments:
        if seg.type == "original":
            body.append(seg.text)
            if trace := _trace_text(seg):
                original_traces.append(f"> 追溯：{trace}")
            continue

        if original_traces:
            body.extend(original_traces)
            original_traces.clear()

        # supplement：依序為每個來源配一個 footnote，並蒐集到 cited
        marks = ""
        for src in seg.sources:
            counter += 1
            cited.append(src)
            marks += f"[^{counter}]"

        prefix = "> 【補充】"
        if seg.confidence == "pending_evidence":
            prefix += "⚠待補證 "
        conflict = getattr(seg, "conflict_note", None)
        if conflict:
            body.append(f"> ⚠️ **衝突告警**: {conflict}")
        body.append(f"{prefix}{seg.text}{marks}")
        if trace := _trace_text(seg):
            body.append(f"> 追溯：{trace}")

    body.extend(original_traces)

    md = "\n\n".join(body)

    # 文末參考區塊：只放實際被引用(有進 body 的)sources，順序即 footnote 順序
    ref_block = build_reference_lines(cited)
    if ref_block:
        md = f"{md}\n\n{ref_block}"

    return md


def to_docx(doc: CorrectionDoc, path: str) -> None:
    """輸出 .docx 訂正稿,結構鏡射 to_markdown(原文 immutable、補充段標【補充】)。

    python-docx 原生 footnote 支援不佳,故 [^n] 以 inline 文字呈現、文末列參考來源。
    """
    from docx import Document as DocxDocument  # 延遲 import,不用 docx 輸出時免裝

    out = DocxDocument()
    cited: list[Source] = []
    original_traces: list[str] = []
    counter = 0

    for seg in doc.segments:
        if seg.type == "original":
            out.add_paragraph(seg.text)
            if trace := _trace_text(seg):
                original_traces.append(trace)
            continue
        if original_traces:
            for trace in original_traces:
                out.add_paragraph(f"追溯：{trace}")
            original_traces.clear()
        marks = ""
        for src in seg.sources:
            counter += 1
            cited.append(src)
            marks += f"[^{counter}]"
        conflict = getattr(seg, "conflict_note", None)
        if conflict:
            p_conflict = out.add_paragraph()
            run_conflict = p_conflict.add_run(f"⚠️ 衝突告警: {conflict}")
            run_conflict.bold = True
        prefix = "【補充】" + ("⚠待補證 " if seg.confidence == "pending_evidence" else "")
        p = out.add_paragraph()
        run = p.add_run(f"{prefix}{seg.text}{marks}")
        run.italic = True  # 補充段視覺區隔於原文
        if trace := _trace_text(seg):
            out.add_paragraph(f"追溯：{trace}")

    for trace in original_traces:
        out.add_paragraph(f"追溯：{trace}")

    ref_lines = build_reference_lines(cited).splitlines()
    if ref_lines:
        out.add_paragraph()
        for line in ref_lines:
            if line.strip():
                out.add_paragraph(line)

    out.save(path)
