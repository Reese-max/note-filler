"""角度覆蓋單元測試：分類、facet、重複／同義判定（不依賴外部服務）。"""
from __future__ import annotations

from note_filler.angle_coverage import (
    attach_relations,
    build_angle_coverage,
    build_angle_key,
    classify_angle_type,
    detect_angle_relation,
    is_angle_coverage_complete,
    normalize_angle_text,
    summarize_angle_coverage,
)


def test_classify_angle_type_keywords():
    assert classify_angle_type("行政處分如何定義？") == "definition"
    assert classify_angle_type("附款有何限制？") == "limitation"
    assert classify_angle_type("構成要件為何？") == "requirement"
    assert classify_angle_type("法律效果為何？") == "effect"
    assert classify_angle_type("申請程序如何？") == "procedure"
    assert classify_angle_type("有無例外規定？") == "exception"
    assert classify_angle_type("兩者區別何在？") == "comparison"
    assert classify_angle_type("適用範圍？") == "application"
    assert classify_angle_type("其他雜訊") == "other"
    assert classify_angle_type("") == "other"


def test_build_angle_coverage_facets_and_labels():
    cov = build_angle_coverage(
        question="行政處分如何定義？",
        functional_gap="原稿未定義",
        user_value="補齊讀者對「行政處分如何定義？」所需的說明",
    )
    assert cov["angle_type"] == "definition"
    assert cov["angle_labels"][0] == "definition"
    assert "functional_gap" in cov["angle_labels"]
    assert "user_value" in cov["angle_labels"]
    assert "angle:definition" in cov["covered_facets"]
    assert "necessity:functional_gap" in cov["covered_facets"]
    assert "necessity:user_value" in cov["covered_facets"]
    assert "question" in cov["covered_facets"]
    assert cov["angle_key"] == build_angle_key("definition", "行政處分如何定義？")
    assert is_angle_coverage_complete(cov) is True


def test_normalize_and_key_stable_for_punctuation():
    a = build_angle_key("definition", "行政處分如何定義？")
    b = build_angle_key("definition", "行政處分如何定義!")
    # 去標點後應相同
    assert a == b
    assert normalize_angle_text("  A-B  ") == "a b"


def test_duplicate_relation_same_key():
    covs = [
        build_angle_coverage(question="行政處分定義？", functional_gap="a", user_value="u1"),
        build_angle_coverage(question="行政處分定義？", functional_gap="b", user_value="u2"),
    ]
    # 強制同一 key
    covs[1]["angle_key"] = covs[0]["angle_key"]
    covs[1]["angle_type"] = covs[0]["angle_type"]
    covs[1]["covered_facets"].append("duplicate-only")
    with_rel = attach_relations(covs)
    assert with_rel[0]["relation"]["kind"] == "duplicate"
    assert with_rel[1]["relation"]["kind"] == "duplicate"
    assert with_rel[0]["relation"]["duplicate_of"] == [1]
    summary = summarize_angle_coverage(with_rel)
    assert [0, 1] in summary["duplicate_pairs"]
    assert summary["synonym_pairs"] == []
    assert [cov["effective_angle_count"] for cov in with_rel] == [1, 0]
    assert with_rel[0]["duplicate_exclusion"] == {
        "excluded": False,
        "reason": None,
        "kept_argument_index": 0,
    }
    assert with_rel[1]["duplicate_exclusion"] == {
        "excluded": True,
        "reason": "duplicate",
        "kept_argument_index": 0,
    }
    assert summary["effective_angle_count"] == 1
    assert summary["excluded_angle_count"] == 1
    assert "duplicate-only" not in summary["covered_facets_union"]
    assert summary["has_sufficient_angles"] is False
    assert summary["coverage_ok"] is False


def test_synonym_relation_overlapping_definition_questions():
    covs = [
        build_angle_coverage(
            question="行政處分之定義為何？",
            functional_gap="a",
            user_value="u1",
        ),
        build_angle_coverage(
            question="行政處分定義如何說明？",
            functional_gap="b",
            user_value="u2",
        ),
    ]
    assert covs[0]["angle_type"] == covs[1]["angle_type"] == "definition"
    assert covs[0]["angle_key"] != covs[1]["angle_key"]
    rel0 = detect_angle_relation(0, covs)
    rel1 = detect_angle_relation(1, covs)
    assert rel0["kind"] == "synonym"
    assert rel1["kind"] == "synonym"
    assert 1 in rel0["synonym_of"]
    assert 0 in rel1["synonym_of"]


def test_unique_when_different_types():
    covs = [
        build_angle_coverage(question="如何定義？", functional_gap="a", user_value="u"),
        build_angle_coverage(question="有何限制？", functional_gap="b", user_value="v"),
    ]
    with_rel = attach_relations(covs)
    assert with_rel[0]["relation"]["kind"] == "unique"
    assert with_rel[1]["relation"]["kind"] == "unique"
    summary = summarize_angle_coverage(with_rel)
    assert summary["duplicate_pairs"] == []
    assert summary["synonym_pairs"] == []
    assert set(summary["unique_angle_types"]) == {"definition", "limitation"}
    assert summary["effective_angle_count"] == 2
    assert summary["required_effective_angle_count"] == 2
    assert summary["duplicate_ratio"] == 0.0
    assert summary["has_sufficient_angles"] is True
    assert summary["has_acceptable_duplicate_ratio"] is True
    assert summary["coverage_ok"] is True


def test_same_topic_two_distinct_non_duplicate_angles_pass():
    """同一主題但至少兩個不同且不重複的有效角度 → coverage_ok。

    例：主題皆為「行政處分」，角度分別為定義／限制，key 不同、非 duplicate／synonym。
    """
    covs = [
        build_angle_coverage(
            question="行政處分如何定義？",
            functional_gap="原稿未給定義",
            user_value="補齊讀者對「行政處分如何定義？」所需的說明",
        ),
        build_angle_coverage(
            question="行政處分有何限制？",
            functional_gap="原稿未給限制",
            user_value="補齊讀者對「行政處分有何限制？」所需的說明",
        ),
    ]
    assert covs[0]["angle_type"] == "definition"
    assert covs[1]["angle_type"] == "limitation"
    assert covs[0]["angle_key"] != covs[1]["angle_key"]

    with_rel = attach_relations(covs)
    assert [c["relation"]["kind"] for c in with_rel] == ["unique", "unique"]
    assert [c["effective_angle_count"] for c in with_rel] == [1, 1]
    assert all(not c["duplicate_exclusion"]["excluded"] for c in with_rel)

    summary = summarize_angle_coverage(with_rel)
    assert summary["duplicate_pairs"] == []
    assert summary["synonym_pairs"] == []
    assert set(summary["unique_angle_types"]) == {"definition", "limitation"}
    assert summary["effective_angle_count"] == 2
    assert summary["required_effective_angle_count"] == 2
    assert summary["excluded_angle_count"] == 0
    assert summary["duplicate_ratio"] == 0.0
    assert summary["has_sufficient_angles"] is True
    assert summary["has_acceptable_duplicate_ratio"] is True
    assert summary["coverage_ok"] is True
    assert "angle:definition" in summary["covered_facets_union"]
    assert "angle:limitation" in summary["covered_facets_union"]


def test_single_or_duplicate_angles_fail_coverage_gate():
    """只有單一有效角度（精確重複或同義去重後）→ 不合格。"""
    # 精確重複：兩論點同一 angle_key → 僅 1 個有效角度
    dup_covs = [
        build_angle_coverage(
            question="行政處分如何定義？",
            functional_gap="gap-a",
            user_value="value-a",
        ),
        build_angle_coverage(
            question="行政處分如何定義!",
            functional_gap="gap-b",
            user_value="value-b",
        ),
    ]
    assert dup_covs[0]["angle_key"] == dup_covs[1]["angle_key"]
    dup_with = attach_relations(dup_covs)
    dup_summary = summarize_angle_coverage(dup_with)
    assert [c["relation"]["kind"] for c in dup_with] == ["duplicate", "duplicate"]
    assert [c["effective_angle_count"] for c in dup_with] == [1, 0]
    assert dup_summary["effective_angle_count"] == 1
    assert dup_summary["required_effective_angle_count"] == 2
    assert dup_summary["has_sufficient_angles"] is False
    assert dup_summary["coverage_ok"] is False

    # 同義重複：同 type、高 token 重疊 → 第二個被排除，僅 1 個有效角度
    syn_covs = [
        build_angle_coverage(
            question="行政處分之定義為何？",
            functional_gap="gap-a",
            user_value="value-a",
        ),
        build_angle_coverage(
            question="行政處分定義如何說明？",
            functional_gap="gap-b",
            user_value="value-b",
        ),
    ]
    assert syn_covs[0]["angle_type"] == syn_covs[1]["angle_type"] == "definition"
    assert syn_covs[0]["angle_key"] != syn_covs[1]["angle_key"]
    syn_with = attach_relations(syn_covs)
    syn_summary = summarize_angle_coverage(syn_with)
    assert [c["relation"]["kind"] for c in syn_with] == ["synonym", "synonym"]
    assert [c["effective_angle_count"] for c in syn_with] == [1, 0]
    assert syn_summary["effective_angle_count"] == 1
    assert syn_summary["required_effective_angle_count"] == 2
    assert syn_summary["has_sufficient_angles"] is False
    assert syn_summary["coverage_ok"] is False


def test_excessive_duplicate_ratio_fails_coverage_gate():
    covs = [
        build_angle_coverage(
            question="行政處分如何定義？",
            functional_gap=f"gap-{i}",
            user_value=f"value-{i}",
        )
        for i in range(3)
    ]
    summary = summarize_angle_coverage(attach_relations(covs))
    assert summary["effective_angle_count"] == 1
    assert summary["excluded_angle_count"] == 2
    assert summary["duplicate_ratio"] == 2 / 3
    assert summary["max_duplicate_ratio"] == 0.5
    assert summary["has_sufficient_angles"] is False
    assert summary["has_acceptable_duplicate_ratio"] is False
    assert summary["coverage_ok"] is False


def test_incomplete_coverage_rejected():
    assert is_angle_coverage_complete(None) is False
    assert is_angle_coverage_complete({}) is False
    assert is_angle_coverage_complete(
        {
            "angle_type": "definition",
            "angle_labels": [],
            "covered_facets": ["angle:definition"],
            "angle_key": "definition:x",
        }
    ) is False
