"""可機器比對的論點—來源綁定報告。

產出固定 schema 的 JSON 結構，讓測試／下游可直接解析並逐項驗證每個論點：
  1. 至少一個來源（at_least_one_source）
  2. 來源可追溯（source_traceable：sources ↔ traceability 對齊）
  3. 無重複遺漏（no_duplicate_sources + no_omitted_traces + no_extra_traces）

明確標示 cardinality：
  - one_to_one：剛好一個來源
  - one_to_many：兩個以上來源
  - none：無來源（通常 pending_evidence）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

SCHEMA_ID = "note_filler.binding_report.v1"
BINDING_REPORT_NAME = "binding_report.json"

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
    }
)
REQUIRED_ARGUMENT_KEYS = frozenset(
    {
        "argument_index",
        "segment_index",
        "argument_text",
        "confidence",
        "cardinality",
        "source_count",
        "source_ids",
        "trace_source_ids",
        "source_id_field",
        "checks",
        "binding_status",
        "binding_ok",
    }
)
REQUIRED_CHECK_KEYS = frozenset(
    {
        "at_least_one_source",
        "source_traceable",
        "no_duplicate_sources",
        "no_omitted_traces",
        "no_extra_traces",
        "source_id_field_aligned",
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


def _source_ids(seg) -> list[str]:
    ids: list[str] = []
    for src in getattr(seg, "sources", None) or []:
        sid = getattr(src, "id", None)
        if isinstance(sid, str) and sid.strip():
            ids.append(sid)
    return ids


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


def _cardinality(source_count: int) -> Cardinality:
    if source_count <= 0:
        return "none"
    if source_count == 1:
        return "one_to_one"
    return "one_to_many"


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
    sid_field = getattr(seg, "source_id", None) or ""
    confidence = getattr(seg, "confidence", None) or ""
    text = getattr(seg, "text", None) or ""
    cardinality = _cardinality(len(source_ids))

    no_dup = len(source_ids) == len(set(source_ids))
    # 追溯側亦不得重複
    no_dup_trace = len(trace_ids) == len(set(trace_ids))
    no_duplicate_sources = no_dup and no_dup_trace

    source_set = set(source_ids)
    trace_set = set(trace_ids)
    no_omitted = source_set <= trace_set  # 每個 source 都有 trace
    no_extra = trace_set <= source_set  # 無多餘 trace

    if source_ids:
        expected_field = f"sources:{','.join(source_ids)}"
        source_id_aligned = sid_field == expected_field
        at_least_one = True
        # 可追溯：trace 與 sources 順序與集合皆對齊
        source_traceable = trace_ids == source_ids and no_omitted and no_extra
    else:
        expected_field_ok = isinstance(sid_field, str) and sid_field.startswith(
            "pending:gap:"
        )
        source_id_aligned = expected_field_ok
        at_least_one = False
        source_traceable = _pending_traceable(seg)
        # 無來源時「無遺漏／無多餘」對空集合為真
        no_omitted = True
        no_extra = True

    checks = {
        "at_least_one_source": at_least_one,
        "source_traceable": source_traceable,
        "no_duplicate_sources": no_duplicate_sources,
        "no_omitted_traces": no_omitted,
        "no_extra_traces": no_extra,
        "source_id_field_aligned": source_id_aligned,
    }

    # 有來源：三項核心 + 對齊皆須通過
    if source_ids:
        binding_ok = all(
            (
                checks["at_least_one_source"],
                checks["source_traceable"],
                checks["no_duplicate_sources"],
                checks["no_omitted_traces"],
                checks["no_extra_traces"],
                checks["source_id_field_aligned"],
            )
        )
        status: BindingStatus = "pass" if binding_ok else "fail"
    else:
        # 無來源：必須為 pending 且 processing_record 可追溯
        intentional_pending = confidence == "pending_evidence" and source_traceable and source_id_aligned
        binding_ok = intentional_pending
        status = "pending_evidence" if intentional_pending else "fail"

    return {
        "argument_index": argument_index,
        "segment_index": segment_index,
        "argument_text": text,
        "confidence": confidence,
        "cardinality": cardinality,
        "source_count": len(source_ids),
        "source_ids": list(source_ids),
        "trace_source_ids": list(trace_ids),
        "source_id_field": sid_field,
        "checks": checks,
        "binding_status": status,
        "binding_ok": binding_ok,
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

    one_to_one = sum(1 for a in arguments if a["cardinality"] == "one_to_one")
    one_to_many = sum(1 for a in arguments if a["cardinality"] == "one_to_many")
    none_n = sum(1 for a in arguments if a["cardinality"] == "none")
    pass_n = sum(1 for a in arguments if a["binding_status"] == "pass")
    fail_n = sum(1 for a in arguments if a["binding_status"] == "fail")
    pending_n = sum(1 for a in arguments if a["binding_status"] == "pending_evidence")

    sourced = [a for a in arguments if a["cardinality"] != "none"]
    all_sourced_ok = all(a["binding_ok"] for a in sourced) if sourced else True
    all_ok = all(a["binding_ok"] for a in arguments) if arguments else True

    return {
        "schema": SCHEMA_ID,
        "source_path": source_path,
        "argument_count": len(arguments),
        "summary": {
            "one_to_one": one_to_one,
            "one_to_many": one_to_many,
            "none": none_n,
            "pass": pass_n,
            "fail": fail_n,
            "pending_evidence": pending_n,
            "all_sourced_arguments_ok": all_sourced_ok,
            "all_arguments_ok": all_ok,
        },
        "arguments": arguments,
    }


def parse_binding_report(data: Any) -> dict[str, Any]:
    """嚴格解析並校驗綁定報告結構；不符則 raise ValueError。

    測試應以此函式解析報告，而非手寫鬆散 dict 存取。
    """
    if not isinstance(data, dict):
        raise ValueError(f"binding report 必須為 dict，實際: {type(data).__name__}")

    missing = REQUIRED_TOP_KEYS - data.keys()
    if missing:
        raise ValueError(f"binding report 缺少頂層欄位: {sorted(missing)}")

    if data.get("schema") != SCHEMA_ID:
        raise ValueError(
            f"binding report schema 不符: 期望 {SCHEMA_ID!r}，實際 {data.get('schema')!r}"
        )

    if not isinstance(data.get("argument_count"), int) or data["argument_count"] < 0:
        raise ValueError("argument_count 必須為非負整數")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("summary 必須為 dict")
    smissing = REQUIRED_SUMMARY_KEYS - summary.keys()
    if smissing:
        raise ValueError(f"summary 缺少欄位: {sorted(smissing)}")

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
        amissing = REQUIRED_ARGUMENT_KEYS - arg.keys()
        if amissing:
            raise ValueError(f"arguments[{i}] 缺少欄位: {sorted(amissing)}")
        checks = arg.get("checks")
        if not isinstance(checks, dict):
            raise ValueError(f"arguments[{i}].checks 必須為 dict")
        cmissing = REQUIRED_CHECK_KEYS - checks.keys()
        if cmissing:
            raise ValueError(f"arguments[{i}].checks 缺少欄位: {sorted(cmissing)}")
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
        if not isinstance(arg["trace_source_ids"], list) or not all(
            isinstance(x, str) for x in arg["trace_source_ids"]
        ):
            raise ValueError(f"arguments[{i}].trace_source_ids 必須為 list[str]")
        if arg.get("argument_index") != i:
            raise ValueError(
                f"arguments[{i}].argument_index 應為 {i}，實際 {arg.get('argument_index')!r}"
            )

    return data


def write_binding_report(output_path: Path, correction) -> Path:
    """將綁定報告寫到輸出檔同目錄的 binding_report.json。"""
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
    return report_path
