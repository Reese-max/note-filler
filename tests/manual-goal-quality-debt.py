"""品質欠債目標：正式基線、排行榜與實際改善後量測的端到端驗收。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from note_filler.binding_report import build_binding_report
from note_filler.correction import CorrectionDoc, Segment, build_related_knowledge
from note_filler.metrics import TRACEABILITY_TARGET_SCORE
from note_filler.metrics_pipeline import (
    OUTPUT_MARKDOWN_BASELINE_NAME,
    QUALITY_DEBT_LEADERBOARD_NAME,
    generate_quality_debt_leaderboard,
    scan_output_markdown_baselines,
)
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source


NOTE_COUNT = 5
MIN_EFFECTIVE_ANGLES = 2
ANGLE_TYPES = ("definition", "effect")


def _verified_text(index: int, angle_type: str) -> str:
    return f"行政處分{angle_type}補充說明。[^{index + 1}]"


def _binding_report(mode: str) -> dict:
    verified = mode.startswith("verified")
    segment_count = int(mode[-1])
    segments = []
    for index, angle_type in enumerate(ANGLE_TYPES[:segment_count]):
        source = Source(
            id=f"law:{index}",
            title=f"行政處分{angle_type}",
            url=f"https://example.test/source-{index}",
            level="A",
            content=f"行政處分{angle_type}官方資料",
            fetched_date="2026-08-01",
            doc_date=None,
            distance=0.0,
        )
        text = _verified_text(index, angle_type) if verified else "【待補證】目前沒有可實際引用的來源。"
        segments.append(Segment(
            type="supplement",
            text=text,
            anchor_idx=0,
            sources=[source] if verified else [],
            confidence="verified" if verified else "pending_evidence",
            traceability=(
                [{"kind": "source", "id": source.id}]
                if verified
                else [{
                    "kind": "processing_record",
                    "id": f"pending:gap:{index}",
                    "question": "行政處分是什麼？",
                    "outcome": "pending_evidence",
                }]
            ),
            citation_spans=(
                [{
                    "source_id": source.id,
                    "span_start": text.index(f"[^{index + 1}]"),
                    "span_end": text.index(f"[^{index + 1}]") + len(f"[^{index + 1}]"),
                    "marker_text": f"[^{index + 1}]",
                }]
                if verified
                else []
            ),
            source_id=f"sources:{source.id}" if verified else f"pending:gap:{index}",
            source_ids=[source.id] if verified else [],
            functional_gap="需要說明行政處分的法律效果",
            user_value="幫助讀者理解行政處分的法律效果",
            summary=text,
            related_knowledge=build_related_knowledge(
                knowledge_body=text,
                functional_gap="需要說明行政處分的法律效果",
                user_value="幫助讀者理解行政處分的法律效果",
            ),
            argument_id=f"argument:{index}",
            angle_type=angle_type,
            angle_labels=[angle_type, "functional_gap", "user_value"],
        ))
    return build_binding_report(CorrectionDoc(
        Document("source.txt", (Paragraph(0, "原稿內容"),), "原稿內容"),
        segments,
    ))


def _write_case(output_root: Path, index: int, mode: str) -> tuple[Path, Path, Path]:
    case_dir = output_root / f"note-{index:02d}"
    case_dir.mkdir(parents=True)
    original_path = case_dir / "original.txt"
    artifact_path = case_dir / "note.md"
    original_text = (
        f"# 原稿 {index}\n\n"
        f"原稿第 {index} 筆，內容不可變。\n"
    )
    original_path.write_text(
        original_text,
        encoding="utf-8",
        newline="\n",
    )
    artifact_path.write_text(
        original_text,
        encoding="utf-8",
        newline="\n",
    )
    (case_dir / "binding_report.json").write_text(
        json.dumps(_binding_report(mode), ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    (case_dir / "delivery_manifest.json").write_text(
        json.dumps({
            "output_path": str(artifact_path),
            "input_path": str(original_path),
            "content_hash": hashlib.sha256(artifact_path.read_bytes()).hexdigest()[:16],
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    return original_path, artifact_path, case_dir / "binding_report.json"


def _repair_case(
    original_path: Path,
    artifact_path: Path,
    binding_report_path: Path,
) -> None:
    """把改善實際寫入成品，再更新其可驗證旁車資料。"""
    before = artifact_path.read_bytes()
    repaired = (
        artifact_path.read_text(encoding="utf-8")
        + "\n## 改善後補充\n"
        + "\n".join(_verified_text(index, angle_type) for index, angle_type in enumerate(ANGLE_TYPES))
        + "\n"
    )
    artifact_path.write_text(repaired, encoding="utf-8", newline="\n")
    assert artifact_path.read_bytes() != before
    assert artifact_path.read_bytes().startswith(original_path.read_bytes())

    binding_report_path.write_text(
        json.dumps(_binding_report("verified2"), ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    manifest_path = artifact_path.parent / "delivery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_hash"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()[:16]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _sha256(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _assert_leaderboard(path: Path, expected_count: int) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "note_filler.quality_debt_leaderboard.v2"
    assert payload["record_count"] == expected_count
    records = payload["records"]
    assert len(records) == expected_count
    assert [record["rank"] for record in records] == list(range(1, expected_count + 1))
    keys = [(
        record["traceability"] is None,
        record["traceability"] if record["traceability"] is not None else float("inf"),
        record["angles_per_topic"] is None,
        record["angles_per_topic"] if record["angles_per_topic"] is not None else float("inf"),
        record["artifact_path"],
        record["content_hash"],
    ) for record in records]
    assert keys == sorted(keys)
    return payload


def test_quality_debt_goal_runs_scan_ranking_and_repair_measurement(tmp_path: Path):
    output_root = tmp_path / "output"
    metrics_root = tmp_path / "metrics_output"
    before_baseline = metrics_root / OUTPUT_MARKDOWN_BASELINE_NAME
    after_baseline = metrics_root / "output_markdown_baseline_after.jsonl"
    before_leaderboard = metrics_root / QUALITY_DEBT_LEADERBOARD_NAME
    after_leaderboard = metrics_root / "quality_debt_leaderboard_after.json"

    cases = [
        _write_case(output_root, 1, "pending1"),
        _write_case(output_root, 2, "pending2"),
        _write_case(output_root, 3, "pending1"),
        _write_case(output_root, 4, "pending1"),
        _write_case(output_root, 5, "pending2"),
    ]
    original_hashes_before = _sha256([case[0] for case in cases])
    artifact_hashes_before = _sha256([case[1] for case in cases])

    before_scan = scan_output_markdown_baselines(output_root, before_baseline)
    before_records = _read_jsonl(before_baseline)
    assert len(list(output_root.rglob("*.md"))) == NOTE_COUNT
    assert before_scan.scanned_count == before_scan.created_count == NOTE_COUNT
    assert len(before_records) == NOTE_COUNT
    assert all(
        record["traceability"] is None
        or record["traceability"] < TRACEABILITY_TARGET_SCORE
        or record["angles_per_topic"] is None
        or record["angles_per_topic"] < MIN_EFFECTIVE_ANGLES
        for record in before_records
    )

    before_ranking = generate_quality_debt_leaderboard(
        before_baseline,
        before_leaderboard,
    )
    assert json.loads(before_leaderboard.read_text(encoding="utf-8")) == before_ranking
    _assert_leaderboard(before_leaderboard, NOTE_COUNT)

    for original_path, artifact_path, binding_report_path in cases:
        _repair_case(original_path, artifact_path, binding_report_path)

    assert _sha256([case[0] for case in cases]) == original_hashes_before
    assert all(
        digest != artifact_hashes_before[str(case[1])]
        for case in cases
        for digest in [_sha256([case[1]])[str(case[1])]]
    )

    after_scan = scan_output_markdown_baselines(output_root, after_baseline)
    after_records = _read_jsonl(after_baseline)
    assert len(list(output_root.rglob("*.md"))) == len(after_records) == NOTE_COUNT
    assert after_scan.scanned_count == after_scan.created_count == NOTE_COUNT
    improved_by_path = {
        record["artifact_path"]: record
        for record in after_records
        if (
            record["status"] == "calculated"
            and record["traceability"] is not None
            and record["traceability"] >= TRACEABILITY_TARGET_SCORE
            and record["angles_per_topic"] is not None
            and record["angles_per_topic"] >= MIN_EFFECTIVE_ANGLES
        )
    }
    assert len(improved_by_path) >= 5
    assert set(improved_by_path) == {record["artifact_path"] for record in after_records}

    after_ranking = generate_quality_debt_leaderboard(
        after_baseline,
        after_leaderboard,
    )
    assert json.loads(after_leaderboard.read_text(encoding="utf-8")) == after_ranking
    _assert_leaderboard(after_leaderboard, NOTE_COUNT)
    assert _sha256([case[0] for case in cases]) == original_hashes_before
