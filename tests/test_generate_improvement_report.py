import json
from pathlib import Path

from scripts.generate_improvement_report import _load_records_from_manifests


def _write_manifest(path: Path, input_path: str, output_path: str, metric_value: int) -> None:
    path.write_text(
        json.dumps(
            {
                "input_path": input_path,
                "output_path": output_path,
                "polaris_metrics": {"sample_metric": {"score": metric_value}},
            }
        ),
        encoding="utf-8",
    )


def test_report_loads_every_note_owned_sidecar_and_deduplicates_latest_copy(tmp_path: Path) -> None:
    first = tmp_path / "first.md.delivery_manifest.json"
    second = tmp_path / "second.md.delivery_manifest.json"
    latest = tmp_path / "delivery_manifest.json"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "third.md.delivery_manifest.json"

    _write_manifest(first, "notes/first.txt", "out/first.md", 1)
    _write_manifest(second, "notes/second.txt", "out/second.md", 2)
    _write_manifest(latest, "notes/second.txt", "out/second.md", 2)
    _write_manifest(nested, "notes/third.txt", "out/third.md", 3)

    records = _load_records_from_manifests([tmp_path], recursive=True)

    assert len(records) == 3
    assert {record["source_path"] for record in records} == {
        "notes/first.txt",
        "notes/second.txt",
        "notes/third.txt",
    }
    second_record = next(record for record in records if record["source_path"] == "notes/second.txt")
    assert Path(second_record["manifest_path"]) == second


def test_report_nonrecursive_scan_reads_only_top_level_sidecars(tmp_path: Path) -> None:
    top_level = tmp_path / "top.md.delivery_manifest.json"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "nested.md.delivery_manifest.json"

    _write_manifest(top_level, "notes/top.txt", "out/top.md", 1)
    _write_manifest(nested, "notes/nested.txt", "out/nested.md", 2)

    records = _load_records_from_manifests([tmp_path], recursive=False)

    assert [record["source_path"] for record in records] == ["notes/top.txt"]


def test_report_rejects_foreign_receipt_before_deduplicating_output(tmp_path: Path) -> None:
    foreign = tmp_path / "first.md.delivery_manifest.json"
    matching = tmp_path / "second.md.delivery_manifest.json"
    latest = tmp_path / "delivery_manifest.json"
    # A copied receipt sorts first, but its name does not bind the output it
    # claims. It must neither publish wrong metrics nor hide the real receipt.
    _write_manifest(foreign, "notes/foreign.txt", "out/second.md", 0)
    _write_manifest(matching, "notes/second.txt", "out/second.md", 2)
    _write_manifest(latest, "notes/second.txt", "out/second.md", 2)

    records = _load_records_from_manifests([tmp_path], recursive=False)

    assert records == [{
        "source_path": "notes/second.txt",
        "manifest_path": str(matching),
        "polaris_metrics": {"sample_metric": {"score": 2}},
    }]


def test_report_rejects_foreign_receipt_without_a_matching_copy(tmp_path: Path) -> None:
    foreign = tmp_path / "first.md.delivery_manifest.json"
    _write_manifest(foreign, "notes/foreign.txt", "out/second.md", 0)

    assert _load_records_from_manifests([tmp_path]) == []
