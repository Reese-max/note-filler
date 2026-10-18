"""根目錄 README 的產品安全契約驗收（issue #1）。

50-persona audit 要求：根目錄必須有 README，向使用者/新維護者
揭露本工具的用途、非用途與「無來源不進正文」硬規則，並說明
輸入/輸出目錄、溯源欄位、原稿保護與回滾、安裝與測試命令、
provider 邊界（不含 secrets），以及一條最小端到端範例。

迴歸基準：A02/C11/H05 型使用者應能在不讀原始碼的情況下，
依 README 跑唯讀檢視路徑，並分辨「原文 / AI 補充 / 來源佐證 /
待審核 / 最終交付」五種文字狀態。
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"),
    re.compile(r"\b(?:gh[pousr]|xox[baprs])_[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{24,}\b"),
)


@pytest.fixture(scope="module")
def readme_text() -> str:
    assert README.is_file(), "根目錄缺少 README.md"
    text = README.read_text(encoding="utf-8")
    assert text.strip(), "README.md 不得為空"
    return text


def test_readme_states_purpose_non_purpose_and_unsourced_rule(readme_text):
    """用途／非用途／硬規則：無來源內容不得進入正典筆記。"""
    for token in ("訂正稿", "非目的", "無來源不進正文", "原稿不可變"):
        assert token in readme_text, f"README 缺少契約語句：{token}"


def test_readme_explains_directories_and_artifact_authority(readme_text):
    """輸入／輸出目錄導覽，且區分 generated 與 authoritative。"""
    for token in (
        "src/note_filler/",
        "app/",
        "tests/",
        "docs/",
        "data/",
        "output/",
        "metrics_output/",
        "scripts/",
        ".task_state/",
        "authoritative",
        "generated",
    ):
        assert token in readme_text, f"README 缺少目錄／權威性說明：{token}"


def test_readme_documents_provenance_fields_and_evidence(readme_text):
    """來源／溯源欄位與可查證的機器可讀 artifact。"""
    for token in (
        "binding_report.json",
        "delivery_manifest.json",
        "traceability",
        "confidence",
        "verified",
        "pending_evidence",
        "【待補證】",
        "來源識別碼",
        "處理紀錄",
        "原始輸入",
        "fetched_date",
        "doc_date",
    ):
        assert token in readme_text, f"README 缺少溯源欄位說明：{token}"


def test_readme_documents_original_protection_and_rollback(readme_text):
    """原稿不被覆寫的機制與 rollback／recovery 路徑。"""
    for token in (
        "recover_delivery",
        "recovery_history.jsonl",
        "recovery_attempts",
        "artifact_integrity_mismatch",
        "訂正稿",
    ):
        assert token in readme_text, f"README 缺少原稿保護／回滾說明：{token}"


def test_readme_documents_setup_tests_and_provider_boundaries(readme_text):
    """本機安裝、測試命令、整合測試需求與 provider 邊界（不含 secrets）。"""
    for token in (
        "pip install -e",
        "constraints-pinned.txt",
        "pytest",
        "not integration",
        "run_tests.sh",
        "127.0.0.1:8318",
        "grok",
        "TWINKLE_HUB_TOKEN",
        "data/law_index.db",
    ):
        assert token in readme_text, f"README 缺少安裝／測試／provider 說明：{token}"


def test_readme_has_minimal_end_to_end_example(readme_text):
    """最小端到端範例：原稿 → 研究建議 → 證據審查 → 接受的輸出。"""
    for token in (
        "python -m note_filler",
        "tests/fixtures/real_note.txt",
        "訂正稿",
        "delivery_manifest.json",
        "binding_report.json",
    ):
        assert token in readme_text, f"README 缺少端到端範例要素：{token}"


def test_readme_read_only_path_and_five_state_taxonomy(readme_text):
    """迴歸：讀者能分辨 原文 / AI 補充 / 來源佐證 / 待審核 / 最終交付。"""
    for token in (
        "original",
        "supplement",
        "AI-researched",
        "source-backed",
        "pending review",
        "final",
        "read-only",
    ):
        assert token in readme_text, f"README 缺少五態判讀語彙：{token}"


def test_readme_contains_no_secret_shaped_strings(readme_text):
    """文件不得含 token/private key 形狀的字串（與推送掃描同規則）。"""
    for pattern in SECRET_PATTERNS:
        match = pattern.search(readme_text)
        assert match is None, f"README 含疑似 secret：{match.group(0)!r}"


@pytest.mark.parametrize(
    "required,forbidden",
    [
        pytest.param(("表格", "頁首頁尾", "首尾空白"), (), id="parsing-limits"),
        pytest.param(("僅 CLI", "網頁介面不寫"), (), id="receipt-scope"),
        pytest.param(
            ("覆寫既有成品", "輸入集合之外", "每份輸入各用一個", "metrics_history.jsonl"),
            ("絕不覆寫輸入檔",), id="output-collisions",
        ),
        pytest.param(
            ("segments[]", "arguments[]", "source_fragments", "trace_source_ids", "source_id_field"),
            (), id="artifact-schemas",
        ),
        pytest.param(("公開網址", "外部服務失敗", "不保證 skip"), (), id="integration-requirements"),
        pytest.param(
            ("相同失敗特徵會去重", "成功驗證不追加", "不會重新生成"),
            (), id="recovery-history",
        ),
        pytest.param(("僅網頁介面", "CLI 請用 `--db`"), (), id="db-override"),
        pytest.param(("bash scripts/run_tests.sh",), ("./scripts/run_tests.sh",), id="bash-invocation"),
    ],
)
def test_readme_discloses_runtime_limits(readme_text, required, forbidden):
    """文件須揭露既有入口及資料保護限制，不能把理想契約當成實作。"""
    for token in required:
        assert token in readme_text, f"README 未揭露：{token}"
    for token in forbidden:
        assert token not in readme_text, f"README 仍含不成立的保證／命令：{token}"


def test_readme_pending_state_does_not_require_empty_sources_or_text_prefix(readme_text):
    pending_row = next(line for line in readme_text.splitlines() if line.startswith("| pending review"))
    assert "來源清單可能非空" in pending_row
    assert "confidence" in pending_row
    assert "JSON 的 `text` 不保證" in readme_text
    assert "原文段的 `verified` 不代表內容已查證" in readme_text
    assert "內容以 `【待補證】` 開頭標示" not in readme_text


def test_readme_does_not_certify_mismatched_historical_receipt(readme_text):
    sample = ROOT / "output/main-flow-2026-07-24T061023Z"
    receipt = json.loads((sample / "delivery_manifest.json").read_text(encoding="utf-8"))
    actual = hashlib.sha256((sample / "real_note.訂正稿.md").read_bytes()).hexdigest()
    expected = receipt.get("output_content_hash") or receipt["content_hash"]
    if actual[:len(expected)] != expected:
        assert "歷史樣本的雜湊與回執不一致" in readme_text
        assert "不能作為已驗證交付" in readme_text


def test_readme_evidence_command_has_explicit_file_encoding(readme_text):
    """實際執行唯讀範例；未指定編碼在任何平台都視為錯誤。"""
    command = next(
        line for line in readme_text.splitlines()
        if line.startswith("python3 -c ") and "binding_report.json" in line
    )
    result = subprocess.run(
        [sys.executable, "-X", "warn_default_encoding", "-W", "error::EncodingWarning",
         *shlex.split(command)[1:]],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
