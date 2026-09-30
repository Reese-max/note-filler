from __future__ import annotations

import json
from dataclasses import asdict

from typing import Any, Literal

from note_filler.angle_coverage import coverage_from_segment
from note_filler.binding_report import TRACEABILITY_FIELD_KEYS, build_binding_report
from note_filler.citation_formatter import build_reference_lines
from note_filler.correction import CorrectionDoc
from note_filler.metrics import calculate_polaris_metrics
from note_filler.review import ReviewLedger, ReviewState, doc_fingerprint, is_exportable
from note_filler.retrieve.models import Source

Cardinality = Literal["one_to_one", "one_to_many", "none"]

ExportMode = Literal["review-draft", "accepted-only"]

EXPORT_MODES = ("review-draft", "accepted-only")


def prepare_export(
    doc: CorrectionDoc, export_mode: ExportMode, ledger: ReviewLedger | None,
) -> tuple[CorrectionDoc, ReviewLedger | None]:
    """正文、統計與回執共用同一文件視圖,不修改原稿或研究結果。"""
    _validate_export_mode(export_mode)
    if ledger is not None and ledger.doc_fingerprint != doc_fingerprint(doc):
        ledger = None
    if export_mode == "accepted-only":
        doc = CorrectionDoc(original=doc.original, segments=[
            s for s in doc.segments
            if s.type != "supplement" or is_exportable(s, ledger)
        ])
    return doc, ledger


def _validate_export_mode(export_mode: str) -> None:
    """fail closed:未知匯出模式一律拒絕,不得靜默退回草稿模式。"""
    if export_mode not in EXPORT_MODES:
        raise ValueError(
            f"export_mode {export_mode!r} 非法(允許: {', '.join(EXPORT_MODES)})"
        )


def _review_state_line(detail: dict | None) -> str:
    """審查狀態單行(機器可解析 key=value):review_state/stale_reason/record 摘要。"""
    if detail is None:
        return "review_state=unreviewed"
    parts = [f"review_state={detail['state'].value}"]
    if detail.get("stale_reason"):
        parts.append(f"stale_reason={detail['stale_reason']}")
    rec = detail.get("record")
    if rec is not None:
        parts.append(f"reviewer={rec.reviewer}")
        parts.append(f"reviewed_at={rec.reviewed_at}")
        parts.append(f"reason_code={rec.reason_code or '-'}")
        parts.append(f"decision_id={rec.decision_id}")
    return "；".join(parts)


def _seg_review_state(seg, ledger: ReviewLedger | None) -> str:
    """segment 的有效審查狀態字串(無 ledger → unreviewed)。"""
    if ledger is None:
        return ReviewState.UNREVIEWED.value
    return ledger.state_of(seg).value


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
      3. 透過 calculate_polaris_metrics 計算五項分項與追溯性總分
      4. 回傳可序列化的 dict（含 overall_score、各分項分數、判定依據）
    
    判定依據：
      - functional_gap_score：可追溯性、覆蓋廣度、必要性明確度、決策助益加權分數
      - user_value_score：可追溯性、覆蓋廣度、必要性明確度、決策助益加權分數
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


def _quality_metadata(argument: dict, seg) -> str:
    """輸出 Markdown-only 品質量測所需的單行、結構化欄位。"""
    coverage = argument["angle_coverage"]
    anchor_idx = getattr(seg, "anchor_idx", None)
    argument_id = argument["argument_id"]
    topic = f"anchor:{anchor_idx}" if type(anchor_idx) is int else f"unanchored:{argument_id}"
    source_ids = list(argument.get("source_ids") or [])
    qualified_source_ids = (
        source_ids if getattr(seg, "confidence", None) == "verified" else []
    )
    return json.dumps(
        {
            "argument_id": argument_id,
            "topic": topic,
            "angle_tags": [coverage["angle_type"]],
            "qualified_source_ids": qualified_source_ids,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _argument_coverage_text(argument: dict, *, quality_metadata: str | None = None) -> str:
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
    
    text = (
        f"functional_gap={functional_gap or '（未提供）'}"
        f"；user_value={user_value or '（未提供）'}"
        f"；angle_tags={'、'.join(angle_tags) if angle_tags else '（無）'}"
        f"；source_ids={','.join(source_ids) if source_ids else 'pending（無來源）'}"
    )
    return f"{text}；quality_metadata={quality_metadata}" if quality_metadata else text


def _visible_summary_text(argument: dict) -> str:
    """同列顯示單一論點的功能缺口、使用者價值與關聯知識（同 argument_id）。"""
    related = argument.get("related_knowledge") or argument.get("summary") or ""
    return (
        f"argument_id={argument['argument_id']}"
        f"；functional_gap={argument['functional_gap'] or '（未提供）'}"
        f"；user_value={argument['user_value'] or '（未提供）'}"
        f"；related_knowledge={related}"
    )


def _argument_trace_text(argument: dict) -> str:
    """同列輸出來源片段、主張片段與主張內引用範圍。"""
    compact = {"ensure_ascii": False, "separators": (",", ":")}
    return (
        f"argument_id={argument['argument_id']}；"
        f"claim_fragment={json.dumps(argument['argument_text'], **compact)}；"
        f"source_fragments={json.dumps(argument['source_fragments'], **compact)}；"
        f"citation_spans={json.dumps(argument['citation_spans'], **compact)}"
    )


def _render_supplement_text(seg, source_numbers: dict[str, int]) -> str:
    """把 segment-local marker 改成成品全域註腳號，不新增虛構 marker。"""
    text = seg.text
    spans = [
        span
        for span in (getattr(seg, "citation_spans", None) or [])
        if isinstance(span, dict)
    ]
    for span in sorted(
        spans,
        key=lambda item: item.get("span_start")
        if type(item.get("span_start")) is int
        else -1,
        reverse=True,
    ):
        if span.get("source_id") not in source_numbers:
            continue
        start = span.get("span_start")
        end = span.get("span_end")
        marker = span.get("marker_text")
        if (
            type(start) is int
            and type(end) is int
            and isinstance(marker, str)
            and 0 <= start < end <= len(text)
            and text[start:end] == marker
        ):
            text = f"{text[:start]}[^{source_numbers[span['source_id']]}]{text[end:]}"
    return text


def _quality_score_breakdown_text(name: str, metric: dict[str, Any]) -> str:
    """將四子分數、總分門檻與公式壓成單行可解析文字。"""
    subscores = metric["subscores"]
    ordered = (
        "traceability",
        "coverage_breadth",
        "necessity_clarity",
        "decision_support",
    )
    values = ",".join(f"{key}:{subscores[key]['score']:.2f}" for key in ordered)
    return (
        f"{name}_subscores={values}；"
        f"{name}_total={metric['total_score']:.2f}；"
        f"{name}_threshold={metric['threshold']:.2f}；"
        f"{name}_formula=weighted_sum_0.25_each；"
        f"{name}_basis={metric['basis_mode']}:{len(metric['calculation_basis'])}_arguments"
    )


def _polaris_trace_lines(polaris: dict[str, Any]) -> list[str]:
    """將版本、公式、來源欄位、分數與判定輸出為固定可解析文字。"""
    traceability = polaris["traceability_score"]
    lines = [
        f"formula_version={polaris['formula_version']}",
        f"overall_score={polaris['overall_score']:.6f}；"
        f"formula={polaris['overall_score_formula']}；"
        f"score_if_traceability_complete={polaris['score_if_traceability_complete']:.6f}；"
        f"traceability_score={traceability['score']:.6f}；"
        f"traceability_penalty={traceability['penalty']:.6f}；"
        f"affected_argument_ids={','.join(traceability['affected_argument_ids'])}",
    ]
    for name in (
        "functional_gap_score",
        "user_value_score",
        "source_binding_integrity",
        "angle_diversity_index",
        "delivery_success_rate",
    ):
        metric = polaris[name]
        lines.append(
            f"metric={name}；formula={metric['formula']}；"
            f"source_fields={','.join(metric['source_fields'])}；"
            f"score={metric['score']:.6f}；decision={metric['decision']}"
        )
    lines.extend(
        f"{key}={json.dumps(polaris[key], ensure_ascii=False, separators=(',', ':'))}"
        for key in TRACEABILITY_FIELD_KEYS
    )
    return lines


def _source_comparison_rows(sources: list[Source]) -> list[dict]:
    """來源比較表：依層級（A→D）與相關性（distance 遞增）排序。"""
    sorted_srcs = sorted(
        sources,
        key=lambda s: ("ABCD".index(s.level) if s.level in "ABCD" else 99, s.distance),
    )
    return [
        {
            "id": s.id,
            "level": s.level,
            "title": s.title,
            "url": s.url,
            "doc_date": s.doc_date or s.fetched_date,
            "distance": s.distance,
            "content_summary": (s.content[:80] + "…") if len(s.content) > 80 else s.content,
        }
        for s in sorted_srcs
    ]


def _extended_readings_block(seg) -> list[str]:
    """延伸閱讀區塊：依優先級規則列出候選來源（Level A→D，同層級按 distance 遞增）。"""
    readings = list(getattr(seg, "extended_readings", None) or [])
    status = getattr(seg, "extended_readings_status", "none")
    reason = getattr(seg, "pending_evidence_reason", "")
    lines: list[str] = []
    
    # 依優先級排序延伸閱讀：Level A > B > C > D，同層級按 distance 遞增
    def reading_priority_key(r):
        level_order = {"A": 0, "B": 1, "C": 2, "D": 3}
        level_priority = level_order.get(r.get("level", "?"), 99)
        distance = r.get("distance", 1.0)
        return (level_priority, distance)
    
    sorted_readings = sorted(readings, key=reading_priority_key)
    
    if sorted_readings:
        lines.append("> **延伸閱讀**：")
        for r in sorted_readings:
            level = r.get("level", "?")
            title = r.get("title", "未知")
            rid = r.get("source_id", "")
            distance = r.get("distance", 0.0)
            lines.append(f"> - [{rid}] Level {level} {title} (相關性: {distance:.2f})")
    if reason:
        # pending_evidence 或 available 但未被引用：一律輸出待補證原因
        lines.append(f"> **待補證原因**：{reason}")
    return lines


def _discrepancy_notes(
    sources: list[Source], conflict_note: str | None = None
) -> list[str]:
    """來源差異分析：層級／日期／相關性差異。"""
    if not sources:
        return ["【待補來源】尚無可用來源"]
    notes = [f"來源衝突：{conflict_note}"] if conflict_note else []
    levels = sorted({s.level for s in sources if s.level in "ABCD"})
    if len(levels) > 1:
        notes.append(f"來源層級不一致（{'/'.join(levels)}）")
    dates = {s.doc_date or s.fetched_date for s in sources if s.doc_date or s.fetched_date}
    if len(dates) > 1:
        notes.append("來源日期不同")
    dists = [s.distance for s in sources]
    if len(dists) >= 2 and max(dists) - min(dists) > 0.2:
        notes.append("來源相關性距離差距顯著")
    return notes or ["來源一致，無顯著差異"]


def _usage_conditions(
    sources: list[Source],
    *,
    pending_evidence: bool = False,
    unresolved_conflict: bool = False,
) -> list[str]:
    """適用條件：依層級與距離建議各來源用途。"""
    if not sources:
        return ["【待補來源】缺乏可用來源，待補充後再評估"]
    if unresolved_conflict:
        return [
            f"{source.title}：【待補來源】來源互相衝突，現有資料無法判定適用條件"
            for source in sources
        ]
    if pending_evidence:
        return ["【待補來源】現有來源不足以支持此論點，待補合格來源後再評估"]
    sorted_srcs = sorted(
        sources,
        key=lambda s: ("ABCD".index(s.level) if s.level in "ABCD" else 99, s.distance),
    )
    return [
        (
            f"{s.title}（Level {s.level}，距離 {s.distance:.2f}）："
            f"適合作為{'主要依據' if i == 0 else '補充比對'}"
        )
        for i, s in enumerate(sorted_srcs)
    ]


def _integrated_conclusion(
    sources: list[Source],
    functional_gap: str,
    user_value: str,
    *,
    pending_evidence: bool = False,
    unresolved_conflict: bool = False,
) -> str:
    """可讀結論：說明何種情境採用哪個來源、何時判定為待補來源。"""
    if not sources:
        return "【待補來源】目前無可用來源，此論點需補齊相關資料後再行評估。"
    if unresolved_conflict:
        return "【待補來源】現有來源互相衝突且適用條件未明；保留各來源，不合併為單一結論。"
    if pending_evidence:
        return "【待補來源】現有來源不足以支持此論點，需補齊合格來源後再行評估。"
    best = max(
        sources,
        key=lambda s: ({"A": 4, "B": 3, "C": 2, "D": 1}.get(s.level, 0), -s.distance),
    )
    parts = [f"建議以 {best.title}（Level {best.level}）為主要引用來源"]
    if len(sources) > 1:
        others = [s for s in sources if s.id != best.id]
        parts.append(f"並以 {'、'.join(s.title for s in others)} 交叉驗證")
    if functional_gap:
        parts.append(f"對應功能缺口：{functional_gap}")
    return "。".join(parts) + "。"


def _three_part_annotation(seg) -> dict:
    """建立三種匯出格式共用的保守來源附註。"""
    sources = list(seg.sources)
    conflict_note = getattr(seg, "conflict_note", None)
    pending_evidence = seg.confidence == "pending_evidence"
    return {
        "source_comparison": _source_comparison_rows(sources),
        "discrepancy_notes": _discrepancy_notes(sources, conflict_note),
        "usage_conditions": _usage_conditions(
            sources,
            pending_evidence=pending_evidence,
            unresolved_conflict=bool(conflict_note),
        ),
        "conclusion": _integrated_conclusion(
            sources,
            getattr(seg, "functional_gap", ""),
            getattr(seg, "user_value", ""),
            pending_evidence=pending_evidence,
            unresolved_conflict=bool(conflict_note),
        ),
    }


def to_json(
    doc: CorrectionDoc,
    *,
    export_mode: ExportMode = "review-draft",
    ledger: ReviewLedger | None = None,
) -> dict:
    """序列化整份 CorrectionDoc；原文 immutable，僅讀不改。

    export_mode="accepted-only" 時只輸出 original 段與通過人工審查閘
    (is_exportable)的 supplement;review-draft(預設)保留全部並附逐段
    review_state 欄位。

    頂層含 binding_summary（整合 binding_report 的摘要）與 polaris_metrics（北極星品質指標），
    讓訂正稿 JSON 本身就可被測試直接解析驗證綁定狀態與品質分數。
    
    polaris_metrics 包含：
      - overall_status：整體品質判定（excellent/good/acceptable/poor/error）
      - overall_score / traceability_score：含追溯扣分與受影響論點的總分
      - core_metrics_pass_count：通過門檻的核心指標數
      - functional_gap_score / user_value_score / source_binding_integrity / 
        angle_diversity_index / delivery_success_rate：各分項分數與判定依據
    """
    doc, ledger = prepare_export(doc, export_mode, ledger)
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
        "export_mode": export_mode,
        "binding_summary": binding_summary,
        "angle_coverage_summary": dict(report.get("angle_coverage_summary") or {}),
        "polaris_metrics": polaris_metrics,
        "segments": [
            {
                "type": seg.type,
                "review_state": (
                    _seg_review_state(seg, ledger)
                    if seg.type == "supplement"
                    else None
                ),
                "text": seg.text,
                "anchor_idx": seg.anchor_idx,
                "confidence": seg.confidence,
                "conflict_note": getattr(seg, "conflict_note", None),
                "source_id": getattr(seg, "source_id", ""),
                "source_ids": _seg_source_ids(seg),
                "cardinality": _cardinality(len(_seg_source_ids(seg))),
                "traceability": list(getattr(seg, "traceability", [])),
                "citation_spans": [
                    dict(span)
                    for span in (getattr(seg, "citation_spans", None) or [])
                ],
                "sources": [_source_to_dict(s) for s in seg.sources],
                "functional_gap": getattr(seg, "functional_gap", ""),
                "user_value": getattr(seg, "user_value", ""),
                **_seg_argument_fields(seg, i),
                "angle_type": getattr(seg, "angle_type", "") or "",
                "angle_labels": list(getattr(seg, "angle_labels", None) or []),
                "angle_key": getattr(seg, "angle_key", "") or "",
                "angle_coverage": _seg_angle_coverage(seg, i),
                "three_part_annotation": _three_part_annotation(seg)
                if seg.type == "supplement"
                else None,
                # 延伸閱讀欄位順序：依格式規格 v1 定義
                "extended_readings": list(getattr(seg, "extended_readings", None) or []),
                "extended_readings_status": getattr(seg, "extended_readings_status", "none"),
                "pending_evidence_reason": getattr(seg, "pending_evidence_reason", ""),
                "openable_links_count": getattr(seg, "openable_links_count", 0),
                "openable_links_status": getattr(seg, "openable_links_status", "none"),
                "openable_links_incomplete_reason": getattr(seg, "openable_links_incomplete_reason", ""),
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


def to_markdown(
    doc: CorrectionDoc,
    *,
    export_mode: ExportMode = "review-draft",
    ledger: ReviewLedger | None = None,
) -> str:
    """
    C3 鎖定格式：
      - original 段：原樣輸出(原文 immutable)。
      - supplement 段：'> 【補充】{text}' 後接 [^n] 註腳(每個來源一個)。
      - pending_evidence 段：【補充】後加 '⚠待補證 '(sources 空則無 footnote)。
    文末以 build_reference_lines(所有被引用 sources) 產參考區塊(C7 內含 Date)。
    footnote 編號與 cited 順序一致，交給 T11 重新列 [^1..n]。

    匯出閘(issue #3):
      - review-draft(預設):每個 supplement 附「審查狀態」標記行,
        UNREVIEWED/STALE_REVIEW 等皆保留供審。
      - accepted-only:只輸出 original + 目前有效 ACCEPTED/EDITED_ACCEPTED
        且系統仍 verified 的 supplement;REJECTED/STALE/NEEDS_MORE_EVIDENCE/
        UNREVIEWED 一律排除(fail closed)。
    """
    doc, ledger = prepare_export(doc, export_mode, ledger)
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
        source_numbers: dict[str, int] = {}
        for src in seg.sources:
            counter += 1
            cited.append(src)
            source_numbers[src.id] = counter

        prefix = "> 【補充】"
        if seg.confidence == "pending_evidence":
            prefix += "⚠待補證 "
        conflict = getattr(seg, "conflict_note", None)
        if conflict:
            body.append(f"> ⚠️ **衝突告警**: {conflict}")
        body.append(f"{prefix}{_render_supplement_text(seg, source_numbers)}")
        if trace := _trace_text(seg):
            body.append(f"> 追溯：{trace}")

        # 審查狀態標記(review-draft 顯示當前決策;accepted-only 皆為已核准)
        detail = ledger.state_detail(seg) if ledger is not None else None
        body.append(f"> **審查狀態**：{_review_state_line(detail)}")

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
            body.append(
                "> **角度覆蓋**："
                f"{_argument_coverage_text(argument, quality_metadata=_quality_metadata(argument, seg))}"
            )
            body.append(f"> **論點追溯**：{_argument_trace_text(argument)}")

        argument_id = getattr(seg, "argument_id", "")
        if argument_id:
            body.append(f"> **論點ID**：{argument_id}")

        # 三段式附註：來源比較／差異分析／適用條件／可讀結論
        annotation = _three_part_annotation(seg)
        if annotation["source_comparison"]:
            body.append("> **來源比較**：")
            for row in annotation["source_comparison"]:
                row_id = row.get("id", "?")
                level = row.get("level", "?")
                title = row.get("title", "?")
                url = row.get("url") or "無URL"
                distance = row.get("distance", 0.0)
                summary = row.get("content_summary", "")
                body.append(f"> - {row_id}（Level {level}）{title} | URL: {url} | 距離: {distance:.2f} | {summary}")
        else:
            body.append("> **來源比較**：【待補來源】")
        for note in annotation["discrepancy_notes"]:
            body.append(f"> **差異分析**：{note}")
        for cond in annotation["usage_conditions"]:
            body.append(f"> **適用條件**：{cond}")
        body.append(f"> **結論**：{annotation['conclusion']}")

        # 可開啟連結不足時輸出【待補來源】標記
        openable_status = getattr(seg, "openable_links_status", "none")
        if openable_status == "insufficient":
            incomplete_reason = getattr(seg, "openable_links_incomplete_reason", "")
            body.append(f"> **【待補來源】**：可開啟連結不足——{incomplete_reason}")

        # 延伸閱讀區塊：附加於論點尾端，不影響原稿
        body.extend(_extended_readings_block(seg))

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
        f"overall_score={polaris['overall_score']:.2f}；"
        f"traceability={polaris['traceability_score']['score']:.2f}"
        f"（扣分 {polaris['traceability_score']['penalty']:.2f}；"
        f"待修 {','.join(polaris['traceability_score']['affected_argument_ids']) or '無'}）；"
        f"functional_gap={polaris['functional_gap_score']['score']:.2f}"
        f"（{'✓' if polaris['functional_gap_score']['passes_threshold'] else '✗'}）；"
        f"user_value={polaris['user_value_score']['score']:.2f}"
        f"（{'✓' if polaris['user_value_score']['passes_threshold'] else '✗'}）；"
        f"source_binding={polaris['source_binding_integrity']['score']:.2f}"
        f"（{'✓' if polaris['source_binding_integrity']['passes_threshold'] else '✗'}）；"
        f"angle_diversity={polaris['angle_diversity_index']['score']:.2f}"
        f"（{'✓' if polaris['angle_diversity_index']['passes_threshold'] else '✗'}）；"
        f"delivery={polaris['delivery_success_rate']['score']:.2f}"
        f"（{'✓' if polaris['delivery_success_rate']['passes_threshold'] else '✗'}）；"
        f"{_quality_score_breakdown_text('functional_gap', polaris['functional_gap_score'])}；"
        f"{_quality_score_breakdown_text('user_value', polaris['user_value_score'])}"
    )
    md += "".join(f"\n> **北極星追蹤**：{line}" for line in _polaris_trace_lines(polaris))

    return f"> **匯出模式**：export_mode={export_mode}\n\n{md}"


def to_docx(
    doc: CorrectionDoc,
    path: str,
    *,
    export_mode: ExportMode = "review-draft",
    ledger: ReviewLedger | None = None,
) -> None:
    """輸出 .docx 訂正稿,結構鏡射 to_markdown(原文 immutable、補充段標【補充】)。

    python-docx 原生 footnote 支援不佳,故 [^n] 以 inline 文字呈現、文末列參考來源。
    export_mode="accepted-only" 時只輸出 original 與通過人工審查閘的 supplement。
    """
    from docx import Document as DocxDocument  # 延遲 import,不用 docx 輸出時免裝

    doc, ledger = prepare_export(doc, export_mode, ledger)
    report = build_binding_report(doc)
    argument_by_seg_index = {
        argument["segment_index"]: argument
        for argument in report["arguments"]
    }
    out = DocxDocument()
    out.sections[0].header.paragraphs[0].text = f"匯出模式：export_mode={export_mode}"
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
        source_numbers: dict[str, int] = {}
        for src in seg.sources:
            counter += 1
            cited.append(src)
            source_numbers[src.id] = counter
        conflict = getattr(seg, "conflict_note", None)
        if conflict:
            p_conflict = out.add_paragraph()
            run_conflict = p_conflict.add_run(f"⚠️ 衝突告警: {conflict}")
            run_conflict.bold = True
        prefix = "【補充】" + ("⚠待補證 " if seg.confidence == "pending_evidence" else "")
        p = out.add_paragraph()
        run = p.add_run(f"{prefix}{_render_supplement_text(seg, source_numbers)}")
        run.italic = True  # 補充段視覺區隔於原文
        if trace := _trace_text(seg):
            out.add_paragraph(f"追溯：{trace}")

        detail = ledger.state_detail(seg) if ledger is not None else None
        out.add_paragraph(f"審查狀態：{_review_state_line(detail)}")

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
            out.add_paragraph(f"論點追溯：{_argument_trace_text(argument)}")

        argument_id = getattr(seg, "argument_id", "")
        if argument_id:
            out.add_paragraph(f"論點ID：{argument_id}")

        # 三段式附註：來源比較／差異分析／適用條件／可讀結論
        annotation = _three_part_annotation(seg)
        if annotation["source_comparison"]:
            out.add_paragraph("來源比較：")
            for row in annotation["source_comparison"]:
                row_id = row.get("id", "?")
                level = row.get("level", "?")
                title = row.get("title", "?")
                url = row.get("url") or "無URL"
                distance = row.get("distance", 0.0)
                summary = row.get("content_summary", "")
                out.add_paragraph(f"  {row_id}（Level {level}）{title} | URL: {url} | 距離: {distance:.2f} | {summary}")
        else:
            out.add_paragraph("來源比較：【待補來源】")
        for note in annotation["discrepancy_notes"]:
            out.add_paragraph(f"差異分析：{note}")
        for cond in annotation["usage_conditions"]:
            out.add_paragraph(f"適用條件：{cond}")
        out.add_paragraph(f"結論：{annotation['conclusion']}")

        # 可開啟連結不足時輸出【待補來源】標記
        openable_status = getattr(seg, "openable_links_status", "none")
        if openable_status == "insufficient":
            incomplete_reason = getattr(seg, "openable_links_incomplete_reason", "")
            out.add_paragraph(f"【待補來源】可開啟連結不足——{incomplete_reason}")

        # 延伸閱讀區塊：依優先級規則列出（Level A→D，同層級按 distance 遞增）
        readings = list(getattr(seg, "extended_readings", None) or [])
        status = getattr(seg, "extended_readings_status", "none")
        reason = getattr(seg, "pending_evidence_reason", "")
        
        # 依優先級排序延伸閱讀
        def reading_priority_key(r):
            level_order = {"A": 0, "B": 1, "C": 2, "D": 3}
            level_priority = level_order.get(r.get("level", "?"), 99)
            distance = r.get("distance", 1.0)
            return (level_priority, distance)
        
        sorted_readings = sorted(readings, key=reading_priority_key)
        
        if sorted_readings:
            out.add_paragraph("延伸閱讀：")
            for r in sorted_readings:
                level = r.get("level", "?")
                title = r.get("title", "未知")
                rid = r.get("source_id", "")
                distance = r.get("distance", 0.0)
                out.add_paragraph(f"  [{rid}] Level {level} {title} (相關性: {distance:.2f})")
        if reason:
            out.add_paragraph(f"待補證原因：{reason}")

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
        f"overall_score={polaris['overall_score']:.2f}；"
        f"traceability={polaris['traceability_score']['score']:.2f}"
        f"（扣分 {polaris['traceability_score']['penalty']:.2f}；"
        f"待修 {','.join(polaris['traceability_score']['affected_argument_ids']) or '無'}）；"
        f"functional_gap={polaris['functional_gap_score']['score']:.2f}"
        f"（{'✓' if polaris['functional_gap_score']['passes_threshold'] else '✗'}）；"
        f"user_value={polaris['user_value_score']['score']:.2f}"
        f"（{'✓' if polaris['user_value_score']['passes_threshold'] else '✗'}）；"
        f"source_binding={polaris['source_binding_integrity']['score']:.2f}"
        f"（{'✓' if polaris['source_binding_integrity']['passes_threshold'] else '✗'}）；"
        f"angle_diversity={polaris['angle_diversity_index']['score']:.2f}"
        f"（{'✓' if polaris['angle_diversity_index']['passes_threshold'] else '✗'}）；"
        f"delivery={polaris['delivery_success_rate']['score']:.2f}"
        f"（{'✓' if polaris['delivery_success_rate']['passes_threshold'] else '✗'}）；"
        f"{_quality_score_breakdown_text('functional_gap', polaris['functional_gap_score'])}；"
        f"{_quality_score_breakdown_text('user_value', polaris['user_value_score'])}"
    )
    for line in _polaris_trace_lines(polaris):
        out.add_paragraph(f"北極星追蹤：{line}")

    out.save(path)
