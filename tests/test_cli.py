"""CLI(__main__)測試:輸入展開 + 單檔輸出命名/格式/計數(stub 掉 pipeline)。"""

from __future__ import annotations

from dataclasses import dataclass

from note_filler import __main__ as cli


def test_iter_inputs_expands_dir_filters_suffix_and_dedups(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_text("x", encoding="utf-8")
    (tmp_path / "c.pdf").write_text("x", encoding="utf-8")  # 應被濾掉
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.txt").write_text("x", encoding="utf-8")

    # 資料夾遞迴 + 明確指定 a.txt(重複) → 去重
    got = cli._iter_inputs([str(tmp_path), str(tmp_path / "a.txt")])
    names = sorted(p.name for p in got)
    assert names == ["a.txt", "b.docx", "d.txt"]  # c.pdf 濾掉、a.txt 不重複


@dataclass
class _Seg:
    type: str
    confidence: str = "verified"


class _Doc:
    segments = [
        _Seg("original"),
        _Seg("supplement", "verified"),
        _Seg("supplement", "pending_evidence"),
    ]


def test_process_file_writes_md_and_counts(tmp_path, monkeypatch):
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _Doc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n內容")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    dest = tmp_path / "note.訂正稿.md"
    assert dest.exists() and dest.read_text(encoding="utf-8").startswith("# 訂正稿")
    assert r["supplements"] == 2 and r["verified"] == 1
    assert r["output"] == str(dest)


def test_process_file_json_format_and_outdir(tmp_path, monkeypatch):
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    out = tmp_path / "結果"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _Doc())
    monkeypatch.setattr(cli, "to_json", lambda doc: {"ok": True})

    r = cli.process_file(note, None, None, None, out_dir=out, fmt="json")

    dest = out / "note.訂正稿.json"
    assert dest.exists() and '"ok": true' in dest.read_text(encoding="utf-8")
    assert r["output"] == str(dest)
