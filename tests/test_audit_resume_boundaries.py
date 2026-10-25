"""Temporary-vault regressions: real state/artifact I/O, no live providers."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from note_filler import __main__ as cli
from note_filler.recovery import recover_delivery
from note_filler.task_state import MAX_TASK_ATTEMPTS, TaskStage, TaskStateManager
from note_filler.llm import FakeLLM


@pytest.mark.parametrize("payload", [b"{}", b'[]', b'{"private":"SYNTHETIC_PRIVATE"', b'\xff'])
def test_corrupt_task_state_is_not_replaced_or_treated_as_new(tmp_path, caplog, payload):
    manager = TaskStateManager(tmp_path / "state")
    key = str(tmp_path / "vault" / "note.txt")
    file = manager._state_path(key)
    file.write_bytes(payload)
    with pytest.raises(RuntimeError, match="state|狀態") as error:
        manager.start_task(key)
    assert file.read_bytes() == payload
    assert "SYNTHETIC_PRIVATE" not in str(error.value) + caplog.text


def test_nested_vault_paths_that_share_the_old_sanitized_name_keep_distinct_history(tmp_path):
    vault = tmp_path / "vault"
    one, two = vault / "a" / "b.txt", vault / "a_b.txt"
    one.parent.mkdir(parents=True)
    one.write_text("Synthetic original one", encoding="utf-8")
    two.write_text("Synthetic original two", encoding="utf-8")
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task(str(one), source_locator=str(one))
    manager.fail(str(one), stage=TaskStage.GENERATION, error_type="FixtureFailure", error_message="offline", recoverable=True)
    first = manager._state_path(str(one)).read_bytes()
    manager.start_task(str(two), source_locator=str(two))
    assert manager._state_path(str(one)) != manager._state_path(str(two))
    assert manager._state_path(str(one)).read_bytes() == first
    assert manager.load(str(one)).task_key == str(one)
    assert manager.load(str(two)).task_key == str(two)
    assert len(manager.load(str(two)).attempts) == 1
    assert one.read_text() == "Synthetic original one"
    assert two.read_text() == "Synthetic original two"


def test_interrupted_state_replacement_retains_prior_snapshot_and_retry_count(tmp_path, monkeypatch):
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task("fixture")
    manager.fail("fixture", stage=TaskStage.GENERATION, error_type="FixtureFailure", error_message="retained", recoverable=True)
    path = manager._state_path("fixture")
    before = path.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):
            manager.start_task("fixture")
    assert path.read_bytes() == before
    assert list(path.parent.glob("*.tmp")) == []
    resumed = TaskStateManager(path.parent).start_task("fixture")
    assert len(resumed.attempts) == 2
    assert resumed.attempts[0].error_message == "retained"


def test_exhausted_cli_task_never_reenters_the_actual_pipeline_or_provider(tmp_path):
    note = tmp_path / "vault" / "note.txt"
    note.parent.mkdir()
    note.write_text("Synthetic original note", encoding="utf-8")
    state_dir = tmp_path / "state"
    manager = TaskStateManager(state_dir)
    for _ in range(MAX_TASK_ATTEMPTS):
        manager.start_task(str(note), source_locator=str(note))
        manager.fail(str(note), stage=TaskStage.GENERATION, error_type="FixtureFailure", error_message="retained", recoverable=True)
    before = manager._state_path(str(note)).read_bytes()

    class ForbiddenProvider:
        calls = 0
        def complete(self, *args, **kwargs):
            self.calls += 1
            raise RuntimeError("provider must not start")

    provider = ForbiddenProvider()
    with pytest.raises(RuntimeError, match="attempt|嘗試"):
        cli.process_file(note, provider, None, None, tmp_path / "markdown-vault", "md", state_dir=state_dir)
    assert provider.calls == 0
    assert manager._state_path(str(note)).read_bytes() == before
    assert note.read_text() == "Synthetic original note"
    assert not (tmp_path / "markdown-vault").exists()


@pytest.mark.parametrize("payload", [b"{}", b'{"status":"delivered"}', b'\xff'])
def test_incomplete_or_non_utf8_receipt_never_verifies_empty_evidence(tmp_path, payload):
    receipt = tmp_path / "note.md.delivery_manifest.json"
    receipt.write_bytes(payload)
    for _ in range(2):
        verdict = recover_delivery(receipt)
        assert not verdict.verified
        assert verdict.status == "failed"
        assert verdict.errors
    assert receipt.read_bytes() == payload


def test_legacy_state_migrates_without_overwriting_the_only_old_history(tmp_path):
    manager = TaskStateManager(tmp_path / "state")
    key = str(tmp_path / "vault" / "note.txt")
    manager.start_task(key, source_locator=key)
    manager.fail(key, stage=TaskStage.GENERATION, error_type="FixtureFailure", error_message="old history", recoverable=True)
    current = manager._state_path(key)
    legacy = current.parent / (key.replace("/", "_").replace("\\", "_").replace(":", "_") + ".task_state.json")
    if current != legacy:
        current.rename(legacy)
    old_bytes = legacy.read_bytes()
    resumed = TaskStateManager(legacy.parent).start_task(key)
    assert len(resumed.attempts) == 2
    assert resumed.attempts[0].error_message == "old history"
    assert manager._state_path(key) != legacy
    assert legacy.read_bytes() == old_bytes


@pytest.mark.parametrize("field,value", [("attempts", None), ("state", "future-unknown-state"), ("future_schema", 2)])
def test_valid_json_with_unknown_or_missing_history_remains_untouched(tmp_path, field, value):
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task("fixture")
    path = manager._state_path("fixture")
    data = json.loads(path.read_text())
    data[field] = value
    before = json.dumps(data).encode()
    path.write_bytes(before)
    with pytest.raises(RuntimeError, match="state"):
        manager.start_task("fixture")
    assert path.read_bytes() == before


def test_running_last_attempt_cannot_exceed_lifetime_cap_after_interruption(tmp_path):
    manager = TaskStateManager(tmp_path / "state")
    for _ in range(MAX_TASK_ATTEMPTS):
        manager.start_task("fixture")
    rejected = TaskStateManager(tmp_path / "state").start_task("fixture")
    assert rejected.state.value == "exhausted"
    assert len(rejected.attempts) == MAX_TASK_ATTEMPTS


def test_deep_real_vault_path_does_not_exceed_the_state_filename_limit(tmp_path):
    source = tmp_path / "vault" / ("a" * 80) / ("b" * 80) / ("c" * 80) / "note.txt"
    source.parent.mkdir(parents=True)
    source.write_text("Synthetic original", encoding="utf-8")
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task(str(source), source_locator=str(source))
    assert manager.load(str(source)).source_locator == str(source)
    assert len(manager._state_path(str(source)).name) < 100
    assert source.read_text() == "Synthetic original"


def test_valid_foreign_legacy_alias_is_preserved_without_inheriting_its_attempts(tmp_path):
    manager = TaskStateManager(tmp_path / "state")
    first, second = "vault/a/b.txt", "vault/a_b.txt"
    manager.start_task(first)
    legacy = manager.state_dir / "vault_a_b.txt.task_state.json"
    manager._state_path(first).rename(legacy)
    before = legacy.read_bytes()
    fresh = manager.start_task(second)
    assert fresh.task_key == second and len(fresh.attempts) == 1
    assert legacy.read_bytes() == before
    assert manager.load(first).task_key == first


@pytest.mark.parametrize("operation", ["succeed", "fail"])
def test_other_state_mutations_also_preserve_unknown_corrupt_history(tmp_path, operation):
    manager = TaskStateManager(tmp_path / "state")
    file = manager._state_path("fixture")
    file.write_bytes(b'{"private":"SYNTHETIC_PRIVATE"')
    before = file.read_bytes()
    with pytest.raises(RuntimeError, match="state"):
        if operation == "succeed":
            manager.succeed("fixture", content="fixture result")
        else:
            manager.fail("fixture", stage=TaskStage.GENERATION, error_type="fixture", error_message="failure")
    assert file.read_bytes() == before


def test_real_pipeline_interruption_resume_and_recovery_in_a_temporary_markdown_vault(tmp_path):
    note = tmp_path / "vault" / "note.txt"
    note.parent.mkdir()
    original = b"Synthetic original note.\n\nAdministrative act notes."
    note.write_bytes(original)
    state_dir, output = tmp_path / "state", tmp_path / "Markdown-vault"

    class InterruptedProvider:
        def complete(self, *args, **kwargs):
            raise OSError("offline fixture interruption")

    with pytest.raises(OSError, match="offline fixture interruption"):
        cli.process_file(note, InterruptedProvider(), None, None, output, "md", state_dir=state_dir)

    class Search:
        def search(self, *args, **kwargs): return []

    class Law:
        def lookup_article(self, *args): return None
        def law_exists(self, *args): return True
        def fuzzy_find_law(self, *args): return None
        def search_articles(self, *args, **kwargs): return []

    questions = ["行政處分如何定義?", "行政處分有哪些限制?"]
    provider = FakeLLM([
        "admin", "\n".join(questions),
        json.dumps([{"question": question, "status": "missing", "reason": "fixture"} for question in questions]),
        '{"keyword":"行政處分","law_name":null}', "【待補證】定義待來源核對。",
        '{"keyword":"行政處分","law_name":null}', "【待補證】限制待來源核對。",
    ])
    result = cli.process_file(note, provider, Search(), Law(), output, "md", state_dir=state_dir)
    generated = Path(result["output"])
    assert generated.suffix == ".md" and generated.read_text(encoding="utf-8")
    assert result["verified"] == 0 # Synthetic absence of sources never becomes verified evidence.
    assert len(provider.calls) == 7
    assert note.read_bytes() == original
    record = TaskStateManager(state_dir).load(str(note))
    assert record.state.value == "succeeded"
    assert len(record.attempts) == 2
    assert record.attempts[0].error_type == "OSError"
    receipt = generated.with_name(generated.name + ".delivery_manifest.json")
    before = receipt.read_bytes(), generated.read_bytes()
    for _ in range(2):
        assert recover_delivery(receipt).verified
    assert (receipt.read_bytes(), generated.read_bytes()) == before
    assert list(output.glob("*.md")) == [generated]
    assert note.read_bytes() == original


def test_actual_quality_gate_failure_is_persisted_as_transmission_failure(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("Synthetic original note", encoding="utf-8")

    class Search:
        def search(self, *args, **kwargs): return []

    class Law:
        def search_articles(self, *args, **kwargs): return []
        def lookup_article(self, *args): return None
        def law_exists(self, *args): return True
        def fuzzy_find_law(self, *args): return None

    questions = ["行政處分如何定義?", "行政處分的定義為何?"]
    provider = FakeLLM(["admin", "\n".join(questions), json.dumps([{"question": q, "status": "missing", "reason": "fixture"} for q in questions]),
                        '{"keyword":"行政處分","law_name":null}', "【待補證】定義待來源核對。",
                        '{"keyword":"行政處分","law_name":null}', "【待補證】相同角度待來源核對。"])
    with pytest.raises(RuntimeError, match="角度"):
        cli.process_file(note, provider, Search(), Law(), tmp_path / "Markdown-vault", "md", state_dir=tmp_path / "state")
    record = TaskStateManager(tmp_path / "state").load(str(note))
    assert record.state.value == "failed"
    assert record.stage == TaskStage.TRANSMISSION
    assert record.attempts[0].error_type == "RuntimeError"
    assert len(provider.calls) == 7
    assert not list((tmp_path / "Markdown-vault").glob("*.delivery_manifest.json"))
    assert note.read_text() == "Synthetic original note"


def test_failed_cli_reservation_write_cannot_reclassify_a_prior_running_attempt(tmp_path, monkeypatch):
    note = tmp_path / "note.txt"
    note.write_text("Synthetic original note", encoding="utf-8")
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task(str(note))
    state = manager._state_path(str(note))
    before = state.read_bytes()
    provider = FakeLLM([])
    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(OSError("fixture atomic reservation failure")))
        with pytest.raises(OSError, match="atomic reservation failure"):
            cli.process_file(note, provider, None, None, tmp_path / "Markdown-vault", "md", state_dir=manager.state_dir)
    assert state.read_bytes() == before
    assert provider.calls == []


def test_partial_receipt_with_missing_artifact_is_preserved_before_failure_mutation(tmp_path):
    receipt = tmp_path / "note.md.delivery_manifest.json"
    before = json.dumps({"output_path": str(tmp_path / "missing.md"), "delivery_status": {
        "primary_note_ready": False, "user_channel_sent": False, "local_fallback_written": False,
    }}).encode()
    receipt.write_bytes(before)
    verdict = recover_delivery(receipt)
    assert not verdict.verified and verdict.status == "failed"
    assert receipt.read_bytes() == before
    assert not (tmp_path / "recovery_history.jsonl").exists()


def test_transmission_failure_phase_survives_a_later_generation_retry(tmp_path):
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task("fixture")
    manager.fail("fixture", stage=TaskStage.TRANSMISSION, error_type="FixtureFailure", error_message="retained", recoverable=True)
    retried = TaskStateManager(manager.state_dir).start_task("fixture")
    assert retried.stage == TaskStage.GENERATION
    assert retried.attempts[0].stage == TaskStage.TRANSMISSION
    assert retried.attempts[0].error_message == "retained"


def test_missing_attempt_timestamp_cannot_be_fabricated_during_resume(tmp_path):
    manager = TaskStateManager(tmp_path / "state")
    manager.start_task("fixture")
    file = manager._state_path("fixture")
    data = json.loads(file.read_text()); del data["attempts"][0]["timestamp"]
    before = json.dumps(data).encode(); file.write_bytes(before)
    with pytest.raises(RuntimeError, match="state"):
        manager.start_task("fixture")
    assert file.read_bytes() == before


@pytest.mark.parametrize("report_hash", ["", "invalid-hash"])
def test_declared_report_without_valid_hash_is_preserved_before_any_recovery_update(tmp_path, report_hash):
    source, output = tmp_path / "note.txt", tmp_path / "note.md"
    source.write_text("Synthetic original", encoding="utf-8")
    output.write_text("Synthetic generated", encoding="utf-8")
    receipt = cli.write_delivery_receipt(output, source, content=output.read_text(), fmt="md")
    data = json.loads(receipt.read_text())
    data["binding_report_content_hash"] = report_hash
    before = json.dumps(data).encode(); receipt.write_bytes(before)
    verdict = recover_delivery(receipt)
    assert not verdict.verified and verdict.status == "failed"
    assert receipt.read_bytes() == before
    assert not (tmp_path / "recovery_history.jsonl").exists()


@pytest.mark.parametrize("report_path", [None, 123])
def test_declared_report_hash_also_requires_a_usable_report_identity(tmp_path, report_path):
    source, output = tmp_path / "note.txt", tmp_path / "note.md"
    source.write_text("Synthetic original", encoding="utf-8")
    output.write_text("Synthetic generated", encoding="utf-8")
    receipt = cli.write_delivery_receipt(output, source, content=output.read_text(), fmt="md")
    data = json.loads(receipt.read_text())
    data.pop("binding_report_canonical_path", None)
    data["binding_report_path"] = report_path
    data["binding_report_content_hash"] = "a" * 64
    before = json.dumps(data).encode(); receipt.write_bytes(before)
    verdict = recover_delivery(receipt)
    assert not verdict.verified and verdict.status == "failed"
    assert receipt.read_bytes() == before
