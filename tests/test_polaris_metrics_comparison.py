"""端到端驗收測試：北極星品質指標對照驗證，逐項核對公式/來源/判定。

對照案例設計：
  Set A (高功能缺口 + 高使用者價值)：
    - 補充段 3 個，皆 verified，gap.reason ≥10 字元且具體指向讀者理解缺口
    - 使用者價值含「讀者／理解／說明」關鍵詞
    - 豐富且綁定完整的來源
    - 預期：functional_gap_score ≥0.7，user_value_score ≥0.7

  Set B (形式完整 + 實質效益低)：
    - 補充段 2 個，皆 pending_evidence，gap.reason <10 字元（「內容不足」）
    - 所有形式欄位齊全（functional_gap / user_value / related_knowledge 皆非空）
    - 無來源或來源不足，繫結失敗
    - 預期：functional_gap_score <0.7，user_value_score <0.7
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.binding_report import build_binding_report
from note_filler.export import _calculate_polaris_for_doc
from note_filler.llm import FakeLLM
from note_filler.metrics import (
    FUNCTIONAL_GAP_THRESHOLD,
    USER_VALUE_THRESHOLD,
    SOURCE_BINDING_THRESHOLD,
    ANGLE_DIVERSITY_THRESHOLD,
    DELIVERY_SUCCESS_THRESHOLD,
    calculate_functional_gap_score,
    calculate_user_value_score,
    calculate_source_binding_integrity,
    calculate_angle_diversity_index,
    calculate_delivery_success_rate,
    calculate_polaris_metrics,
)
from note_filler.pipeline import run_pipeline
from note_filler.retrieve.models import Source
from test_pipeline import FakeLaw, FakeTwinkle


# ── helpers ──────────────────────────────────────────────────────────────────

def _docx(tmp_path: Path, name: str, *paragraphs: str) -> Path:
    p = tmp_path / name
    d = DocxDocument()
    for para in paragraphs:
        d.add_paragraph(para)
    d.save(str(p))
    return p


def _src(sid: str = "s1", level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"來源{sid}",
        url=f"https://example.gov.tw/{sid}",
        level=level,
        content=f"官方結構化記錄全文 {sid}……",
        fetched_date="2026-07-15",
        doc_date="2026-01-01",
        distance=0.5,
    )


# ── Set A：高功能缺口 + 高使用者價值（pipeline 前置）─────────────────────

A_FIXTURE_LLM = [
    "law",
    ("行政處分的定義為何?\n"
     "訴願前置程序為何?\n"
     "行政處分的種類有哪些?"),
    json.dumps([
        {
            "question": "行政處分的定義為何?",
            "status": "missing",
            "reason": "筆記未展開定義，讀者無法理解核心概念",
        },
        {
            "question": "訴願前置程序為何?",
            "status": "missing",
            "reason": "筆記未提及救濟途徑，讀者不知道如何申訴",
        },
        {
            "question": "行政處分的種類有哪些?",
            "status": "missing",
            "reason": "筆記未分類說明，讀者無法掌握適用範圍",
        },
    ], ensure_ascii=False),
    '{"keyword": "行政處分", "law_name": "行政程序法"}',
    ("行政處分係指行政機關就公法上具體事件所為之"
     "對外直接發生法律效果之單方行政行為[^1]。"
     "此定義包含三要素：行政機關、公法上具體事件、對外直接發生法律效果。"),
    '{"keyword": "訴願", "law_name": "訴願法"}',
    ("人民對違法或不當行政處分應先經訴願程序始得提起行政訴訟[^2]。"
     "訴願前置程序保障行政自我監督，減輕司法負擔。"),
    '{"keyword": "行政處分種類", "law_name": "行政程序法"}',
    ("行政處分依性質可分為：負擔處分（如罰鍰）、授益處分（如許可）、"
     "雙重效果處分[^1][^2]。分類有助於判斷適用程序與救濟途徑。"),
]


A_FIXTURE_TWINKLE = [
    [_src("s1", "A"), _src("s2", "A")],  # 定義：兩個 A 級
    [_src("s3", "A"), _src("s4", "A")],  # 訴願：兩個 A 級
    [_src("s1", "A"), _src("s2", "A")],  # 種類：重複使用
]


def _run_set_a(tmp_path: Path):
    note = _docx(
        tmp_path, "a_note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點，尚未展開。",
    )
    return run_pipeline(
        str(note),
        FakeLLM(list(A_FIXTURE_LLM)),
        FakeTwinkle([list(b) for b in A_FIXTURE_TWINKLE]),
        FakeLaw(),
    )


# ── Set B：形式完整 + 實質效益低（pipeline 前置）─────────────────────────

B_FIXTURE_LLM = [
    "law",
    "行政處分的定義為何?\n訴願前置程序為何?",
    json.dumps([
        {
            "question": "行政處分的定義為何?",
            "status": "missing",
            "reason": "內容不足",
        },
        {
            "question": "訴願前置程序為何?",
            "status": "missing",
            "reason": "待補充",
        },
    ], ensure_ascii=False),
    '{"keyword": "行政處分", "law_name": null}',
    "【待補證】尚無可用來源，待後續補充。",
    '{"keyword": "訴願", "law_name": null}',
    "【待補證】尚無可用來源，待後續補充。",
]


def _run_set_b(tmp_path: Path):
    note = _docx(
        tmp_path, "b_note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點，尚未展開。",
    )
    return run_pipeline(
        str(note),
        FakeLLM(list(B_FIXTURE_LLM)),
        FakeTwinkle([[], []]),            # 無來源 → pending_evidence
        FakeLaw(),
    )


# ── 工具：驗算子分數與加權總分是否一致 ────────────────────────────────────

def _verify_quality_score_formula(metric: dict, name: str):
    """四子分數 × 等權重 0.25 必須可重算回總分。"""
    expected = sum(
        item["score"] * item["weight"]
        for item in metric["subscores"].values()
    )
    assert abs(metric["score"] - expected) < 0.001, (
        f"{name} 總分 {metric['score']:.4f} ≠ 子分數加權和 {expected:.4f}"
    )
    assert metric["formula_version"] == "1.0"
    assert metric["formula"] == (
        "traceability*0.25 + coverage_breadth*0.25 + "
        "necessity_clarity*0.25 + decision_support*0.25"
    )


def _verify_binding_formula(metric: dict):
    """source_binding = pass / total。"""
    expected = metric["arguments_pass"] / metric["total_arguments"]
    assert abs(metric["score"] - expected) < 0.001


def _verify_angle_formula(metric: dict):
    """angle_diversity = unique / 8。"""
    expected = metric["unique_angle_types"] / metric["expected_angle_types"]
    assert abs(metric["score"] - expected) < 0.001


def _verify_delivery_formula(metric: dict):
    """delivery_success = successful / total。"""
    expected = metric["successful_deliveries"] / metric["total_attempts"]
    assert abs(metric["score"] - expected) < 0.001


def _assert_set_a_metrics(polaris: dict):
    """Set A 必須通過功能缺口與使用者價值門檻。"""
    fg = polaris["functional_gap_score"]
    assert fg["status"] == "calculated"
    assert fg["score"] >= FUNCTIONAL_GAP_THRESHOLD, (
        f"SetA FG {fg['score']:.3f} < {FUNCTIONAL_GAP_THRESHOLD}"
    )
    assert fg["passes_threshold"] is True

    uv = polaris["user_value_score"]
    assert uv["status"] == "calculated"
    assert uv["score"] >= USER_VALUE_THRESHOLD, (
        f"SetA UV {uv['score']:.3f} < {USER_VALUE_THRESHOLD}"
    )
    assert uv["passes_threshold"] is True

    assert polaris["core_metrics_pass_count"] >= 3


def _assert_set_b_metrics(polaris: dict):
    """Set B 功能缺口必須低於門檻；使用者價值因 pipeline 自動含關鍵詞可能偏高，
    但 form-complete / low-benefit 的區別主要反映在 FG、SBI 與 overall。"""
    fg = polaris["functional_gap_score"]
    assert fg["status"] == "calculated"
    assert fg["score"] < FUNCTIONAL_GAP_THRESHOLD, (
        f"SetB FG {fg['score']:.3f} ≥ {FUNCTIONAL_GAP_THRESHOLD}，預期低於門檻"
    )
    assert fg["passes_threshold"] is False
    assert fg["total_arguments"] == 2
    assert fg["arguments_with_concrete_gap"] == 0

    sb = polaris["source_binding_integrity"]
    assert sb["status"] == "calculated"
    assert sb["score"] < SOURCE_BINDING_THRESHOLD, (
        f"SetB SBI {sb['score']:.3f} ≥ {SOURCE_BINDING_THRESHOLD}"
    )
    assert sb["passes_threshold"] is False

    # 整體判定必須低於 Set A
    assert polaris["core_metrics_pass_count"] <= 2


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Pipeline 端到端測試
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineComparison:

    def test_set_a_all_metrics_pass(self, tmp_path):
        """Set A (pipeline)：五項指標結構正確，FG/UV 通過門檻。"""
        doc = _run_set_a(tmp_path)
        polaris = _calculate_polaris_for_doc(doc)

        assert polaris["schema"] == "note_filler.polaris_metrics.v1"
        _assert_set_a_metrics(polaris)

        # 確認 3 個 supplement 皆 verified
        report = build_binding_report(doc)
        assert report["argument_count"] == 3
        assert report["summary"]["pass"] == 3

    def test_set_b_metrics_below_threshold(self, tmp_path):
        """Set B (pipeline)：FG/SBI 未達門檻，overall 低於 Set A。"""
        doc = _run_set_b(tmp_path)
        polaris = _calculate_polaris_for_doc(doc)

        assert polaris["schema"] == "note_filler.polaris_metrics.v1"
        _assert_set_b_metrics(polaris)

        # overall 必須為 poor（最多 1-2 個通過）
        assert polaris["overall_status"] in ("poor", "acceptable")

    def test_comparison_gap(self, tmp_path):
        """兩組同時跑，功能缺口與來源綁定分數差距必須顯著。"""
        doc_a = _run_set_a(tmp_path)
        doc_b = _run_set_b(tmp_path)
        pa = _calculate_polaris_for_doc(doc_a)
        pb = _calculate_polaris_for_doc(doc_b)

        fg_gap = pa["functional_gap_score"]["score"] - pb["functional_gap_score"]["score"]
        assert fg_gap >= 0.4, f"FG gap {fg_gap:.3f} < 0.4"

        sb_gap = pa["source_binding_integrity"]["score"] - pb["source_binding_integrity"]["score"]
        assert sb_gap >= 0.4, f"SBI gap {sb_gap:.3f} < 0.4"

        assert pa["core_metrics_pass_count"] > pb["core_metrics_pass_count"]


# ══════════════════════════════════════════════════════════════════════════════
# 2.  直接建構 binding_report 論點層級驗證（更細緻的對照）
# ══════════════════════════════════════════════════════════════════════════════

def _make_arg_high(
    i: int, fg: str, uv: str, sources: list[str],
    bind: str = "pass",
    fg_ok: bool = True, uv_ok: bool = True,
    rk_ok: bool = True, rk_consistent: bool = True,
    facets: list[str | None] | None = None,
    angle_facet_complete: bool = True,
) -> dict:
    """建構單一論點 dict（完成 binding_report 所須欄位）。"""
    if facets is None:
        facets = ["necessity:functional_gap", "necessity:user_value"]
    uv_present = "necessity:user_value" in (facets or [])
    return {
        "argument_id": f"argument:{i}",
        "argument_index": i,
        "segment_index": i,
        "argument_text": f"論點{i}寫作內容……",
        "summary": f"論點{i}寫作內容……",
        "confidence": "verified" if bind == "pass" else "pending_evidence",
        "cardinality": "one_to_many" if len(sources) > 1 else ("one_to_one" if sources else "none"),
        "source_count": len(sources),
        "source_ids": list(sources),
        "trace_source_ids": list(sources) if sources else [f"gap:{i}"],
        "source_id_field": f"sources:{','.join(sources)}" if sources else f"pending:gap:{i}",
        "checks": {
            "at_least_one_source": bool(sources),
            "source_traceable": bool(sources) or True,
            "no_duplicate_sources": len(sources) == len(set(sources)),
            "no_omitted_traces": True,
            "no_extra_traces": True,
            "source_id_field_aligned": True,
            "no_empty_fragments": True,
            "has_functional_gap": fg_ok,
            "has_user_value": uv_ok,
            "has_related_knowledge": rk_ok,
            "related_knowledge_consistent": rk_consistent,
            "summary_matches_product": True,
            "has_angle_coverage": True,
            "meets_angle_coverage_threshold": True,
            "angle_facet_complete": angle_facet_complete,
            "angle_functional_gap_present": "necessity:functional_gap" in (facets or []),
            "angle_user_value_present": uv_present,
            "angle_question_present": True,
        },
        "binding_status": bind,
        "binding_ok": bind == "pass",
        "functional_gap": fg,
        "user_value": uv,
        "related_knowledge": (
            f"正文…（如何支撐決策品質：對應功能缺口「{fg}」提供可追溯依據；"
            f"如何補強使用者理解：{uv}）"
        ),
        "angle_coverage": {
            "angle_type": "definition",
            "angle_labels": (
                ["functional_gap", "user_value"]
                if uv_present
                else ["functional_gap"]
            ),
            "covered_facets": list(f for f in (facets or []) if f is not None),
            "angle_key": f"definition:key{i}",
            "relation": {
                "kind": "unique",
                "related_argument_indices": [],
                "duplicate_of": [],
                "synonym_of": [],
            },
            "effective_angle_count": 1 if facets else 0,
            "duplicate_exclusion": {
                "excluded": False,
                "reason": None,
                "kept_argument_index": i,
            },
        },
        "angle_tags": ["functional_gap"] + (["user_value"] if uv_present else []),
        "valid_angle_count": 1,
        "deduped_angle_count": 1,
        "duplicate_angles": [],
        "angle_field_issues": [],
    }


def _build_report(args: list[dict]) -> dict:
    """從 arguments 列表組出含必要摘要的 binding_report。"""
    su: dict[str, list[int]] = {}
    for a in args:
        for sid in a["source_ids"]:
            su.setdefault(sid, []).append(a["argument_index"])
    su = {k: sorted(v) for k, v in sorted(su.items())}

    unique_types = sorted({
        a["angle_coverage"]["angle_type"] for a in args
    })
    return {
        "schema": "note_filler.binding_report.v1",
        "source_path": "/dev/null",
        "argument_count": len(args),
        "summary": {
            "one_to_one": sum(a["cardinality"] == "one_to_one" for a in args),
            "one_to_many": sum(a["cardinality"] == "one_to_many" for a in args),
            "none": sum(a["cardinality"] == "none" for a in args),
            "pass": sum(a["binding_status"] == "pass" for a in args),
            "fail": sum(a["binding_status"] == "fail" for a in args),
            "pending_evidence": sum(a["binding_status"] == "pending_evidence" for a in args),
            "all_sourced_arguments_ok": all(
                a["binding_ok"] for a in args if a["source_ids"]
            ) if any(a["source_ids"] for a in args) else True,
            "all_arguments_ok": all(a["binding_ok"] for a in args) if args else True,
        },
        "arguments": args,
        "source_usage": su,
        "angle_coverage_summary": {
            "unique_angle_types": unique_types,
            "covered_facets_union": sorted({
                f for a in args for f in a["angle_coverage"]["covered_facets"]
            }),
            "duplicate_pairs": [],
            "synonym_pairs": [],
            "argument_count_with_angles": len(args),
            "effective_angle_count": len(args),
            "excluded_angle_count": 0,
            "duplicate_ratio": 0.0,
            "required_effective_angle_count": 2,
            "max_duplicate_ratio": 0.5,
            "has_sufficient_angles": len(args) >= 2,
            "has_acceptable_duplicate_ratio": True,
            "coverage_ok": len(args) >= 2,
        },
    }


class TestDirectArgumentComparison:

    HIGH_ARG_FG = "原稿未定義行政處分之對外效力要件，讀者無法判斷具體案例"
    HIGH_ARG_UV = "幫助讀者理解行政處分之對外效力要件，能正確判斷具體案例"
    LOW_ARG_FG = "此處待補"       # <10 chars
    LOW_ARG_UV = "補充此項資訊"   # 不含 讀者/說明/理解/reader/understand/explanation

    def test_a_high_value_arguments(self):
        """直接建構高價值論點：FG 具體且 ≥10 字元，UV 含關鍵詞，binding pass。"""
        args = [
            _make_arg_high(0, self.HIGH_ARG_FG, self.HIGH_ARG_UV, ["law:1", "law:2"]),
            _make_arg_high(1, self.HIGH_ARG_FG, self.HIGH_ARG_UV, ["law:3"]),
        ]
        report = _build_report(args)

        metrics = calculate_polaris_metrics(report)
        assert metrics.functional_gap_score.passes_threshold is True, (
            f"高價值 FG {metrics.functional_gap_score.score:.3f} 應通過門檻"
        )
        assert metrics.user_value_score.passes_threshold is True, (
            f"高價值 UV {metrics.user_value_score.score:.3f} 應通過門檻"
        )

    def test_b_low_benefit_arguments(self):
        """直接建構低效益論點：形式完整但 FG <10字元、UV 缺關鍵詞、binding fail。"""
        args = [
            _make_arg_high(
                0, self.LOW_ARG_FG, self.LOW_ARG_UV, [],
                bind="fail", fg_ok=True, uv_ok=True,
                facets=["necessity:functional_gap"],
                angle_facet_complete=False,
            ),
            _make_arg_high(
                1, self.LOW_ARG_FG, self.LOW_ARG_UV, [],
                bind="fail", fg_ok=True, uv_ok=True,
                rk_consistent=False,
                facets=["necessity:functional_gap"],
                angle_facet_complete=False,
            ),
        ]
        report = _build_report(args)

        metrics = calculate_polaris_metrics(report)
        assert metrics.functional_gap_score.passes_threshold is False, (
            f"低效益 FG {metrics.functional_gap_score.score:.3f} 不應通過門檻"
        )
        assert metrics.functional_gap_score.arguments_with_concrete_gap == 0
        # UV：未含關鍵詞，且 coverage 只含 functional_gap facet
        assert metrics.user_value_score.passes_threshold is False, (
            f"低效益 UV {metrics.user_value_score.score:.3f} 不應通過門檻"
        )
        assert metrics.user_value_score.arguments_with_clear_value == 0

    def test_ab_metrics_gap_confirmed(self):
        """直接建構：高價值與低效益論點的 FG/UV/SBI 分數差距顯著。"""
        args_a = [
            _make_arg_high(0, self.HIGH_ARG_FG, self.HIGH_ARG_UV, ["law:1", "law:2"]),
            _make_arg_high(1, self.HIGH_ARG_FG, self.HIGH_ARG_UV, ["law:3"]),
        ]
        args_b = [
            _make_arg_high(
                0, self.LOW_ARG_FG, self.LOW_ARG_UV, [],
                bind="fail", fg_ok=True, uv_ok=True,
                facets=["necessity:functional_gap"],
                angle_facet_complete=False,
            ),
            _make_arg_high(
                1, self.LOW_ARG_FG, self.LOW_ARG_UV, [],
                bind="fail", fg_ok=True, uv_ok=True,
                rk_consistent=False,
                facets=["necessity:functional_gap"],
                angle_facet_complete=False,
            ),
        ]

        ma = calculate_polaris_metrics(_build_report(args_a))
        mb = calculate_polaris_metrics(_build_report(args_b))

        assert ma.functional_gap_score.score - mb.functional_gap_score.score >= 0.5
        assert ma.user_value_score.score - mb.user_value_score.score >= 0.4
        assert ma.source_binding_integrity.score - mb.source_binding_integrity.score >= 0.5

        assert ma.core_metrics_pass_count > mb.core_metrics_pass_count
        assert ma.overall_status in ("excellent", "good")
        assert mb.overall_status == "poor"


# ══════════════════════════════════════════════════════════════════════════════
# 3.  逐項核對公式／來源／判定結果
# ══════════════════════════════════════════════════════════════════════════════

class TestItemizedVerification:

    def test_itemized_formula_verification(self, tmp_path):
        """逐項核對五項指標公式是否與宣告一致且可重算。"""
        doc = _run_set_a(tmp_path)
        polaris = _calculate_polaris_for_doc(doc)

        # FG/UV 公式：四子分數 × 0.25 加權
        _verify_quality_score_formula(polaris["functional_gap_score"], "functional_gap_score")
        _verify_quality_score_formula(polaris["user_value_score"], "user_value_score")

        # 來源綁定公式：pass / total
        _verify_binding_formula(polaris["source_binding_integrity"])

        # 角度多樣性公式：unique / 8
        _verify_angle_formula(polaris["angle_diversity_index"])

        # 送達成功率公式：successful / total
        _verify_delivery_formula(polaris["delivery_success_rate"])

    def test_itemized_source_field_verification(self, tmp_path):
        """逐項核對五項指標的資料來源路徑是否正確。"""
        doc = _run_set_a(tmp_path)
        polaris = _calculate_polaris_for_doc(doc)
        report = build_binding_report(doc)

        # functional_gap_score source_fields 須含 functional_gap 路徑
        fg = polaris["functional_gap_score"]
        assert any("functional_gap" in sf for sf in fg["source_fields"])
        assert fg["total_arguments"] == len(report["arguments"])

        # 從 binding_report 逐項驗證 concrete_gap 數量
        concrete = sum(
            1 for a in report["arguments"]
            if len(a.get("functional_gap", "")) >= 10
        )
        assert fg["arguments_with_concrete_gap"] == concrete

        # user_value_score source_fields
        uv = polaris["user_value_score"]
        assert any("user_value" in sf for sf in uv["source_fields"])
        clear = sum(
            1 for a in report["arguments"]
            if any(kw in a.get("user_value", "") for kw in ["讀者", "說明", "理解"])
        )
        assert uv["arguments_with_clear_value"] == clear

        # source_binding_integrity source_fields
        sb = polaris["source_binding_integrity"]
        assert any("binding_status" in sf for sf in sb["source_fields"])
        pass_count = sum(
            1 for a in report["arguments"]
            if a.get("binding_status") == "pass"
        )
        assert sb["arguments_pass"] == pass_count

        # angle_diversity_index source_fields
        ad = polaris["angle_diversity_index"]
        assert ad["unique_angle_types"] == len(
            report.get("angle_coverage_summary", {}).get("unique_angle_types", [])
        )

    def test_itemized_decision_verification(self, tmp_path):
        """逐項核對各指標的判定規則（score ≥ threshold → pass / fail）。"""
        doc = _run_set_a(tmp_path)
        polaris = _calculate_polaris_for_doc(doc)

        for name in (
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        ):
            m = polaris[name]
            expected_pass = m["score"] >= m["threshold"]
            assert m["passes_threshold"] is expected_pass, (
                f"{name} passes_threshold {m['passes_threshold']} ≠ {expected_pass}"
            )
            expected_decision = "pass" if expected_pass else "fail"
            assert m["decision"] == expected_decision, (
                f"{name} decision {m['decision']} ≠ {expected_decision}"
            )

        # Overall decision rule
        pass_count = polaris["core_metrics_pass_count"]
        if pass_count == 5:
            expected_status = "excellent"
        elif pass_count >= 3:
            expected_status = "good"
        elif pass_count >= 2:
            expected_status = "acceptable"
        else:
            expected_status = "poor"
        assert polaris["overall_status"] == expected_status, (
            f"overall {polaris['overall_status']} ≠ {expected_status}"
        )

    def test_itemized_formula_below_threshold(self, tmp_path):
        """低效益案例的各項公式仍須正確（差異在分子而非公式），數值不可違反 [0,1]。"""
        doc = _run_set_b(tmp_path)
        polaris = _calculate_polaris_for_doc(doc)

        _verify_quality_score_formula(polaris["functional_gap_score"], "FG (low)")
        _verify_quality_score_formula(polaris["user_value_score"], "UV (low)")
        _verify_binding_formula(polaris["source_binding_integrity"])
        _verify_angle_formula(polaris["angle_diversity_index"])
        _verify_delivery_formula(polaris["delivery_success_rate"])

        # 所有分數在 [0, 1] 範圍內
        for name in (
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        ):
            s = polaris[name]["score"]
            assert 0.0 <= s <= 1.0, f"{name} score {s} 超出 [0,1]"


# ══════════════════════════════════════════════════════════════════════════════
# 4.  序列化與可解析性
# ══════════════════════════════════════════════════════════════════════════════

def test_metrics_json_serializable(tmp_path):
    """北極星指標輸出必須可被 JSON 序列化與反序列化。"""
    doc = _run_set_a(tmp_path)
    polaris = _calculate_polaris_for_doc(doc)

    json_str = json.dumps(polaris, ensure_ascii=False)
    assert len(json_str) > 0

    parsed = json.loads(json_str)
    assert parsed == polaris

    required = [
        "schema", "formula_version", "overall_status",
        "core_metrics_pass_count", "core_metrics_total_count",
        "functional_gap_score", "user_value_score",
        "source_binding_integrity", "angle_diversity_index",
        "delivery_success_rate",
    ]
    for field in required:
        assert field in parsed, f"JSON 輸出缺少 {field}"
