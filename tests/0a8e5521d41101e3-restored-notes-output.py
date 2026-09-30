"""GOAL 0a8e5521d41101e3 驗收入口：非空實際筆記硬性產出閘。

本檔供 GOAL 明確路徑執行；實作測試在 test_note_product_gate.py（預設套件可收集）。
"""

from test_note_product_gate import (  # noqa: F401
    test_process_file_rejects_empty_product_stub_with_reason,
    test_process_file_success_requires_non_empty_body,
    test_require_non_empty_accepts_original_or_supplement,
    test_require_non_empty_emits_audit_event,
    test_require_non_empty_rejects_blank_product_with_reason,
    test_require_non_empty_rejects_whitespace_or_audit_only_with_reason,
    test_run_pipeline_empty_input_and_no_gaps_fails_product_gate,
    test_run_pipeline_produces_non_empty_traceable_notes,
)
