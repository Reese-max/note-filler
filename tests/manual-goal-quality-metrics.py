"""正式產出管線的品質量測驗收。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.llm import FakeLLM
from note_filler.pipeline import run_pipeline
from test_pipeline import FakeLaw, FakeTwinkle, _src


def _note(tmp_path: Path, name: str) -> Path:
    path = tmp_path / f"{name}.docx"
    document = DocxDocument()
    document.add_paragraph("行政處分是行政機關對外作成的單方行政行為。")
    document.save(str(path))
    return path


def _history(note_path: Path) -> list[dict]:
    history_path = note_path.with_name("metrics_history.jsonl")
    return [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]


def _quality_llm() -> FakeLLM:
    gaps = [
        {"question": "行政處分成立的要件為何？", "status": "missing", "reason": "原稿未說明要件。"},
        {"question": "行政處分撤銷的法律效果為何？", "status": "missing", "reason": "原稿未說明效果。"},
    ]
    return FakeLLM([
        "admin",
        "\n".join(item["question"] for item in gaps),
        json.dumps(gaps, ensure_ascii=False),
        '{"keyword": "行政處分要件", "law_name": null}',
        "行政處分成立須具備法定要件[^1][^2]。",
        '{"keyword": "行政處分撤銷效果", "law_name": null}',
        "撤銷後應依法律效果處理既有行政處分[^1][^2]。",
    ])


def test_quality_metrics_history_is_exact_and_idempotent(tmp_path):
    note_path = _note(tmp_path, "high-quality")
    original = note_path.read_bytes()
    source_batches = [
        [
            _src("requirements-a", "行政處分要件官方資料 A", "https://example.test/requirements-a", "A"),
            _src("requirements-b", "行政處分要件官方資料 B", "https://example.test/requirements-b", "B"),
        ],
        [
            _src("effect-a", "行政處分撤銷效果官方資料 A", "https://example.test/effect-a", "A"),
            _src("effect-b", "行政處分撤銷效果官方資料 B", "https://example.test/effect-b", "B"),
        ],
    ]

    run_pipeline(str(note_path), _quality_llm(), FakeTwinkle(source_batches), FakeLaw())
    records = _history(note_path)

    assert len(records) == 1
    record = records[0]
    assert set(record) == {
        "timestamp", "note_id", "product_hash", "status", "traceability", "angles_per_topic",
    }
    assert datetime.fromisoformat(record["timestamp"])
    assert isinstance(record["note_id"], str) and record["note_id"]
    assert isinstance(record["product_hash"], str) and len(record["product_hash"]) == 64
    assert record["status"] == "calculated"
    assert record["traceability"] == 1.0
    assert record["angles_per_topic"] >= 2
    assert note_path.read_bytes() == original

    run_pipeline(
        str(note_path),
        _quality_llm(),
        FakeTwinkle(source_batches),
        FakeLaw(),
    )
    rerun_records = _history(note_path)

    assert len(rerun_records) == 1
    assert [item["note_id"] for item in rerun_records] == [record["note_id"]]
    assert rerun_records == records


def test_low_quality_fixture_records_failed_threshold(tmp_path):
    note_path = _note(tmp_path, "low-quality")
    llm = FakeLLM([
        "admin",
        "行政處分成立的要件為何？",
        json.dumps([
            {"question": "行政處分成立的要件為何？", "status": "missing", "reason": "原稿未說明要件。"},
        ], ensure_ascii=False),
        '{"keyword": "行政處分要件", "law_name": null}',
        "【待補證】目前沒有可實際引用的來源。",
    ])

    run_pipeline(str(note_path), llm, FakeTwinkle([[]]), FakeLaw())
    record = _history(note_path)[0]

    assert record["status"] == "calculated"
    assert record["traceability"] == 0.0
    assert record["traceability"] < 1.0
    assert record["angles_per_topic"] < 2


@pytest.mark.parametrize("question_block", ["", "[]"], ids=["missing", "malformed"])
def test_missing_or_abnormal_argument_blocks_return_metrics_unavailable(tmp_path, question_block):
    note_path = _note(tmp_path, "metrics-unavailable")

    result = run_pipeline(
        str(note_path),
        FakeLLM(["admin", question_block]),
        FakeTwinkle([]),
        FakeLaw(),
    )
    record = _history(note_path)[0]

    assert not [segment for segment in result.segments if segment.type == "supplement"]
    assert result.metrics_record["status"] == "metrics_unavailable"
    assert record["status"] == "metrics_unavailable"
    assert record["traceability"] is None
    assert record["angles_per_topic"] is None
