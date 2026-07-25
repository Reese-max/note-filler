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
    with_rel = attach_relations(covs)
    assert with_rel[0]["relation"]["kind"] == "duplicate"
    assert with_rel[1]["relation"]["kind"] == "duplicate"
    assert with_rel[0]["relation"]["duplicate_of"] == [1]
    summary = summarize_angle_coverage(with_rel)
    assert [0, 1] in summary["duplicate_pairs"]
    assert summary["synonym_pairs"] == []


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
