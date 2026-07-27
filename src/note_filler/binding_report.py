"""可機器比對的論點—來源綁定報告。

產出固定 schema 的 JSON 結構，讓測試／下游可直接解析並逐項驗證每個論點：
  1. 至少一個來源（at_least_one_source）
  2. 來源可追溯（source_traceable：sources ↔ traceability 對齊）
  3. 無重複遺漏（no_duplicate_sources + no_omitted_traces + no_extra_traces）
  4. 摘要已落地成品（summary_matches_product）
  5. 關聯知識與功能缺口／使用者價值跨欄位一致

明確標示 cardinality：
  - one_to_one：剛好一個來源
  - one_to_many：兩個以上來源
  - none：無來源（通常 pending_evidence）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from note_filler.angle_coverage import (
    attach_relations,
    build_angle_field_issues,
    build_argument_angle_fields,
    coverage_from_segment,
    is_angle_coverage_complete,
    summarize_angle_coverage,
    validate_argument_angle,
)
from note_filler.correction import (
    build_related_knowledge,
    related_knowledge_explains_value,
    related_knowledge_matches_views,
)
from note_filler.write import CITATION_SPAN_KEYS, citation_span_issues

SCHEMA_ID = "note_filler.binding_report.v1"
BINDING_REPORT_NAME = "binding_report.json"

TRACEABILITY_MARKER_KEYS = ("argument_id", "kind", "id", "binding_status")
SOURCE_FRAGMENT_KEYS = ("source_id", "text")
CITATION_SPAN_MAP_KEYS = (
    "segment_index",
    "argument_id",
    "source_id",
    "span_start",
    "span_end",
    "marker_text",
)
TRACEABILITY_FIELD_KEYS = (
    "traceability_markers",
    "claim_source_map",
    "citation_span_map",
)

Cardinality = Literal["one_to_one", "one_to_many", "none"]
BindingStatus = Literal["pass", "fail", "pending_evidence"]

# 測試可直接 import 的固定欄位契約
REQUIRED_TOP_KEYS = frozenset(
    {
        "schema",
        "source_path",
        "argument_count",
        "summary",
        "arguments",
        "source_usage",
        "angle_coverage_summary",
        *TRACEABILITY_FIELD_KEYS,
    }
)
REQUIRED_ARGUMENT_ANGLE_KEYS = frozenset(
    {
        "angle_tags",
        "valid_angle_count",
        "deduped_angle_count",
        "duplicate_angles",
        # 角度有效性：缺少或被排除的角度欄位（空 list 表示通過）
        "angle_field_issues",
    }
)
REQUIRED_ARGUMENT_KEYS = frozenset(
    {
        "argument_index",
        "argument_id",
        "segment_index",
        "argument_text",
        "summary",
        "confidence",
        "cardinality",
        "source_count",
        "source_ids",
        "trace_source_ids",
        "source_fragments",
        "citation_spans",
        "source_id_field",
        "checks",
        "binding_status",
        "binding_ok",
        "functional_gap",
        "user_value",
        # 關聯知識：與同一 argument_id 綁定，明示決策品質／使用者理解
        "related_knowledge",
        "angle_coverage",
    }
) | REQUIRED_ARGUMENT_ANGLE_KEYS
REQUIRED_CHECK_KEYS = frozenset(
    {
        "at_least_one_source",
        "source_traceable",
        "no_duplicate_sources",
        "no_omitted_traces",
        "no_extra_traces",
        "source_id_field_aligned",
        "no_empty_fragments",
        # 必要性雙視角：來源可追溯仍不得遺失功能缺口／使用者價值
        "has_functional_gap",
        "has_user_value",
        # 關聯知識：須明示如何支撐決策品質、如何補強使用者理解
        "has_related_knowledge",
        # 三欄須指向同一主題，不得各寫各的
        "related_knowledge_consistent",
        "summary_matches_product",
        # 角度覆蓋：論點須具備可機器讀的角度標籤／面向
        "has_angle_coverage",
        "meets_angle_coverage_threshold",
        # 角度有效性：每個 argument 必須具備完整四類 facet（angle type、functional_gap、user_value、question）
        "angle_facet_complete",
        "angle_functional_gap_present",
        "angle_user_value_present",
        "angle_question_present",
    }
)
REQUIRED_SUMMARY_KEYS = frozenset(
    {
        "one_to_one",
        "one_to_many",
        "none",
        "pass",
        "fail",
        "pending_evidence",
        "all_sourced_arguments_ok",
        "all_arguments_ok",
    }
)
REQUIRED_ANGLE_COVERAGE_KEYS = frozenset(
    {
        "angle_type",
        "angle_labels",
        "covered_facets",
        "angle_key",
        "relation",
        "effective_angle_count",
        "duplicate_exclusion",
    }
)
REQUIRED_ANGLE_RELATION_KEYS = frozenset(
    {
        "kind",
        "related_argument_indices",
        "duplicate_of",
        "synonym_of",
    }
)
REQUIRED_DUPLICATE_EXCLUSION_KEYS = frozenset(
    {
        "excluded",
        "reason",
        "kept_argument_index",
    }
)
REQUIRED_ANGLE_SUMMARY_KEYS = frozenset(
    {
        "unique_angle_types",
        "covered_facets_union",
        "duplicate_pairs",
        "synonym_pairs",
        "argument_count_with_angles",
        "effective_angle_count",
        "excluded_angle_count",
        "duplicate_ratio",
        "required_effective_angle_count",
        "max_duplicate_ratio",
        "has_sufficient_angles",
        "has_acceptable_duplicate_ratio",
        "coverage_ok",
    }
)

# 結構性必填非空字串（枚舉／狀態）；source_id_field 可空（語意 fail，非結構錯誤）
# functional_gap／user_value／related_knowledge 空欄以 checks + binding_ok 拒絕，仍可解析以指出缺失項
_ARGUMENT_NONEMPTY_STR_KEYS = frozenset(
    {
        "argument_text",
        "summary",
        "confidence",
        "cardinality",
        "binding_status",
        "argument_id",
    }
)


def _source_ids(seg) -> list[str]:
    ids: list[str] = []
    for src in getattr(seg, "sources", None) or []:
        sid = getattr(src, "id", None)
        if isinstance(sid, str) and sid.strip():
            ids.append(sid)
    return ids


def _no_empty_fragments(seg) -> bool:
    """來源有 ID 但 content 為空白 → False。"""
    for src in getattr(seg, "sources", None) or []:
        sid = getattr(src, "id", None)
        if not isinstance(sid, str) or not sid.strip():
            continue
        content = getattr(src, "content", None) or ""
        if not content.strip():
            return False
    return True


def _trace_source_ids(seg) -> list[str]:
    ids: list[str] = []
    for ref in getattr(seg, "traceability", None) or []:
        if not isinstance(ref, dict):
            continue
        if ref.get("kind") != "source":
            continue
        rid = ref.get("id")
        if isinstance(rid, str) and rid.strip():
            ids.append(rid)
    return ids


def _source_fragments(seg) -> list[dict[str, str]]:
    """把實際掛入成品的來源內容投影為固定鍵序片段。"""
    return [
        {"source_id": src.id, "text": src.content}
        for src in (getattr(seg, "sources", None) or [])
        if isinstance(getattr(src, "id", None), str)
    ]


def _citation_spans(seg) -> list:
    raw = getattr(seg, "citation_spans", None)
    if not isinstance(raw, list):
        return []
    return [dict(item) if isinstance(item, dict) else item for item in raw]


def _cardinality(source_count: int) -> Cardinality:
    if source_count <= 0:
        return "none"
    if source_count == 1:
        return "one_to_one"
    return "one_to_many"


def _summarize_bindings(arguments: list[dict[str, Any]]) -> dict[str, Any]:
    sourced = [a for a in arguments if a["cardinality"] != "none"]
    return {
        "one_to_one": sum(a["cardinality"] == "one_to_one" for a in arguments),
        "one_to_many": sum(a["cardinality"] == "one_to_many" for a in arguments),
        "none": sum(a["cardinality"] == "none" for a in arguments),
        "pass": sum(a["binding_status"] == "pass" for a in arguments),
        "fail": sum(a["binding_status"] == "fail" for a in arguments),
        "pending_evidence": sum(
            a["binding_status"] == "pending_evidence" for a in arguments
        ),
        "all_sourced_arguments_ok": (
            all(a["binding_ok"] for a in sourced) if sourced else True
        ),
        "all_arguments_ok": (
            all(a["binding_ok"] for a in arguments) if arguments else True
        ),
    }


def _pending_traceable(seg) -> bool:
    """無來源段：processing_record 必須可追溯。"""
    refs = getattr(seg, "traceability", None) or []
    if len(refs) != 1 or not isinstance(refs[0], dict):
        return False
    ref = refs[0]
    conf = getattr(seg, "confidence", None)
    return (
        ref.get("kind") == "processing_record"
        and bool(ref.get("id"))
        and bool(ref.get("question"))
        and ref.get("outcome") == conf
    )


def _evaluate_argument(seg, *, argument_index: int, segment_index: int) -> dict[str, Any]:
    source_ids = _source_ids(seg)
    trace_ids = _trace_source_ids(seg)
    raw_citation_spans = getattr(seg, "citation_spans", None)
    citation_spans = _citation_spans(seg)
    span_issues = citation_span_issues(text=getattr(seg, "text", "") or "", source_ids=source_ids, citation_spans=raw_citation_spans)
    span_ids = [
        item.get("source_id")
        for item in citation_spans
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    ]
    sid_field = getattr(seg, "source_id", None) or ""
    confidence = getattr(seg, "confidence", None) or ""
    text = getattr(seg, "text", None) or ""
    summary = getattr(seg, "summary", None)
    if summary is None:  # 相容既有手建 Segment；正式組裝一律顯式寫入。
        summary = text
    summary_matches_product = summary == text
    cardinality = _cardinality(len(source_ids))
    functional_gap = getattr(seg, "functional_gap", "") or ""
    user_value = getattr(seg, "user_value", "") or ""
    if not isinstance(functional_gap, str):
        functional_gap = str(functional_gap)
    if not isinstance(user_value, str):
        user_value = str(user_value)
    has_functional_gap = bool(functional_gap.strip())
    has_user_value = bool(user_value.strip())

    # 關聯知識：None＝相容手建 Segment 自動合成；空字串＝明確缺欄
    raw_related = getattr(seg, "related_knowledge", None)
    if raw_related is None:
        related_knowledge = build_related_knowledge(
            knowledge_body=summary,
            functional_gap=functional_gap,
            user_value=user_value,
        )
    elif not isinstance(raw_related, str):
        related_knowledge = str(raw_related)
    else:
        related_knowledge = raw_related
    has_related_knowledge = related_knowledge_explains_value(related_knowledge)
    related_knowledge_consistent = related_knowledge_matches_views(
        related_knowledge,
        functional_gap=functional_gap,
        user_value=user_value,
    )

    # 角度覆蓋（暫不含 relation；整份 arguments 組齊後再 attach）
    angle_coverage = coverage_from_segment(seg)
    has_angle_coverage = is_angle_coverage_complete(angle_coverage)

    # 論點 ID（用於錯誤訊息定位）
    argument_id = getattr(seg, "argument_id", None) or f"argument:{argument_index}"

    # 角度有效性驗證：每個 argument 必須具備四類必要 facet
    angle_valid, angle_missing = validate_argument_angle(angle_coverage, argument_id=argument_id)
    angle_facet_complete = angle_valid
    angle_functional_gap_present = not any("functional_gap" in m for m in angle_missing)
    angle_user_value_present = not any("user_value" in m for m in angle_missing)
    angle_question_present = not any("question" in m for m in angle_missing)

    no_dup = len(source_ids) == len(set(source_ids))
    # 追溯側亦不得重複
    no_dup_trace = len(trace_ids) == len(set(trace_ids))
    no_duplicate_sources = no_dup and no_dup_trace

    source_set = set(source_ids)
    trace_set = set(trace_ids)
    span_set = set(span_ids)
    no_omitted = source_set <= trace_set and source_set <= span_set
    no_extra = trace_set <= source_set and span_set <= source_set

    if source_ids:
        expected_field = f"sources:{','.join(source_ids)}"
        source_id_aligned = sid_field == expected_field
        at_least_one = True
        # 可追溯：來源、trace 與主張內 citation span 三向對齊。
        source_traceable = (
            trace_ids == source_ids
            and not span_issues
            and no_omitted
            and no_extra
        )
    else:
        expected_field_ok = isinstance(sid_field, str) and sid_field.startswith(
            "pending:gap:"
        )
        source_id_aligned = expected_field_ok
        at_least_one = False
        source_traceable = _pending_traceable(seg) and not span_issues
        # 無來源時不可殘留來源 trace 或 citation span。
        no_omitted = True
        no_extra = not trace_set and not span_set

    no_empty_fragments = _no_empty_fragments(seg)

    checks = {
        "at_least_one_source": at_least_one,
        "source_traceable": source_traceable,
        "no_duplicate_sources": no_duplicate_sources,
        "no_omitted_traces": no_omitted,
        "no_extra_traces": no_extra,
        "source_id_field_aligned": source_id_aligned,
        "no_empty_fragments": no_empty_fragments,
        "has_functional_gap": has_functional_gap,
        "has_user_value": has_user_value,
        "has_related_knowledge": has_related_knowledge,
        "related_knowledge_consistent": related_knowledge_consistent,
        "summary_matches_product": summary_matches_product,
        "has_angle_coverage": has_angle_coverage,
        # 角度有效性檢查
        "angle_facet_complete": angle_facet_complete,
        "angle_functional_gap_present": angle_functional_gap_present,
        "angle_user_value_present": angle_user_value_present,
        "angle_question_present": angle_question_present,
        # 跨論點量測完成後覆寫。
        "meets_angle_coverage_threshold": True,
    }

    necessity_ok = (
        has_functional_gap
        and has_user_value
        and has_related_knowledge
        and related_knowledge_consistent
    )
    angle_ok = has_angle_coverage and angle_facet_complete

    # 有來源：核心綁定 + 對齊 + 片段非空 + 必要性雙視角 + 角度覆蓋皆須通過
    if source_ids:
        binding_ok = all(
            (
                checks["at_least_one_source"],
                checks["source_traceable"],
                checks["no_duplicate_sources"],
                checks["no_omitted_traces"],
                checks["no_extra_traces"],
                checks["source_id_field_aligned"],
                checks["no_empty_fragments"],
                summary_matches_product,
                necessity_ok,
                angle_ok,
            )
        )
        status: BindingStatus = "pass" if binding_ok else "fail"
    else:
        # 無來源：必須為 pending 且 processing_record 可追溯，且必要性／角度仍在
        intentional_pending = (
            confidence == "pending_evidence"
            and source_traceable
            and source_id_aligned
            and summary_matches_product
            and necessity_ok
            and angle_ok
        )
        binding_ok = intentional_pending
        status = "pending_evidence" if intentional_pending else "fail"

    return {
        "argument_index": argument_index,
        "argument_id": argument_id,
        "segment_index": segment_index,
        "argument_text": text,
        "summary": summary,
        "confidence": confidence,
        "cardinality": cardinality,
        "source_count": len(source_ids),
        "source_ids": list(source_ids),
        "trace_source_ids": list(trace_ids),
        "source_fragments": _source_fragments(seg),
        "citation_spans": citation_spans,
        "source_id_field": sid_field,
        "checks": checks,
        "binding_status": status,
        "binding_ok": binding_ok,
        "functional_gap": functional_gap,
        "user_value": user_value,
        "related_knowledge": related_knowledge,
        "angle_coverage": angle_coverage,
    }


def _build_traceability_fields(
    segments: list,
    arguments: list[dict[str, Any]],
) -> dict[str, Any]:
    """由同一份 argument/segment 資料建立三個固定序列化投影。"""
    markers: list[dict[str, Any]] = []
    claim_source_map: dict[str, list[str]] = {}
    span_map: list[dict[str, Any]] = []

    for argument in arguments:
        argument_id = argument["argument_id"]
        segment_index = argument["segment_index"]
        segment = segments[segment_index]
        claim_source_map[argument_id] = list(argument["source_ids"])

        for ref in getattr(segment, "traceability", None) or []:
            if not isinstance(ref, dict) or ref.get("kind") not in (
                "source",
                "processing_record",
            ):
                continue
            ref_id = ref.get("id")
            if not isinstance(ref_id, str) or not ref_id.strip():
                continue
            markers.append(
                {
                    "argument_id": argument_id,
                    "kind": ref["kind"],
                    "id": ref_id,
                    "binding_status": argument["binding_status"],
                }
            )

        for span in argument["citation_spans"]:
            if not isinstance(span, dict) or tuple(span) != CITATION_SPAN_KEYS:
                continue
            span_map.append(
                {
                    "segment_index": segment_index,
                    "argument_id": argument_id,
                    "source_id": span["source_id"],
                    "span_start": span["span_start"],
                    "span_end": span["span_end"],
                    "marker_text": span["marker_text"],
                }
            )

    span_map.sort(
        key=lambda item: (
            item["segment_index"],
            item["span_start"],
            item["span_end"],
            item["source_id"],
        )
    )
    return {
        "traceability_markers": markers,
        "claim_source_map": claim_source_map,
        "citation_span_map": span_map,
    }


def build_binding_report(correction) -> dict[str, Any]:
    """從 CorrectionDoc 建可機器解析的綁定報告（純函式、不改 doc）。

    只掃描 type==\"supplement\" 的段（論點／補充）；original 不列為論點綁定項。
    """
    original = getattr(correction, "original", None)
    source_path = getattr(original, "source_path", None) or ""
    segments = list(getattr(correction, "segments", None) or [])

    arguments: list[dict[str, Any]] = []
    arg_i = 0
    for seg_i, seg in enumerate(segments):
        if getattr(seg, "type", None) != "supplement":
            continue
        arguments.append(
            _evaluate_argument(seg, argument_index=arg_i, segment_index=seg_i)
        )
        arg_i += 1

    # 角度覆蓋：跨論點判定重複／同義，並寫回 relation
    bare_coverages = [dict(a["angle_coverage"]) for a in arguments]
    with_relations = attach_relations(bare_coverages)
    for a, cov in zip(arguments, with_relations):
        a["angle_coverage"] = cov
        a.update(
            build_argument_angle_fields(
                cov,
                argument_id=a["argument_id"],
                coverages=with_relations,
            )
        )
    angle_summary = summarize_angle_coverage(with_relations)
    angle_gate_ok = angle_summary["coverage_ok"]
    for argument in arguments:
        argument["checks"]["meets_angle_coverage_threshold"] = angle_gate_ok
        # 明確列出缺少或被排除的角度欄位（單一角度／缺失／同義重複）
        argument["angle_field_issues"] = build_angle_field_issues(
            argument["angle_coverage"],
            argument_id=argument["argument_id"],
            angle_gate_ok=angle_gate_ok,
            effective_angle_count=angle_summary["effective_angle_count"],
            required_effective_angle_count=angle_summary[
                "required_effective_angle_count"
            ],
        )
        if not angle_gate_ok or argument["angle_field_issues"]:
            # 角度有效性未過 → 驗收明確失敗（來源 checks 仍保留原判定）
            argument["binding_ok"] = False
            argument["binding_status"] = "fail"

    # 反向索引：每個 source_id → 使用了它的 argument_indices
    source_usage: dict[str, list[int]] = {}
    for a in arguments:
        for sid in a["source_ids"]:
            source_usage.setdefault(sid, []).append(a["argument_index"])
    source_usage = dict(sorted(
        {k: sorted(v) for k, v in source_usage.items()}.items()
    ))
    traceability_fields = _build_traceability_fields(segments, arguments)

    return {
        "schema": SCHEMA_ID,
        "source_path": source_path,
        "argument_count": len(arguments),
        "summary": _summarize_bindings(arguments),
        "arguments": arguments,
        "source_usage": source_usage,
        "angle_coverage_summary": angle_summary,
        **traceability_fields,
    }


def _reject_key_drift(actual: Any, required: frozenset[str], *, where: str) -> None:
    """鎖定欄位契約：缺欄或未知欄（欄位漂移）一律拒絕。"""
    if not isinstance(actual, dict):
        raise ValueError(f"{where} 必須為 dict")
    keys = set(actual.keys())
    missing = required - keys
    if missing:
        raise ValueError(f"{where} 缺少欄位: {sorted(missing)}")
    extra = keys - required
    if extra:
        raise ValueError(f"{where} 含未知欄位（欄位漂移）: {sorted(extra)}")


def _validate_traceability_fields(
    data: dict[str, Any],
    arguments: list[dict[str, Any]],
) -> None:
    """鎖定三欄結構、順序及其與逐論點資料的一致性。"""
    argument_ids = [argument["argument_id"] for argument in arguments]
    by_id = {argument["argument_id"]: argument for argument in arguments}

    claim_map = data.get("claim_source_map")
    if not isinstance(claim_map, dict) or list(claim_map) != argument_ids:
        raise ValueError("claim_source_map 鍵序或 argument_id 覆蓋不一致")
    expected_claim_map = {
        argument["argument_id"]: list(argument["source_ids"])
        for argument in arguments
    }
    if claim_map != expected_claim_map:
        raise ValueError("claim_source_map 與 arguments[].source_ids 不一致")

    markers = data.get("traceability_markers")
    if not isinstance(markers, list):
        raise ValueError("traceability_markers 必須為 list")
    marker_groups: dict[str, list[dict[str, Any]]] = {
        argument_id: [] for argument_id in argument_ids
    }
    for index, marker in enumerate(markers):
        where = f"traceability_markers[{index}]"
        if not isinstance(marker, dict) or tuple(marker) != TRACEABILITY_MARKER_KEYS:
            raise ValueError(f"{where} 欄位或序列漂移")
        argument = by_id.get(marker["argument_id"])
        if argument is None:
            raise ValueError(f"{where}.argument_id 指向未知論點")
        if marker["kind"] not in ("source", "processing_record"):
            raise ValueError(f"{where}.kind 非法")
        if not isinstance(marker["id"], str) or not marker["id"].strip():
            raise ValueError(f"{where}.id 必須為非空字串")
        if marker["binding_status"] != argument["binding_status"]:
            raise ValueError(f"{where}.binding_status 與論點不一致")
        marker_groups[marker["argument_id"]].append(marker)

    spans = data.get("citation_span_map")
    if not isinstance(spans, list):
        raise ValueError("citation_span_map 必須為 list")
    for index, span in enumerate(spans):
        if not isinstance(span, dict) or tuple(span) != CITATION_SPAN_MAP_KEYS:
            raise ValueError(f"citation_span_map[{index}] 欄位或序列漂移")
    expected_spans = [
        {
            "segment_index": argument["segment_index"],
            "argument_id": argument["argument_id"],
            "source_id": span["source_id"],
            "span_start": span["span_start"],
            "span_end": span["span_end"],
            "marker_text": span["marker_text"],
        }
        for argument in arguments
        for span in argument["citation_spans"]
    ]
    expected_spans.sort(
        key=lambda item: (
            item["segment_index"],
            item["span_start"],
            item["span_end"],
            item["source_id"],
        )
    )
    if spans != expected_spans:
        raise ValueError("citation_span_map 與 arguments[].citation_spans 不一致")

    span_pairs = {
        (span["argument_id"], span["source_id"])
        for span in spans
    }
    marker_pairs = {
        (marker["argument_id"], marker["id"])
        for marker in markers
        if marker["kind"] == "source"
    }
    source_pairs = {
        (argument_id, source_id)
        for argument_id, source_ids in claim_map.items()
        for source_id in source_ids
    }
    for argument in arguments:
        argument_id = argument["argument_id"]
        grouped = marker_groups[argument_id]
        source_marker_ids = [
            marker["id"] for marker in grouped if marker["kind"] == "source"
        ]
        processing_markers = [
            marker for marker in grouped if marker["kind"] == "processing_record"
        ]
        if source_marker_ids != argument["trace_source_ids"]:
            raise ValueError(f"{argument_id} 的 traceability_markers 與 trace_source_ids 不一致")
        if argument["source_ids"] and processing_markers:
            raise ValueError(f"{argument_id} 不得混用 source 與 processing_record marker")
        if (
            not argument["source_ids"]
            and argument["checks"]["source_traceable"]
            and len(processing_markers) != 1
        ):
            raise ValueError(f"{argument_id} 待補證 marker 遺漏或重複")

    if source_pairs != marker_pairs or source_pairs != span_pairs:
        mismatched_ids = {
            argument_id
            for argument_id in argument_ids
            if {
                pair for pair in source_pairs if pair[0] == argument_id
            }
            != {pair for pair in marker_pairs if pair[0] == argument_id}
            or {
                pair for pair in source_pairs if pair[0] == argument_id
            }
            != {pair for pair in span_pairs if pair[0] == argument_id}
        }
        passed = [
            argument["argument_id"]
            for argument in arguments
            if argument["argument_id"] in mismatched_ids
            and (argument["binding_status"] == "pass" or argument["binding_ok"])
        ]
        if passed:
            raise ValueError(
                "可追溯性三欄不一致但論點仍標通過: " + ",".join(passed)
            )


def parse_binding_report(data: Any) -> dict[str, Any]:
    """嚴格解析並校驗綁定報告結構；不符則 raise ValueError。

    固定欄位契約：
      - 缺欄／未知欄（欄位漂移）→ ValueError
      - 結構性空欄（如 confidence、source_id 元素）→ ValueError
      - 必要性空欄（functional_gap／user_value／related_knowledge）以 checks 標記，
        binding_ok 為 False（仍可解析，便於驗收指出缺失項）

    測試應以此函式解析報告，而非手寫鬆散 dict 存取。
    """
    if not isinstance(data, dict):
        raise ValueError(f"binding report 必須為 dict，實際: {type(data).__name__}")

    _reject_key_drift(data, REQUIRED_TOP_KEYS, where="binding report")

    if data.get("schema") != SCHEMA_ID:
        raise ValueError(
            f"binding report schema 不符: 期望 {SCHEMA_ID!r}，實際 {data.get('schema')!r}"
        )

    if not isinstance(data.get("argument_count"), int) or data["argument_count"] < 0:
        raise ValueError("argument_count 必須為非負整數")
    if not isinstance(data.get("source_path"), str):
        raise ValueError("source_path 必須為 str")

    summary = data.get("summary")
    _reject_key_drift(summary, REQUIRED_SUMMARY_KEYS, where="summary")

    arguments = data.get("arguments")
    if not isinstance(arguments, list):
        raise ValueError("arguments 必須為 list")
    if len(arguments) != data["argument_count"]:
        raise ValueError(
            f"argument_count={data['argument_count']} 與 arguments 長度 {len(arguments)} 不一致"
        )

    for i, arg in enumerate(arguments):
        if not isinstance(arg, dict):
            raise ValueError(f"arguments[{i}] 必須為 dict")
        _reject_key_drift(arg, REQUIRED_ARGUMENT_KEYS, where=f"arguments[{i}]")
        checks = arg.get("checks")
        _reject_key_drift(checks, REQUIRED_CHECK_KEYS, where=f"arguments[{i}].checks")
        for ck in REQUIRED_CHECK_KEYS:
            if not isinstance(checks[ck], bool):
                raise ValueError(f"arguments[{i}].checks.{ck} 必須為 bool")
        if arg["cardinality"] not in ("one_to_one", "one_to_many", "none"):
            raise ValueError(
                f"arguments[{i}].cardinality 非法: {arg['cardinality']!r}"
            )
        if arg["binding_status"] not in ("pass", "fail", "pending_evidence"):
            raise ValueError(
                f"arguments[{i}].binding_status 非法: {arg['binding_status']!r}"
            )
        if not isinstance(arg["source_ids"], list) or not all(
            isinstance(x, str) for x in arg["source_ids"]
        ):
            raise ValueError(f"arguments[{i}].source_ids 必須為 list[str]")
        if any(not x.strip() for x in arg["source_ids"]):
            raise ValueError(f"arguments[{i}].source_ids 不可含空字串（空欄）")
        if not isinstance(arg["trace_source_ids"], list) or not all(
            isinstance(x, str) for x in arg["trace_source_ids"]
        ):
            raise ValueError(f"arguments[{i}].trace_source_ids 必須為 list[str]")
        if any(not x.strip() for x in arg["trace_source_ids"]):
            raise ValueError(f"arguments[{i}].trace_source_ids 不可含空字串（空欄）")
        source_fragments = arg.get("source_fragments")
        if not isinstance(source_fragments, list):
            raise ValueError(f"arguments[{i}].source_fragments 必須為 list")
        fragment_ids: list[str] = []
        for j, fragment in enumerate(source_fragments):
            where = f"arguments[{i}].source_fragments[{j}]"
            if not isinstance(fragment, dict) or tuple(fragment) != SOURCE_FRAGMENT_KEYS:
                raise ValueError(f"{where} 欄位或序列漂移")
            if not isinstance(fragment["source_id"], str) or not fragment["source_id"].strip():
                raise ValueError(f"{where}.source_id 必須為非空字串")
            if not isinstance(fragment["text"], str):
                raise ValueError(f"{where}.text 必須為 str")
            fragment_ids.append(fragment["source_id"])
        if fragment_ids != arg["source_ids"]:
            raise ValueError(
                f"arguments[{i}].source_fragments 與 source_ids 不一致"
            )

        citation_spans = arg.get("citation_spans")
        if not isinstance(citation_spans, list):
            raise ValueError(f"arguments[{i}].citation_spans 必須為 list")
        for j, span in enumerate(citation_spans):
            if not isinstance(span, dict) or tuple(span) != CITATION_SPAN_KEYS:
                raise ValueError(
                    f"arguments[{i}].citation_spans[{j}] 欄位或序列漂移"
                )
        span_issues = citation_span_issues(
            arg["argument_text"],
            arg["source_ids"],
            citation_spans,
        )
        span_ids = [
            span["source_id"]
            for span in citation_spans
            if isinstance(span, dict) and tuple(span) == CITATION_SPAN_KEYS
        ]
        source_set = set(arg["source_ids"])
        trace_set = set(arg["trace_source_ids"])
        span_set = set(span_ids)
        expected_no_omitted = source_set <= trace_set and source_set <= span_set
        expected_no_extra = trace_set <= source_set and span_set <= source_set
        expected_source_traceable = (
            arg["trace_source_ids"] == arg["source_ids"]
            and not span_issues
            and expected_no_omitted
            and expected_no_extra
        )
        expected_at_least_one = bool(arg["source_ids"])
        expected_no_duplicates = (
            len(arg["source_ids"]) == len(source_set)
            and len(arg["trace_source_ids"]) == len(trace_set)
        )
        if not isinstance(arg.get("source_id_field"), str):
            raise ValueError(f"arguments[{i}].source_id_field 必須為 str")
        expected_source_id = (
            f"sources:{','.join(arg['source_ids'])}"
            if arg["source_ids"]
            else None
        )
        expected_source_id_aligned = (
            arg["source_id_field"] == expected_source_id
            if expected_source_id is not None
            else arg["source_id_field"].startswith("pending:gap:")
        )
        expected_no_empty_fragments = all(
            fragment["text"].strip() for fragment in source_fragments
        )
        for check_name, expected in (
            ("at_least_one_source", expected_at_least_one),
            ("no_duplicate_sources", expected_no_duplicates),
            ("source_id_field_aligned", expected_source_id_aligned),
            ("no_empty_fragments", expected_no_empty_fragments),
        ):
            if checks[check_name] is not expected:
                raise ValueError(
                    f"arguments[{i}].checks.{check_name} 與來源資料不一致"
                )
        if checks["no_omitted_traces"] is not expected_no_omitted:
            raise ValueError(f"arguments[{i}].checks.no_omitted_traces 與追溯資料不一致")
        if checks["no_extra_traces"] is not expected_no_extra:
            raise ValueError(f"arguments[{i}].checks.no_extra_traces 與追溯資料不一致")
        if arg["source_ids"] and checks["source_traceable"] is not expected_source_traceable:
            raise ValueError(f"arguments[{i}].checks.source_traceable 與引用範圍不一致")
        if span_issues and (
            arg["binding_ok"] is not False or arg["binding_status"] == "pass"
        ):
            raise ValueError(
                f"arguments[{i}] 引用範圍不完整但未明確標為 fail: {span_issues}"
            )
        if arg.get("argument_index") != i:
            raise ValueError(
                f"arguments[{i}].argument_index 應為 {i}，實際 {arg.get('argument_index')!r}"
            )
        if not isinstance(arg.get("segment_index"), int) or arg["segment_index"] < 0:
            raise ValueError(f"arguments[{i}].segment_index 必須為非負整數")
        if not isinstance(arg.get("source_count"), int) or arg["source_count"] < 0:
            raise ValueError(f"arguments[{i}].source_count 必須為非負整數")
        if not isinstance(arg.get("binding_ok"), bool):
            raise ValueError(f"arguments[{i}].binding_ok 必須為 bool")
        for sk in _ARGUMENT_NONEMPTY_STR_KEYS:
            val = arg.get(sk)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"arguments[{i}].{sk} 不可為空欄")
        if not isinstance(arg.get("source_id_field"), str):
            raise ValueError(f"arguments[{i}].source_id_field 必須為 str")
        if not isinstance(arg.get("functional_gap"), str):
            raise ValueError(f"arguments[{i}].functional_gap 必須為 str")
        if not isinstance(arg.get("user_value"), str):
            raise ValueError(f"arguments[{i}].user_value 必須為 str")
        if not isinstance(arg.get("related_knowledge"), str):
            raise ValueError(f"arguments[{i}].related_knowledge 必須為 str")
        expected_summary_match = arg["summary"] == arg["argument_text"]
        if checks["summary_matches_product"] is not expected_summary_match:
            raise ValueError(
                f"arguments[{i}].checks.summary_matches_product 與摘要／成品不一致"
            )
        if not expected_summary_match:
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] 摘要未落地到成品但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] 摘要未落地到成品但 binding_status 為 pass"
                )
        angle_tags = arg.get("angle_tags")
        if not isinstance(angle_tags, list) or not angle_tags or not all(
            isinstance(tag, str) and tag.strip() for tag in angle_tags
        ):
            raise ValueError(f"arguments[{i}].angle_tags 必須為非空 list[str]")
        for count_key in ("valid_angle_count", "deduped_angle_count"):
            count = arg.get(count_key)
            if (
                not isinstance(count, int)
                or isinstance(count, bool)
                or count < 0
            ):
                raise ValueError(f"arguments[{i}].{count_key} 必須為非負 int")
        duplicate_angles = arg.get("duplicate_angles")
        if not isinstance(duplicate_angles, list) or not all(
            isinstance(angle, str) and angle.strip() for angle in duplicate_angles
        ):
            raise ValueError(f"arguments[{i}].duplicate_angles 必須為 list[str]")
        angle_field_issues = arg.get("angle_field_issues")
        if not isinstance(angle_field_issues, list) or not all(
            isinstance(issue, str) and issue.strip() for issue in angle_field_issues
        ):
            raise ValueError(
                f"arguments[{i}].angle_field_issues 必須為 list[str]（可為空 list）"
            )
        if angle_field_issues:
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] 有 angle_field_issues 但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] 有 angle_field_issues 但 binding_status 為 pass"
                )
        # 必要性空欄：結構可解析，但必須在 checks 反映，且不得標為通過
        if not arg["functional_gap"].strip():
            if checks.get("has_functional_gap") is not False:
                raise ValueError(
                    f"arguments[{i}] functional_gap 為空欄但 checks.has_functional_gap 未標 False"
                )
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] functional_gap 為空欄但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] functional_gap 為空欄但 binding_status 為 pass"
                )
        if not arg["user_value"].strip():
            if checks.get("has_user_value") is not False:
                raise ValueError(
                    f"arguments[{i}] user_value 為空欄但 checks.has_user_value 未標 False"
                )
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] user_value 為空欄但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] user_value 為空欄但 binding_status 為 pass"
                )
        # 關聯知識：空欄或缺決策品質／使用者理解說明 → checks 必須點名且不得 pass
        rk_ok = related_knowledge_explains_value(arg["related_knowledge"])
        if not rk_ok:
            if checks.get("has_related_knowledge") is not False:
                raise ValueError(
                    f"arguments[{i}] related_knowledge 缺決策品質／使用者理解說明"
                    f"但 checks.has_related_knowledge 未標 False"
                )
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] related_knowledge 不合格但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] related_knowledge 不合格但 binding_status 為 pass"
                )
        elif checks.get("has_related_knowledge") is not True:
            raise ValueError(
                f"arguments[{i}] related_knowledge 合格但 checks.has_related_knowledge 未標 True"
            )

        rk_consistent = related_knowledge_matches_views(
            arg["related_knowledge"],
            functional_gap=arg["functional_gap"],
            user_value=arg["user_value"],
        )
        if checks.get("related_knowledge_consistent") is not rk_consistent:
            raise ValueError(
                f"arguments[{i}].checks.related_knowledge_consistent "
                "與跨欄位一致性量測不一致"
            )
        if not rk_consistent:
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] 關聯知識跨欄位不一致但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] 關聯知識跨欄位不一致但 binding_status 為 pass"
                )

        # 角度覆蓋：固定結構 + 空欄語意
        ac = arg.get("angle_coverage")
        _reject_key_drift(
            ac, REQUIRED_ANGLE_COVERAGE_KEYS, where=f"arguments[{i}].angle_coverage"
        )
        if not isinstance(ac.get("angle_type"), str) or not ac["angle_type"].strip():
            raise ValueError(f"arguments[{i}].angle_coverage.angle_type 不可為空欄")
        if not isinstance(ac.get("angle_labels"), list) or not all(
            isinstance(x, str) and x.strip() for x in ac["angle_labels"]
        ):
            raise ValueError(
                f"arguments[{i}].angle_coverage.angle_labels 必須為非空 list[str]"
            )
        if not ac["angle_labels"]:
            raise ValueError(
                f"arguments[{i}].angle_coverage.angle_labels 不可為空清單"
            )
        if not isinstance(ac.get("covered_facets"), list) or not all(
            isinstance(x, str) and x.strip() for x in ac["covered_facets"]
        ):
            raise ValueError(
                f"arguments[{i}].angle_coverage.covered_facets 必須為非空 list[str]"
            )
        if not ac["covered_facets"]:
            raise ValueError(
                f"arguments[{i}].angle_coverage.covered_facets 不可為空清單"
            )
        if not isinstance(ac.get("angle_key"), str) or not ac["angle_key"].strip():
            raise ValueError(f"arguments[{i}].angle_coverage.angle_key 不可為空欄")
        rel = ac.get("relation")
        _reject_key_drift(
            rel,
            REQUIRED_ANGLE_RELATION_KEYS,
            where=f"arguments[{i}].angle_coverage.relation",
        )
        if rel.get("kind") not in ("unique", "duplicate", "synonym"):
            raise ValueError(
                f"arguments[{i}].angle_coverage.relation.kind 非法: {rel.get('kind')!r}"
            )
        for rk in (
            "related_argument_indices",
            "duplicate_of",
            "synonym_of",
        ):
            rv = rel.get(rk)
            if not isinstance(rv, list) or not all(isinstance(x, int) for x in rv):
                raise ValueError(
                    f"arguments[{i}].angle_coverage.relation.{rk} 必須為 list[int]"
                )
        if ac.get("effective_angle_count") not in (0, 1) or isinstance(
            ac.get("effective_angle_count"), bool
        ):
            raise ValueError(
                f"arguments[{i}].angle_coverage.effective_angle_count 必須為 0 或 1"
            )
        exclusion = ac.get("duplicate_exclusion")
        _reject_key_drift(
            exclusion,
            REQUIRED_DUPLICATE_EXCLUSION_KEYS,
            where=f"arguments[{i}].angle_coverage.duplicate_exclusion",
        )
        if not isinstance(exclusion.get("excluded"), bool):
            raise ValueError(
                f"arguments[{i}].angle_coverage.duplicate_exclusion.excluded 必須為 bool"
            )
        if exclusion.get("reason") not in (None, "duplicate", "synonym"):
            raise ValueError(
                f"arguments[{i}].angle_coverage.duplicate_exclusion.reason 非法"
            )
        kept_index = exclusion.get("kept_argument_index")
        if (
            not isinstance(kept_index, int)
            or isinstance(kept_index, bool)
            or kept_index < 0
            or kept_index >= len(arguments)
        ):
            raise ValueError(
                f"arguments[{i}].angle_coverage.duplicate_exclusion."
                "kept_argument_index 超出範圍"
            )
        complete = is_angle_coverage_complete(
            {
                "angle_type": ac["angle_type"],
                "angle_labels": ac["angle_labels"],
                "covered_facets": ac["covered_facets"],
                "angle_key": ac["angle_key"],
            }
        )
        if not complete:
            if checks.get("has_angle_coverage") is not False:
                raise ValueError(
                    f"arguments[{i}] angle_coverage 不完整但 checks.has_angle_coverage 未標 False"
                )
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] angle_coverage 不完整但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] angle_coverage 不完整但 binding_status 為 pass"
                )
        elif checks.get("has_angle_coverage") is not True:
            raise ValueError(
                f"arguments[{i}] angle_coverage 完整但 checks.has_angle_coverage 未標 True"
            )

        # 角度有效性檢查：每個 argument 必須具備完整四類 facet
        if checks.get("angle_facet_complete") is not True:
            if checks.get("angle_facet_complete") is not False:
                raise ValueError(
                    f"arguments[{i}] angle_facet_complete 應為 bool"
                )
            if arg["binding_ok"] is not False:
                raise ValueError(
                    f"arguments[{i}] angle_facet_complete 為 False 但 binding_ok 未標 False"
                )
            if arg["binding_status"] == "pass":
                raise ValueError(
                    f"arguments[{i}] angle_facet_complete 為 False 但 binding_status 為 pass"
                )
            # angle_facet_complete 為 False 時，至少有一個子檢查應為 False
            sub_checks = [
                checks.get("angle_functional_gap_present", True),
                checks.get("angle_user_value_present", True),
                checks.get("angle_question_present", True),
            ]
            if all(sub_checks):
                raise ValueError(
                    f"arguments[{i}] angle_facet_complete 為 False 但所有子檢查皆為 True，不一致"
                )
        elif checks.get("angle_facet_complete") is not True:
            raise ValueError(
                f"arguments[{i}] angle_facet_complete 為 True 但未正確標記"
            )
        else:
            # angle_facet_complete 為 True 時，所有子檢查必須為 True
            for sub_key in (
                "angle_functional_gap_present",
                "angle_user_value_present",
                "angle_question_present",
            ):
                if checks.get(sub_key) is not True:
                    raise ValueError(
                        f"arguments[{i}] angle_facet_complete 為 True 但 {sub_key} 未標 True"
                    )

    _validate_traceability_fields(data, arguments)

    # 重新量測原始角度欄位，拒絕 relation／排除／有效數被竄改。
    base_coverages = [
        {
            key: arg["angle_coverage"][key]
            for key in ("angle_type", "angle_labels", "covered_facets", "angle_key")
        }
        for arg in arguments
    ]
    expected_coverages = attach_relations(base_coverages)
    for i, (arg, expected) in enumerate(zip(arguments, expected_coverages)):
        actual = arg["angle_coverage"]
        for key in ("relation", "effective_angle_count", "duplicate_exclusion"):
            if actual[key] != expected[key]:
                raise ValueError(
                    f"arguments[{i}].angle_coverage 角度量測不一致: {key}"
                )
        expected_fields = build_argument_angle_fields(
            expected,
            argument_id=arg["argument_id"],
            coverages=expected_coverages,
        )
        for key in REQUIRED_ARGUMENT_ANGLE_KEYS:
            if key == "angle_field_issues":
                continue  # 需搭配 coverage_ok 重算，見下方
            if arg[key] != expected_fields[key]:
                raise ValueError(f"arguments[{i}].{key} 角度量測不一致")

    # 校驗 source_usage 反向索引
    su = data.get("source_usage")
    if not isinstance(su, dict):
        raise ValueError("source_usage 必須為 dict")
    expected_su: dict[str, list[int]] = {}
    for i, a in enumerate(arguments):
        for sid in a.get("source_ids", []):
            expected_su.setdefault(sid, []).append(i)
    expected_su = {k: sorted(v) for k, v in expected_su.items()}
    if su != expected_su:
        raise ValueError(
            f"source_usage 與 arguments 不一致: 期望 {expected_su}，實際 {su}"
        )

    # 角度覆蓋摘要
    acs = data.get("angle_coverage_summary")
    _reject_key_drift(acs, REQUIRED_ANGLE_SUMMARY_KEYS, where="angle_coverage_summary")
    if not isinstance(acs.get("unique_angle_types"), list):
        raise ValueError("angle_coverage_summary.unique_angle_types 必須為 list")
    if not isinstance(acs.get("covered_facets_union"), list):
        raise ValueError("angle_coverage_summary.covered_facets_union 必須為 list")
    if not isinstance(acs.get("duplicate_pairs"), list):
        raise ValueError("angle_coverage_summary.duplicate_pairs 必須為 list")
    if not isinstance(acs.get("synonym_pairs"), list):
        raise ValueError("angle_coverage_summary.synonym_pairs 必須為 list")
    if (
        not isinstance(acs.get("argument_count_with_angles"), int)
        or acs["argument_count_with_angles"] < 0
    ):
        raise ValueError(
            "angle_coverage_summary.argument_count_with_angles 必須為非負整數"
        )
    if acs["argument_count_with_angles"] != data["argument_count"]:
        raise ValueError(
            "angle_coverage_summary.argument_count_with_angles 必須等於 argument_count"
        )
    expected_acs = summarize_angle_coverage(expected_coverages)
    if acs != expected_acs:
        raise ValueError(
            f"angle_coverage_summary 角度覆蓋摘要不一致: "
            f"期望 {expected_acs}，實際 {acs}"
        )
    angle_gate_ok = expected_acs["coverage_ok"]
    for i, arg in enumerate(arguments):
        checks = arg["checks"]
        if checks["meets_angle_coverage_threshold"] is not angle_gate_ok:
            raise ValueError(
                f"arguments[{i}].checks.meets_angle_coverage_threshold "
                "與 angle_coverage_summary.coverage_ok 不一致"
            )
        if not angle_gate_ok and (
            arg["binding_ok"] is not False or arg["binding_status"] != "fail"
        ):
            raise ValueError(
                f"arguments[{i}] 角度覆蓋未達門檻但驗收未明確標為 fail"
            )
        expected_issues = build_angle_field_issues(
            arg["angle_coverage"],
            argument_id=arg["argument_id"],
            angle_gate_ok=angle_gate_ok,
            effective_angle_count=expected_acs["effective_angle_count"],
            required_effective_angle_count=expected_acs[
                "required_effective_angle_count"
            ],
        )
        if arg.get("angle_field_issues") != expected_issues:
            raise ValueError(
                f"arguments[{i}].angle_field_issues 與角度有效性量測不一致: "
                f"期望 {expected_issues}，實際 {arg.get('angle_field_issues')}"
            )
        if expected_issues and (
            arg["binding_ok"] is not False or arg["binding_status"] != "fail"
        ):
            raise ValueError(
                f"arguments[{i}] 角度有效性問題未明確標為 fail: {expected_issues}"
            )
    expected_summary = _summarize_bindings(arguments)
    if summary != expected_summary:
        raise ValueError(
            f"summary 驗收摘要不一致: 期望 {expected_summary}，實際 {summary}"
        )

    return data


def _collect_angle_field_issues(report: dict[str, Any]) -> list[str]:
    """彙總所有論點的缺少／被排除角度欄位問題（保序、去重）。"""
    seen: set[str] = set()
    issues: list[str] = []
    for arg in report.get("arguments") or []:
        for issue in arg.get("angle_field_issues") or []:
            if not isinstance(issue, str) or not issue.strip():
                continue
            if issue in seen:
                continue
            seen.add(issue)
            issues.append(issue)
    return issues


def write_binding_report(output_path: Path, correction) -> Path:
    """寫入報告；摘要或角度驗收未通過時保留報告並明確拒絕。

    失敗訊息必須指出 argument_id 與摘要或角度問題。
    """
    report = build_binding_report(correction)
    # 校驗後再落盤，保證產物可被 parse_binding_report 直接吃
    parse_binding_report(report)
    dest_dir = output_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    report_path = dest_dir / BINDING_REPORT_NAME
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    summary_issues = [
        f"{arg['argument_id']}.summary 與成品正文不一致"
        for arg in report["arguments"]
        if not arg["checks"]["summary_matches_product"]
    ]
    if summary_issues:
        raise RuntimeError(f"摘要一致性驗收失敗：{'；'.join(summary_issues)}")
    traceability_issues = [
        f"{arg['argument_id']}.來源、追溯標記與 citation_spans 不一致"
        for arg in report["arguments"]
        if arg["source_count"] and not arg["checks"]["source_traceable"]
    ]
    if traceability_issues:
        raise RuntimeError(
            f"引用範圍追溯驗收失敗：{'；'.join(traceability_issues)}"
        )
    related_issues = [
        f"{arg['argument_id']}.related_knowledge 缺決策品質／使用者理解說明"
        for arg in report["arguments"]
        if not arg["checks"].get("has_related_knowledge", False)
    ]
    if related_issues:
        raise RuntimeError(f"關聯知識驗收失敗：{'；'.join(related_issues)}")
    angle_summary = report["angle_coverage_summary"]
    field_issues = _collect_angle_field_issues(report)
    facet_incomplete = any(
        not (arg.get("checks") or {}).get("angle_facet_complete", True)
        for arg in report.get("arguments") or []
    )
    if not angle_summary["coverage_ok"] or field_issues or facet_incomplete:
        detail = "；".join(field_issues) if field_issues else (
            f"有效角度 {angle_summary['effective_angle_count']}/"
            f"最低 {angle_summary['required_effective_angle_count']}；"
            f"重複率 {angle_summary['duplicate_ratio']:.3f}/"
            f"上限 {angle_summary['max_duplicate_ratio']:.3f}"
        )
        raise RuntimeError(f"角度有效性驗收失敗：{detail}")
    consistency_issues = [
        f"{arg['argument_id']}.related_knowledge 未對應 functional_gap／user_value"
        for arg in report["arguments"]
        if not arg["checks"]["related_knowledge_consistent"]
    ]
    if consistency_issues:
        raise RuntimeError(
            f"跨欄位一致性驗收失敗：{'；'.join(consistency_issues)}"
        )
    return report_path
