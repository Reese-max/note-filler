from __future__ import annotations

from dataclasses import asdict

from typing import Literal

from note_filler.binding_report import build_binding_report
from note_filler.citation_formatter import build_reference_lines
from note_filler.correction import CorrectionDoc
from note_filler.retrieve.models import Source

Cardinality = Literal["one_to_one", "one_to_many", "none"]


def _cardinality(source_count: int) -> Cardinality:
    if source_count <= 0:
        return "none"
    if source_count == 1:
        return "one_to_one"
    return "one_to_many"


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
    source_id = getattr(seg, "source_id", None)
    if source_id:
        items.append(f"來源ID {source_id}")
    for ref in getattr(seg, "traceability", []):
        ref_id = ref.get("id")
        if ref.get("kind") == "original_input":
            ref_id = f"{ref_id}#paragraph-{ref.get('paragraph_idx')}"
        items.append(f"{labels.get(ref.get('kind'), ref.get('kind'))} {ref_id}")
    return "、".join(items)


def to_json(doc: CorrectionDoc) -> dict:
    """序列化整份 CorrectionDoc；原文 immutable，僅讀不改。

    頂層含 binding_summary（整合 binding_report 的摘要），
    讓訂正稿 JSON 本身就可被測試直接解析驗證綁定狀態。
    """
    report = build_binding_report(doc)
    binding_summary = {
        "schema": report["schema"],
        "argument_count": report["argument_count"],
        "pass": report["summary"]["pass"],
        "fail": report["summary"]["fail"],
        "pending_evidence": report["summary"]["pending_evidence"],
        "one_to_one": report["summary"]["one_to_one"],
        "one_to_many": report["summary"]["one_to_many"],
        "none": report["summary"]["none"],
        "all_arguments_ok": report["summary"]["all_arguments_ok"],
        "all_sourced_arguments_ok": report["summary"]["all_sourced_arguments_ok"],
    }
    def _seg_source_ids(seg) -> list[str]:
        ids = list(getattr(seg, "source_ids", None) or [])
        if not ids:
            ids = [s.id for s in getattr(seg, "sources", [])]
        return ids

    return {
        "source_path": doc.original.source_path,
        "full_text": doc.original.full_text,
        "binding_summary": binding_summary,
        "segments": [
            {
                "type": seg.type,
                "text": seg.text,
                "anchor_idx": seg.anchor_idx,
                "confidence": seg.confidence,
                "conflict_note": getattr(seg, "conflict_note", None),
                "source_id": getattr(seg, "source_id", ""),
                "source_ids": _seg_source_ids(seg),
                "cardinality": _cardinality(len(_seg_source_ids(seg))),
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
        source_ids = list(getattr(seg, "source_ids", None) or [])
        if not source_ids:
            source_ids = [s.id for s in getattr(seg, "sources", [])]
        if source_ids:
            body.append(
                f"> **來源清單**：{','.join(source_ids)}"
                f"（{_cardinality(len(source_ids)).replace('_', ' ')})"
            )
        elif seg.type == "supplement":
            body.append("> **來源清單**：pending（無來源）")

    body.extend(original_traces)

    md = "\n\n".join(body)

    # 文末參考區塊：只放實際被引用(有進 body 的)sources，順序即 footnote 順序
    ref_block = build_reference_lines(cited)
    if ref_block:
        md = f"{md}\n\n{ref_block}"

    # 綁定驗證摘要行：可直接被測試解析的結構化文字
    report = build_binding_report(doc)
    s = report["summary"]
    summary_parts = []
    if s["pass"]:
        summary_parts.append(f"✓ {s['pass']} 通過")
    if s["fail"]:
        summary_parts.append(f"✗ {s['fail']} 未通過")
    if s["pending_evidence"]:
        summary_parts.append(f"⚠ {s['pending_evidence']} 待補證")
    binding_line = "、".join(summary_parts) if summary_parts else "無論點"
    verdict = "全部通過 ✓" if s["all_arguments_ok"] else "有綁定問題 ✗"
    md = f"{md}\n\n---\n> **來源綁定**：{verdict}（{binding_line}）"

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
        source_ids = list(getattr(seg, "source_ids", None) or [])
        if not source_ids:
            source_ids = [s.id for s in getattr(seg, "sources", [])]
        if source_ids:
            out.add_paragraph(
                f"來源清單：{','.join(source_ids)}"
                f"（{_cardinality(len(source_ids)).replace('_', ' ')}）"
            )
        elif seg.type == "supplement":
            out.add_paragraph("來源清單：pending（無來源）")

    for trace in original_traces:
        out.add_paragraph(f"追溯：{trace}")

    ref_lines = build_reference_lines(cited).splitlines()
    if ref_lines:
        out.add_paragraph()
        for line in ref_lines:
            if line.strip():
                out.add_paragraph(line)

    out.save(path)
