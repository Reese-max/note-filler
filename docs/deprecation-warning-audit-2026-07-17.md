# Deprecation Warning Audit — 2026-07-17

## 測試指令

```
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -m "not integration"
```

pyproject.toml `addopts` 已內建：
```
-W error::DeprecationWarning -W error::PendingDeprecationWarning
```

## 測試環境

- Python 3.11.9
- pytest 9.1.1
- anyio 4.14.2

## 結果

```
102 passed, 8 deselected in 0.92s
```

- 102 tests 通過
- 8 tests 被 `-m "not integration"` 跳過（整合測試）
- **零 DeprecationWarning**
- **零 PendingDeprecationWarning**

## 結論

所有非整合測試在 deprecation warning 視為 error 的模式下全數通過，無任何 deprecation 風險。
