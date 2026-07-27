#!/usr/bin/env python
"""adng discovery surveyCommand 入口(2026-07-27)。

發掘器過去只看得到 pytest 輸出與遙測,從未讀過成品筆記——感知侷限使其只提
防錯/量測案。本腳本在 pytest 摘要之外,附上最近成品筆記的節選與庫存統計,
讓 finder 能對「產品本身」提出批評(論點單一視角、延伸閱讀缺失等)。

輸出預算:survey 有字元上限且 USER-SIGNALS/NORTHSTAR 高權重優先,
本腳本 stdout 控制在 ~8KB 內,超出部分由 survey 預算機制截斷(fail-open)。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_NOTES = 1
SAMPLE_LINES = 35  # 中文筆記 ~90 字/行:35 行 ≈ 3.2KB,survey 8KB 預算內留空間給遙測摘要


def pytest_summary() -> str:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", "-m", "not integration", "-q"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=280,
    )
    # survey 總預算 8000 字元:進度 dots 行丟棄,只留失敗行(前 5)與最後統計行
    lines = (proc.stdout or "").strip().splitlines()
    fails = [l for l in lines if l.startswith(("FAILED", "ERROR"))][:5]
    tail = lines[-1:] if lines else []
    return "\n".join(fails + tail)


def latest_notes() -> tuple[list[Path], int]:
    notes = sorted(
        ROOT.glob("output/**/*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return notes[:SAMPLE_NOTES], len(notes)


def main() -> int:
    print("# pytest 摘要")
    try:
        print(pytest_summary())
    except Exception as e:  # 勘查來源各自 fail-open,不互相拖垮
        print(f"(pytest 執行失敗: {e})")

    try:
        picks, total = latest_notes()
        print(f"\n# 成品筆記庫存:output/ 共 {total} 篇 markdown")
        for note in picks:
            lines = note.read_text(encoding="utf-8", errors="replace").splitlines()
            rel = note.relative_to(ROOT)
            print(f"\n# 成品筆記採樣:{rel}(全文 {len(lines)} 行,節選前 {SAMPLE_LINES} 行)")
            print("\n".join(lines[:SAMPLE_LINES]))
    except Exception as e:
        print(f"(筆記採樣失敗: {e})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
