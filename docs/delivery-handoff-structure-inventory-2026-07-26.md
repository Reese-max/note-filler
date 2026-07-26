# 最終回傳值與使用者可見通道交接資料結構盤點

日期：2026-07-26
基準 revision：`ce0d69e3`

## 結論

經盤點，目前**沒有**仍把「本機落盤成功」誤當完成條件的函式。所有相關函式已正確以 `user_visible_content`（即 `r["content"]`）為主完成判定。

## 交接資料結構

### 1. `process_file()` 回傳值

位置：`src/note_filler/__main__.py:172-178`

```python
return {
    "input": str(path),
    "output": str(dest),
    "content": body,        # ← 使用者可見內容
    "supplements": len(supp),
    "verified": ver,
}
```

- `content` 欄位即為 `user_visible_content`，代表完整筆記內容
- 此內容同時用於 stdout 送達與本機落盤

### 2. `main()` 函式的完成判定

位置：`src/note_filler/__main__.py:204-254`

```python
ok = 0
for f in files:
    try:
        r = process_file(f, llm, twinkle, law, out_dir, args.format)
        print(r["content"], flush=True)  # ← 先送達使用者可見內容
        ok += 1                          # ← 送達成功後才計數
        # ...
    except Exception as e:
        # 送達失敗不計入 ok
        # ...

return 0 if ok == len(files) else 1
```

**關鍵邏輯**：
- `ok += 1` 只在 `print(r["content"], flush=True)` **成功執行後**才執行
- 若 stdout 送達失敗（拋出 OSError），會進入 `except` 分支，不會增加 `ok`
- 最終返回值基於 `ok == len(files)`，即只計數成功送達使用者可見內容的檔案

### 3. 使用者可見通道

| 通道 | 資料來源 | 完成條件 |
|---|---|---|
| stdout | `r["content"]` | `print(r["content"], flush=True)` 成功 |
| 本機檔案 | `r["content"]` → `dest.write_text(body)` | 檔案寫入成功且非空 |
| delivery_manifest | `write_delivery_receipt()` | manifest 寫入成功 |

## 驗證測試

### 測試 1：stdout 送達失敗不計入成功

位置：`tests/test_cli.py:187-219`

```python
def test_main_stdout_delivery_failure_is_not_counted_as_success(tmp_path, monkeypatch, capsys):
    # 模擬 stdout 失敗
    def fail_stdout(*args, **kwargs):
        if kwargs.get("file") is None:
            raise OSError("message output unavailable")
        return real_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", fail_stdout)

    code = cli.main([str(note), "-o", str(out), "--db", str(tmp_path / "no.db")])
    captured = capsys.readouterr()

    assert code == 1  # ← 非零返回值
    assert captured.out == ""  # ← stdout 為空
    assert "完成 0/1 檔" in captured.err  # ← ok 未增加
```

### 測試 2：process_file 回傳值包含完整內容

位置：`tests/test_e2e_acceptance_final.py:523-546`

```python
def test_final_note_delivery_not_empty_or_local_only(tmp_path):
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")
    content = r["content"]

    assert content.strip(), "content 為空輸出"
    assert len(content) > 100, "content 內容過短，疑似僅包含路徑或統計"
    assert "行政程序法" in content, "content 缺乏實際筆記內容，疑似僅本機落盤"
```

## 歷史修復記錄

| Commit | 修復內容 |
|---|---|
| `7e6121d` | 將完整訂正稿送至標準輸出，補上 stdout 資料流與失敗計數 |
| `b3f1efc` | 移除錯誤處理中的堆疊暴露，確保送達失敗不暴露堆疊 |

## 結論

**目前沒有尚待修改的函式**。所有完成判定都已正確以 `user_visible_content`（`r["content"]`）為主，而非僅依賴本機落盤成功。

---

## 唯一需要修改的檔案與欄位

**無**。問題已在之前的 commit 中修復完畢。
