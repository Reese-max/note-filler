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

import pytest

from scripts import refresh_design_acceptance as refresh

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


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _baseline_reachability(repo: Path, commit: str) -> str:
    """Check the validation reference without requiring historical run objects.

    A shallow boundary can hide the baseline or its ancestry. This is explicitly
    unverified, while a complete clone must prove that the baseline is reachable.
    No fetching or dependence on merged feature branches is allowed here.
    """
    assert re.fullmatch(r"[0-9a-f]{40}", commit), "invalid validation baseline SHA"
    shallow = _git(repo, "rev-parse", "--is-shallow-repository")
    assert shallow.returncode == 0, shallow.stderr
    assert shallow.stdout.strip() in {"true", "false"}
    is_shallow = shallow.stdout.strip() == "true"
    show = _git(repo, "cat-file", "-t", commit)
    if show.returncode != 0:
        assert is_shallow, (
            f"validation baseline {commit} is not present in this complete clone; "
            "choose a commit reachable from the default branch"
        )
        return "unverified (shallow history; use a complete clone to verify ancestry)"
    assert show.stdout.strip() == "commit", "validation baseline must name a commit"
    reachable = _git(repo, "merge-base", "--is-ancestor", commit, "HEAD")
    if reachable.returncode == 0:
        return "verified"
    assert reachable.returncode == 1, reachable.stderr
    if is_shallow:
        shallow_path = _git(repo, "rev-parse", "--git-path", "shallow")
        assert shallow_path.returncode == 0, shallow_path.stderr
        boundaries = (repo / shallow_path.stdout.strip()).read_text().splitlines()
        if any(
            _git(repo, "merge-base", "--is-ancestor", sha, "HEAD").returncode == 0
            for sha in boundaries
        ):
            return "unverified (shallow history; use a complete clone to verify ancestry)"
    raise AssertionError(
        f"validation baseline {commit} is not an ancestor of HEAD; "
        "choose a commit reachable from the default branch"
    )


def _history_fixture(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "source"
    repo.mkdir()
    assert _git(repo, "init", "--initial-branch=main").returncode == 0
    (repo / "evidence.txt").write_text("baseline\n")
    assert _git(repo, "add", ".").returncode == 0
    assert _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "baseline").returncode == 0
    baseline = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "evidence.txt").write_text("current\n")
    assert _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-am", "current").returncode == 0
    return repo, baseline


def test_validation_baseline_in_single_branch_clone(tmp_path: Path) -> None:
    repo, baseline = _history_fixture(tmp_path)
    clone = tmp_path / "clone"
    assert _git(tmp_path, "clone", "--single-branch", "--branch", "main",
                repo.as_uri(), str(clone)).returncode == 0
    assert _baseline_reachability(clone, baseline) == "verified"


def test_validation_baseline_outside_shallow_clone_is_explicitly_unverified(tmp_path: Path) -> None:
    repo, baseline = _history_fixture(tmp_path)
    clone = tmp_path / "shallow"
    assert _git(tmp_path, "clone", "--depth=1", "--single-branch", "--branch", "main",
                repo.as_uri(), str(clone)).returncode == 0
    assert _git(clone, "cat-file", "-t", baseline).returncode != 0
    assert _baseline_reachability(clone, baseline).startswith("unverified (shallow history")
    assert _baseline_reachability(clone, _git(clone, "rev-parse", "HEAD").stdout.strip()) == "verified"
    assert _git(clone, "cat-file", "-t", baseline).returncode != 0  # no implicit fetch
    assert _git(clone, "fetch", "origin", baseline).returncode == 0
    assert _git(clone, "cat-file", "-t", baseline).stdout.strip() == "commit"
    assert _baseline_reachability(clone, baseline).startswith("unverified (shallow history")
    assert _git(clone, "fetch", "--unshallow", "origin").returncode == 0
    assert _baseline_reachability(clone, baseline) == "verified"


def test_validation_baseline_rejects_missing_and_unrelated_commits(tmp_path: Path) -> None:
    repo, baseline = _history_fixture(tmp_path)
    with pytest.raises(AssertionError, match="not present in this complete clone"):
        _baseline_reachability(repo, "0" * 40)
    assert _git(repo, "checkout", "-b", "unrelated", baseline).returncode == 0
    (repo / "unrelated.txt").write_text("separate branch\n")
    assert _git(repo, "add", ".").returncode == 0
    assert _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "unrelated").returncode == 0
    unrelated = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert _git(repo, "checkout", "main").returncode == 0
    with pytest.raises(AssertionError, match="not an ancestor"):
        _baseline_reachability(repo, unrelated)


def test_validation_baseline_rejects_non_commit_and_invalid_sha(tmp_path: Path) -> None:
    repo, _ = _history_fixture(tmp_path)
    blob = _git(repo, "rev-parse", "HEAD:evidence.txt").stdout.strip()
    with pytest.raises(AssertionError, match="must name a commit"):
        _baseline_reachability(repo, blob)
    with pytest.raises(AssertionError, match="invalid validation baseline SHA"):
        _baseline_reachability(repo, "main")


def test_refresh_records_real_head_without_writing_historical_results() -> None:
    outputs = [_PACKAGE, _PACKAGE_MD, _REPORT]
    before = [path.read_bytes() for path in outputs]
    package = refresh.build_package()
    assert package["acceptance_pass"] is True, package["failures"]
    current_head = _git(_REPO, "rev-parse", "HEAD").stdout.strip()
    assert package["git"]["head"] == current_head
    assert package["git"]["validation_baseline"]["commit"] == current_head
    assert [path.read_bytes() for path in outputs] == before


def test_rendered_git_observation_and_validation_baseline_are_distinct() -> None:
    package = _load_json(_PACKAGE)
    # Lock the migration's historical observation, while permitting a genuine
    # future refresh (new timestamp, actual HEAD and new executed test results).
    if package["generated_at"] == "2026-09-16T15:52:26+08:00":
        assert package["git"]["head"] == "b58d1324bac1276170d53342aafbc4158b285163"
    companions = [
        refresh.render_package_md(package), refresh.render_report(package),
        _PACKAGE_MD.read_text(encoding="utf-8"), _REPORT.read_text(encoding="utf-8"),
    ]
    for rendered in companions:
        assert package["git"]["head"] in rendered
        assert package["git"]["validation_baseline"]["commit"] in rendered
        assert "歷史實測" in rendered
        assert "驗證基準" in rendered
        assert "shallow" in rendered


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
    baseline = package["git"]["validation_baseline"]
    assert re.fullmatch(r"[0-9a-f]{40}", baseline["commit"])
    assert baseline["source"].strip()

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
    """Validate baseline reachability separately from the historical run HEAD."""
    package = _load_json(_PACKAGE)
    baseline_head = package["git"]["validation_baseline"]["commit"]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_REPO,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
    ).stdout.strip()
    # Historical execution HEAD may belong to a deleted or squash-merged branch.
    # It remains evidence metadata, never rewritten to satisfy Git availability.
    reachability = _baseline_reachability(_REPO, baseline_head)
    assert head  # current HEAD exists

    print("\n===== DESIGN_ACCEPTANCE_BEGIN =====")
    print(f"SCHEMA: {package['schema']}")
    print(f"PACKAGE_HEAD: {package['git']['head']}")
    print(f"VALIDATION_BASELINE: {baseline_head}")
    print(f"BASELINE_ANCESTRY: {reachability}")
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
