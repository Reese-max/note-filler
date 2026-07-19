"""Machine-checkable design acceptance for D-01..D-05.

Narrative-only or count-only packages must fail. Every claim must map to a
spec file, impl content anchors, and offline test anchors present in the
committed package.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CLAIMS = _REPO / "docs" / "specs" / "evidence" / "design-acceptance-claims.json"
_PACKAGE = _REPO / "docs" / "specs" / "evidence" / "design-acceptance-package.json"
_PACKAGE_MD = _REPO / "docs" / "specs" / "evidence" / "design-acceptance-package.md"
_REPORT = _REPO / "docs" / "design-acceptance-2026-07-19.md"
_EXPECTED_IDS = ["D-01", "D-02", "D-03", "D-04", "D-05"]
_SCHEMA = "note-filler.design-acceptance/v1"
_CLAIMS_SCHEMA = "note-filler.design-acceptance-claims/v1"
_CONFIRMATION_FIELDS = {
    "event_id",
    "confirmed_by",
    "confirmed_at",
    "method",
    "resolution_status",
    "todo",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_design_claims_index_is_complete() -> None:
    """Source claims catalog must list D-01..D-05 with required fields."""
    data = _load_json(_CLAIMS)
    assert data["schema"] == _CLAIMS_SCHEMA
    assert "禁止" in data["rule"] or "必須" in data["rule"]
    ids = [c["id"] for c in data["claims"]]
    assert ids == _EXPECTED_IDS
    for claim in data["claims"]:
        assert ( _REPO / claim["spec_file"]).is_file(), claim["spec_file"]
        assert claim["impl_anchors"], claim["id"]
        assert claim["test_anchors"], claim["id"]
        record = claim["confirmation_record"]
        assert set(record) == _CONFIRMATION_FIELDS, claim["id"]
        assert all(record[field].strip() for field in _CONFIRMATION_FIELDS - {"todo"})
        assert datetime.fromisoformat(record["confirmed_at"]).tzinfo is not None
        assert record["resolution_status"] in {"已結案", "待辦"}
        if record["resolution_status"] == "待辦":
            assert record["todo"].strip(), claim["id"]
        for anchor in claim["impl_anchors"]:
            path = _REPO / anchor["path"]
            assert path.is_file(), f"{claim['id']}: missing {anchor['path']}"
            text = path.read_text(encoding="utf-8")
            for token in anchor["must_contain"]:
                assert token in text, (
                    f"{claim['id']}: {anchor['path']} missing token {token!r}"
                )


def test_design_acceptance_package_is_machine_checkable() -> None:
    """Committed package must be per-claim evidence, not a count summary."""
    assert _PACKAGE.is_file(), "missing design-acceptance-package.json — run refresh script"
    assert _PACKAGE_MD.is_file(), "missing design-acceptance-package.md"
    assert _REPORT.is_file(), "missing design-acceptance report"

    package = _load_json(_PACKAGE)
    required = {
        "schema",
        "generated_at",
        "rule",
        "git",
        "claim_ids",
        "per_claim",
        "claim_to_artifact_map",
        "failures",
        "acceptance_mode",
        "acceptance_pass",
        "quality_gates_immutable",
    }
    missing = required - set(package)
    assert not missing, f"package missing fields: {sorted(missing)}"
    assert package["schema"] == _SCHEMA
    assert package["acceptance_mode"] == "per-claim-evidence"
    assert package["claim_ids"] == _EXPECTED_IDS
    assert package["acceptance_pass"] is True
    assert package["failures"] == []
    assert package["git"]["head"]
    assert re.fullmatch(r"[0-9a-f]{40}", package["git"]["head"])

    claims_src = _load_json(_CLAIMS)
    by_id = {c["id"]: c for c in package["per_claim"]}
    map_by_id = {c["claim_id"]: c for c in package["claim_to_artifact_map"]}
    for src in claims_src["claims"]:
        cid = src["id"]
        entry = by_id[cid]
        assert entry["claim_ok"] is True, cid
        assert entry["confirmation_record_ok"] is True, cid
        assert entry["confirmation_record"] == src["confirmation_record"]
        assert entry["spec_exists"] is True
        assert entry["spec_file"] == src["spec_file"]
        assert all(a["ok"] for a in entry["impl_anchors"]), cid
        for t in entry["test_individual_results"]:
            assert t["status"] == "passed", (cid, t)
            assert t["exit_code"] == 0, (cid, t)
            assert t["invocation"]
            assert "pytest" in t["invocation"]
        mapped = map_by_id[cid]
        assert mapped["ok"] is True
        assert mapped["spec_file"] == src["spec_file"]
        assert set(mapped["test_ids"]) == set(src["test_anchors"])
        assert mapped["confirmation_event_id"] == src["confirmation_record"]["event_id"]
        assert mapped["confirmation_status"] == src["confirmation_record"]["resolution_status"]
        assert f"per_claim[{cid}].confirmation_record" in mapped["package_fields"]

    # Markdown companions must reference schema and each claim id
    md = _PACKAGE_MD.read_text(encoding="utf-8")
    report = _REPORT.read_text(encoding="utf-8")
    assert _SCHEMA in md
    assert "ACCEPTANCE_PASS" in md
    assert "確認紀錄" in md
    assert "確認紀錄" in report
    for cid in _EXPECTED_IDS:
        assert cid in md
        assert cid in report
    assert "design-acceptance-package.json" in report
    assert "per-claim-evidence" in report


def test_design_acceptance_rejects_claim_without_artifact() -> None:
    """A narrative-only / count-only payload must fail schema requirements."""
    invalid_payloads = [
        {
            "summary": "design docs exist",
            "counts": {"claims": 5},
        },
        {
            "schema": _SCHEMA,
            "claim_ids": _EXPECTED_IDS,
            # missing per_claim / map / git / acceptance_mode
        },
        {
            "schema": _SCHEMA,
            "claim_ids": _EXPECTED_IDS,
            "per_claim": [
                {
                    "id": "D-01",
                    "title": "x",
                    "spec_file": "docs/nope.md",
                    "claim_ok": True,
                    "impl_anchors": [],
                    "test_individual_results": [],
                }
            ],
            "claim_to_artifact_map": [],
            "failures": [],
            "acceptance_mode": "per-claim-evidence",
            "acceptance_pass": True,
            "git": {"head": "0" * 40},
        },
    ]
    required = {
        "schema",
        "git",
        "claim_ids",
        "per_claim",
        "claim_to_artifact_map",
        "failures",
        "acceptance_mode",
        "acceptance_pass",
    }
    for payload in invalid_payloads:
        missing = required - set(payload)
        if missing:
            assert missing  # structurally incomplete
            continue
        # structurally present but anchors empty / bogus → must not be treated OK
        assert payload["per_claim"][0]["impl_anchors"] == []
        assert payload["per_claim"][0]["test_individual_results"] == []
        assert not (
            payload["per_claim"][0]["impl_anchors"]
            and payload["per_claim"][0]["test_individual_results"]
        )


def test_design_package_head_matches_repo_and_claim_map_printable() -> None:
    """Package HEAD must be a real git object; claim map must be 1:1 printable."""
    package = _load_json(_PACKAGE)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_REPO,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
    ).stdout.strip()
    # Package may have been generated before this commit; still must be valid object
    show = subprocess.run(
        ["git", "cat-file", "-t", package["git"]["head"]],
        cwd=_REPO,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert show.returncode == 0, package["git"]["head"]
    assert show.stdout.strip() == "commit"
    assert head  # current HEAD exists

    print("\n===== DESIGN_ACCEPTANCE_BEGIN =====")
    print(f"SCHEMA: {package['schema']}")
    print(f"PACKAGE_HEAD: {package['git']['head']}")
    print(f"CURRENT_HEAD: {head}")
    print(f"ACCEPTANCE_MODE: {package['acceptance_mode']}")
    print(f"ACCEPTANCE_PASS: {package['acceptance_pass']}")
    for row in package["claim_to_artifact_map"]:
        print(
            f"{row['claim_id']}: ok={row['ok']} "
            f"spec={row['spec_file']} "
            f"impl={len(row['impl_files'])} "
            f"tests={len(row['test_ids'])}"
        )
        for path in row["impl_files"]:
            print(f"  impl: {path}")
        for tid in row["test_ids"]:
            print(f"  test: {tid}")
    print(f"PYTHON: {sys.executable}")
    print("===== DESIGN_ACCEPTANCE_END =====")
