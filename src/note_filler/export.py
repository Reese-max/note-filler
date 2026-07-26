from __future__ import annotations

from dataclasses import asdict

from typing import Any, Literal

from note_filler.angle_coverage import coverage_from_segment
from note_filler.binding_report import build_binding_report
from note_filler.citation_formatter import build_reference_lines
from note_filler.correction import CorrectionDoc
from note_filler.metrics import calculate_polaris_metrics
from note_filler.retrieve.models import Source

Cardinality = Literal["one_to_one", "one_to_many", "none"]


def _cardinality(source_count: int) -> Cardinality:
    if source_count <= 0:
        return "none"
    if source_count == 1:
        return "one_to_one"
    return "one_to_many"


def _calculate_polaris_for_doc(doc: CorrectionDoc) -> dict[str, Any]:
    """從 CorrectionDoc 計算北極星品質指標，用於整合到成品輸出。
    
    計算方式：
      1. 從 build_binding_report 取得綁定報告
      2. 依每個 segment 的 confidence 建構 delivery_status
      3. 透過 calculate_polaris_metrics 計算五項分項分數
      4. 回傳可序列化的 dict（含 overall_status、各分項分數、判定依據）
    
    判定依據：
      - functional_gap_score：功能缺口具體描述比例
      - user_value_score：使用者價值關鍵詞覆蓋比例
      - source_binding_integrity：來源綁定通過比例
      - angle_diversity_index：角度多樣性覆蓋比例
      - delivery_success_rate：端到端送達成功率
    
    資料來源：
      - binding_report.arguments[].functional_gap / user_value / binding_status
      - binding_report.angle_coverage_summary
      - 各 segment 的 confidence 狀態
    """
    report = build_binding_report(doc)
    
    # 從 segments 建構 delivery_status
    all_segments = list(getattr(doc, "segments", None) or [])
    has_any_segment = len(all_segments) > 0
    has_supplement = any(s.type == "supplement" for s in all_segments)
    all_verified = all(
        s.confidence == "verified" 
        for s in all_segments 
        if s.type == "supplement"
    ) if has_supplement else False
    
    delivery_status = {
        "primary_note_ready": has_any_segment,
        "user_channel_sent": False,  # 尚未送出，由外部更新
        "local_fallback_written": has_any_segment,
    }
    
    metrics = calculate_polaris_metrics(
        binding_report=report,
        delivery_status=delivery_status,
    )
    
    return metrics.to_dict()


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


def _argument_coverage_text(argument: dict) -> str:
    """逐筆聚合論點、來源、必要性雙視角與角度清單。
    
    格式與機器可讀報告對齊，顯示四個核心欄位：
    - functional_gap：功能缺口
    - user_value：使用者價值
    - angle_tags：角度標籤
    - source_ids：來源識別碼
    """
    coverage = argument["angle_coverage"]
    angle_tags = argument.get("angle_tags", coverage.get("angle_labels", []))
    source_ids = argument.get("source_ids", [])
    functional_gap = argument.get("functional_gap", "")
    user_value = argument.get("user_value", "")
    
    return (
        f"functional_gap={functional_gap or '（未提供）'}"
        f"；user_value={user_value or '（未提供）'}"
        f"；angle_tags={'、'.join(angle_tags) if angle_tags else '（無）'}"
        f"；source_ids={','.join(source_ids) if source_ids else 'pending（無來源）'}"
    )


def _visible_summary_text(argument: dict) -> str:
    """同列顯示單一論點的功能缺口、使用者價值與關聯知識（同 argument_id）。"""
    related = argument.get("related_knowledge") or argument.get("summary") or ""
    return (
        f"argument_id={argument['argument_id']}"
        f"；functional_gap={argument['functional_gap'] or '（未提供）'}"
        f"；user_value={argument['user_value'] or '（未提供）'}"
        f"；related_knowledge={related}"
    )


def to_json(doc: CorrectionDoc) -> dict:
    """序列化整份 CorrectionDoc；原文 immutable，僅讀不改。

    頂層含 binding_summary（整合 binding_report 的摘要）與 polaris_metrics（北極星品質指標），
    讓訂正稿 JSON 本身就可被測試直接解析驗證綁定狀態與品質分數。
    
    polaris_metrics 包含：
      - overall_status：整體品質判定（excellent/good/acceptable/poor/error）
      - core_metrics_pass_count：通過門檻的核心指標數
      - functional_gap_score / user_value_score / source_binding_integrity / 
        angle_diversity_index / delivery_success_rate：各分項分數與判定依據
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
    
    # 計算北極星品質指標
    polaris_metrics = _calculate_polaris_for_doc(doc)
    def _seg_source_ids(seg) -> list[str]:
        ids = list(getattr(seg, "source_ids", None) or [])
        if not ids:
            ids = [s.id for s in getattr(seg, "sources", [])]
        return ids

    # 以 binding_report 的 angle_coverage（含 relation）對齊 segment 輸出
    argument_by_seg_index: dict[int, dict] = {
        argument["segment_index"]: argument for argument in report["arguments"]
    }

    def _seg_angle_coverage(seg, seg_index: int) -> dict:
        if seg_index in argument_by_seg_index:
            return argument_by_seg_index[seg_index]["angle_coverage"]
        # original 等無論點：仍輸出可解析空結構
        if getattr(seg, "type", None) != "supplement":
            return {
                "angle_type": getattr(seg, "angle_type", "") or "",
                "angle_labels": list(getattr(seg, "angle_labels", None) or []),
                "covered_facets": [],
                "angle_key": getattr(seg, "angle_key", "") or "",
                "relation": {
                    "kind": "unique",
                    "related_argument_indices": [],
                    "duplicate_of": [],
                    "synonym_of": [],
                },
                "effective_angle_count": 0,
                "duplicate_exclusion": {
                    "excluded": False,
                    "reason": None,
                    "kept_argument_index": None,
                },
            }
        return coverage_from_segment(seg)

    def _seg_argument_fields(seg, seg_index: int) -> dict:
        if argument := argument_by_seg_index.get(seg_index):
            return {
                "argument_id": argument["argument_id"],
                "summary": argument["summary"],
                "related_knowledge": argument["related_knowledge"],
                "angle_tags": list(argument["angle_tags"]),
                "valid_angle_count": argument["valid_angle_count"],
                "deduped_angle_count": argument["deduped_angle_count"],
                "duplicate_angles": list(argument["duplicate_angles"]),
            }
        return {
            "argument_id": str(getattr(seg, "argument_id", "") or ""),
            "summary": str(getattr(seg, "summary", "") or ""),
            "related_knowledge": str(getattr(seg, "related_knowledge", "") or ""),
            "angle_tags": list(getattr(seg, "angle_tags", None) or []),
            "valid_angle_count": int(getattr(seg, "valid_angle_count", 0) or 0),
            "deduped_angle_count": int(getattr(seg, "deduped_angle_count", 0) or 0),
            "duplicate_angles": list(getattr(seg, "duplicate_angles", None) or []),
        }

    return {
        "source_path": doc.original.source_path,
        "full_text": doc.original.full_text,
        "binding_summary": binding_summary,
        "angle_coverage_summary": dict(report.get("angle_coverage_summary") or {}),
        "polaris_metrics": polaris_metrics,
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
                "functional_gap": getattr(seg, "functional_gap", ""),
                "user_value": getattr(seg, "user_value", ""),
                **_seg_argument_fields(seg, i),
                "angle_type": getattr(seg, "angle_type", "") or "",
                "angle_labels": list(getattr(seg, "angle_labels", None) or []),
                "angle_key": getattr(seg, "angle_key", "") or "",
                "angle_coverage": _seg_angle_coverage(seg, i),
            }
            for i, seg in enumerate(doc.segments)
        ],
    }


def _related_knowledge_of(seg, argument: dict | None) -> str:
    """取同 argument_id 綁定的關聯知識（優先報告欄，再 segment）。"""
    if argument:
        rk = argument.get("related_knowledge")
        if isinstance(rk, str) and rk.strip():
            return rk
    raw = getattr(seg, "related_knowledge", None)
    if isinstance(raw, str) and raw.strip():
        return raw
    return ""


def to_markdown(doc: CorrectionDoc) -> str:
    """
    C3 鎖定格式：
      - original 段：原樣輸出(原文 immutable)。
      - supplement 段：'> 【補充】{text}' 後接 [^n] 註腳(每個來源一個)。
      - pending_evidence 段：【補充】後加 '⚠待補證 '(sources 空則無 footnote)。
    文末以 build_reference_lines(所有被引用 sources) 產參考區塊(C7 內含 Date)。
    footnote 編號與 cited 順序一致，交給 T11 重新列 [^1..n]。
    """
    report = build_binding_report(doc)
    argument_by_seg_index = {
        argument["segment_index"]: argument
        for argument in report["arguments"]
    }
    body: list[str] = []
    cited: list[Source] = []
    original_traces: list[str] = []
    counter = 0

    for seg_index, seg in enumerate(doc.segments):
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

        # 多層面必要性區塊：功能缺口 → 使用者價值 → 關聯知識 → 來源 → 角度
        functional_gap = getattr(seg, "functional_gap", "")
        if functional_gap:
            body.append(f"> **功能缺口**：{functional_gap}")

        user_value = getattr(seg, "user_value", "")
        if user_value:
            body.append(f"> **使用者價值**：{user_value}")

        argument = argument_by_seg_index.get(seg_index)
        related_knowledge = _related_knowledge_of(seg, argument)
        if related_knowledge:
            body.append(f"> **關聯知識**：{related_knowledge}")

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

        if argument:
            body.append(f"> **摘要可見**：{_visible_summary_text(argument)}")
            body.append(f"> **角度覆蓋**：{_argument_coverage_text(argument)}")

        argument_id = getattr(seg, "argument_id", "")
        if argument_id:
            body.append(f"> **論點ID**：{argument_id}")

    body.extend(original_traces)

    md = "\n\n".join(body)

    # 文末參考區塊：只放實際被引用(有進 body 的)sources，順序即 footnote 順序
    ref_block = build_reference_lines(cited)
    if ref_block:
        md = f"{md}\n\n{ref_block}"

    # 綁定驗證摘要行：可直接被測試解析的結構化文字
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
    angle_summary = report["angle_coverage_summary"]
    angle_verdict = "通過 ✓" if angle_summary["coverage_ok"] else "未通過 ✗"
    md += (
        "\n> **角度覆蓋摘要**："
        f"{angle_verdict}（有效角度 {angle_summary['effective_angle_count']}/"
        f"最低 {angle_summary['required_effective_angle_count']}；"
        f"排除重複 {angle_summary['excluded_angle_count']}；"
        f"重複率 {angle_summary['duplicate_ratio']:.3f}/"
        f"上限 {angle_summary['max_duplicate_ratio']:.3f}）"
    )
    
    # 北極星品質指標摘要：每則筆記同步帶出分數、判定依據與資料來源
    polaris = _calculate_polaris_for_doc(doc)
    md += (
        "\n> **北極星分數**："
        f"overall={polaris['overall_status']}"
        f"（pass {polaris['core_metrics_pass_count']}/{polaris['core_metrics_total_count']}）；"
        f"functional_gap={polaris['functional_gap_score']['score']:.2f}"
        f"（{'✓' if polaris['functional_gap_score']['passes_threshold'] else '✗'}）；"
        f"user_value={polaris['user_value_score']['score']:.2f}"
        f"（{'✓' if polaris['user_value_score']['passes_threshold'] else '✗'}）；"
        f"source_binding={polaris['source_binding_integrity']['score']:.2f}"
        f"（{'✓' if polaris['source_binding_integrity']['passes_threshold'] else '✗'}）；"
        f"angle_diversity={polaris['angle_diversity_index']['score']:.2f}"
        f"（{'✓' if polaris['angle_diversity_index']['passes_threshold'] else '✗'}）；"
        f"delivery={polaris['delivery_success_rate']['score']:.2f}"
        f"（{'✓' if polaris['delivery_success_rate']['passes_threshold'] else '✗'}）"
    )

    return md


def to_docx(doc: CorrectionDoc, path: str) -> None:
    """輸出 .docx 訂正稿,結構鏡射 to_markdown(原文 immutable、補充段標【補充】)。

    python-docx 原生 footnote 支援不佳,故 [^n] 以 inline 文字呈現、文末列參考來源。
    """
    from docx import Document as DocxDocument  # 延遲 import,不用 docx 輸出時免裝

    report = build_binding_report(doc)
    argument_by_seg_index = {
        argument["segment_index"]: argument
        for argument in report["arguments"]
    }
    out = DocxDocument()
    cited: list[Source] = []
    original_traces: list[str] = []
    counter = 0

    for seg_index, seg in enumerate(doc.segments):
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

        # 多層面必要性區塊：功能缺口 → 使用者價值 → 關聯知識 → 來源 → 角度
        functional_gap = getattr(seg, "functional_gap", "")
        if functional_gap:
            out.add_paragraph(f"功能缺口：{functional_gap}")

        user_value = getattr(seg, "user_value", "")
        if user_value:
            out.add_paragraph(f"使用者價值：{user_value}")

        argument = argument_by_seg_index.get(seg_index)
        related_knowledge = _related_knowledge_of(seg, argument)
        if related_knowledge:
            out.add_paragraph(f"關聯知識：{related_knowledge}")

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

        if argument:
            out.add_paragraph(f"摘要可見：{_visible_summary_text(argument)}")
            out.add_paragraph(f"角度覆蓋：{_argument_coverage_text(argument)}")

        argument_id = getattr(seg, "argument_id", "")
        if argument_id:
            out.add_paragraph(f"論點ID：{argument_id}")

    for trace in original_traces:
        out.add_paragraph(f"追溯：{trace}")

    ref_lines = build_reference_lines(cited).splitlines()
    if ref_lines:
        out.add_paragraph()
        for line in ref_lines:
            if line.strip():
                out.add_paragraph(line)

    angle_summary = report["angle_coverage_summary"]
    angle_verdict = "通過 ✓" if angle_summary["coverage_ok"] else "未通過 ✗"
    out.add_paragraph(
        f"角度覆蓋摘要：{angle_verdict}（"
        f"有效角度 {angle_summary['effective_angle_count']}/"
        f"最低 {angle_summary['required_effective_angle_count']}；"
        f"排除重複 {angle_summary['excluded_angle_count']}；"
        f"重複率 {angle_summary['duplicate_ratio']:.3f}/"
        f"上限 {angle_summary['max_duplicate_ratio']:.3f}）"
    )
    
    # 北極星品質指標摘要：每則筆記同步帶出分數、判定依據與資料來源
    polaris = _calculate_polaris_for_doc(doc)
    out.add_paragraph(
        f"北極星分數：overall={polaris['overall_status']}"
        f"（pass {polaris['core_metrics_pass_count']}/{polaris['core_metrics_total_count']}）；"
        f"functional_gap={polaris['functional_gap_score']['score']:.2f}"
        f"（{'✓' if polaris['functional_gap_score']['passes_threshold'] else '✗'}）；"
        f"user_value={polaris['user_value_score']['score']:.2f}"
        f"（{'✓' if polaris['user_value_score']['passes_threshold'] else '✗'}）；"
        f"source_binding={polaris['source_binding_integrity']['score']:.2f}"
        f"（{'✓' if polaris['source_binding_integrity']['passes_threshold'] else '✗'}）；"
        f"angle_diversity={polaris['angle_diversity_index']['score']:.2f}"
        f"（{'✓' if polaris['angle_diversity_index']['passes_threshold'] else '✗'}）；"
        f"delivery={polaris['delivery_success_rate']['score']:.2f}"
        f"（{'✓' if polaris['delivery_success_rate']['passes_threshold'] else '✗'}）"
    )

    out.save(path)
