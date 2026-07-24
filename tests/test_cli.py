"""CLI(__main__)測試:輸入展開 + 單檔輸出命名/格式/計數(stub 掉 pipeline)。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

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
    text: str = "可追溯筆記內容"


class _Doc:
    segments = [
        _Seg("original", text="原文段落"),
        _Seg("supplement", "verified", text="補充段落 verified"),
        _Seg("supplement", "pending_evidence", text="補充段落 pending"),
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


def test_process_file_delivery_write_failure_does_not_return_success(tmp_path, monkeypatch):
    """digest 已生成但寫出(送達)失敗時,不得回傳成功 dict。

    鎖定失敗語義:pipeline 成功後發送端 OSError 必須向上傳遞,
    不可被吞掉成看似完成的統計結果(L039/L036)。
    """
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _Doc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n內容")

    def _boom_write(self, *args, **kwargs):
        raise OSError("simulated delivery failure: disk full")

    monkeypatch.setattr(Path, "write_text", _boom_write)

    with pytest.raises(OSError, match="delivery failure|disk full"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    # 失敗後不得留下「成功輸出路徑」假象(寫出未完成)
    assert not (tmp_path / "note.訂正稿.md").exists()


def test_process_file_empty_export_body_does_not_return_success(tmp_path, monkeypatch):
    """digest 已生成但匯出體為空時,不得回傳成功 dict。

    鎖定:發送端回傳空結果仍標成功的回歸洞(L035/L036/L039)。
    """
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _Doc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "   \n\t  ")  # 空/空白結果

    with pytest.raises(RuntimeError, match="為空|送達"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    assert not (tmp_path / "note.訂正稿.md").exists()


def test_main_delivery_failure_not_counted_as_success(tmp_path, monkeypatch, capsys):
    """main 批次層:單檔送達失敗不得計入 ok,exit≠0,stderr 含失敗原因。"""
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")

    def _fail_process(*args, **kwargs):
        raise OSError("delivery channel down")

    monkeypatch.setattr(cli, "process_file", _fail_process)
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
    monkeypatch.setattr(cli, "LawLookup", lambda db: None)

    code = cli.main([str(note), "--db", str(tmp_path / "no.db")])
    captured = capsys.readouterr()

    assert code == 1
    assert "✅" not in captured.out
    assert "完成 0/1 檔" in captured.out
    assert "delivery channel down" in captured.err
    assert "OSError" in captured.err


def test_main_partial_delivery_failure_returns_failure(tmp_path, monkeypatch, capsys):
    """批次中任一檔未送達時，即使其他檔成功也不得回傳成功。"""
    notes = [tmp_path / "ok.txt", tmp_path / "empty.txt"]
    for note in notes:
        note.write_text("內容", encoding="utf-8")

    def _process(path, *args, **kwargs):
        if path.name == "empty.txt":
            raise RuntimeError("訂正稿內容為空")
        return {"input": str(path), "output": "ok.md", "supplements": 0, "verified": 0}

    monkeypatch.setattr(cli, "process_file", _process)
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
    monkeypatch.setattr(cli, "LawLookup", lambda db: None)

    code = cli.main([*(str(note) for note in notes), "--db", str(tmp_path / "no.db")])
    captured = capsys.readouterr()

    assert code == 1
    assert "完成 1/2 檔" in captured.out
    assert "訂正稿內容為空" in captured.err


def test_main_missing_token_warns_to_stderr(tmp_path, monkeypatch, capsys):
    """缺 TWINKLE_HUB_TOKEN 時 stderr 警告,twinkle 降級為空,但 pipeline 仍繼續。

    __main__.py:157-158:只 warn 不 abort, Level B 來源降級。
    """
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "process_file", lambda *a, **k: {
        "input": str(note), "output": "ok.md", "supplements": 0, "verified": 0,
    })
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
    monkeypatch.setattr(cli, "LawLookup", lambda db: None)
    # 確保環境變數也不設定
    monkeypatch.delenv("TWINKLE_HUB_TOKEN", raising=False)

    code = cli.main([str(note), "--db", str(tmp_path / "no.db"), "--token", ""])
    captured = capsys.readouterr()

    assert code == 0
    assert "警告" in captured.err
    assert "TWINKLE_HUB_TOKEN" in captured.err
    assert "Level B" in captured.err


def test_main_missing_db_warns_to_stderr(tmp_path, monkeypatch, capsys):
    """缺法條 DB 時 stderr 警告,Level A 查無結果,但 pipeline 仍繼續。

    __main__.py:159-160:只 warn 不 abort, Level A 來源降級。
    """
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "process_file", lambda *a, **k: {
        "input": str(note), "output": "ok.md", "supplements": 0, "verified": 0,
    })
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
    monkeypatch.setattr(cli, "LawLookup", lambda db: None)

    nonexistent_db = str(tmp_path / "nonexistent.db")
    code = cli.main([str(note), "--db", nonexistent_db])
    captured = capsys.readouterr()

    assert code == 0
    assert "警告" in captured.err
    assert "法條 DB 不存在" in captured.err
    assert nonexistent_db in captured.err


def test_main_missing_token_and_db_both_warn(tmp_path, monkeypatch, capsys):
    """同時缺 token 與 DB 時兩條警告都出現,pipeline 仍繼續執行。"""
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "process_file", lambda *a, **k: {
        "input": str(note), "output": "ok.md", "supplements": 0, "verified": 0,
    })
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
    monkeypatch.setattr(cli, "LawLookup", lambda db: None)
    monkeypatch.delenv("TWINKLE_HUB_TOKEN", raising=False)

    nonexistent_db = str(tmp_path / "no_such_db.db")
    code = cli.main([str(note), "--db", nonexistent_db, "--token", ""])
    captured = capsys.readouterr()

    assert code == 0
    assert "TWINKLE_HUB_TOKEN" in captured.err
    assert "法條 DB 不存在" in captured.err
