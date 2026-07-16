# 即將失效 API 盤點報告

## 盤點目標

排查所有測試中直接或間接依賴以下即將失效 API 的用法：

1. `fastapi.testclient.TestClient`
2. `starlette.testclient.TestClient`
3. 受 httpx 版本升級影響的 client 初始化參數（如 `app=` 直接傳入 `httpx.AsyncClient`）

## 盤點範圍

- `tests/` 下全部 22 個測試檔 + `conftest.py`（共 23 個 `.py` 檔）
- `src/note_filler/` 下全部 22 個原始碼檔
- `app/server.py`（FastAPI 應用本體）

## 盤點結果

### 1. `fastapi.testclient.TestClient`

**影響範圍：零。** 全 repo 無任何檔案 import 或使用 `fastapi.testclient.TestClient`。

- grep `TestClient` across all `*.py`：0 命中
- grep `fastapi.testclient` across all `*.py`：0 命中

### 2. `starlette.testclient.TestClient`

**影響範圍：零。** 全 repo 無任何檔案 import 或使用 `starlette.testclient.TestClient`。

- grep `starlette.testclient` across all `*.py`：0 命中

### 3. httpx client 初始化參數

`tests/conftest.py:8-9` 是全 repo 唯一使用 `httpx` 的位置：

```python
transport = httpx.ASGITransport(app=server.app)
async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
```

**已採用 httpx 0.27+ 推薦的 `ASGITransport` 模式**，而非已移除的 `httpx.AsyncClient(app=...)` 語法。此寫法與 httpx 0.28.1（目前安裝版本）完全相容，無任何 deprecated 參數。

### 4. 間接依賴排查

| 檔案 | HTTP client 用途 | 是否安全 |
|---|---|---|
| `tests/conftest.py` | `httpx.ASGITransport` + `httpx.AsyncClient` | ✅ 已是現代寫法 |
| `tests/test_server.py` | 透過 `async_client` fixture 呼叫 | ✅ 間接使用，無問題 |
| `tests/test_web.py` | 純單元測試，無 HTTP client | ✅ 不受影響 |
| `tests/test_e2e_acceptance.py` | 直接呼叫 pipeline，無 HTTP client | ✅ 不受影響 |
| 其餘 19 個 test_*.py | 無 HTTP client 使用 | ✅ 不受影響 |

## 驗證證據

### pyproject.toml 的 deprecation 閘

```toml
addopts = "-p no:asyncio -W error::DeprecationWarning -W error::PendingDeprecationWarning"
```

任何 `DeprecationWarning` 或 `PendingDeprecationWarning` 會直接導致 pytest FAIL。

### 實測輸出（2026-07-17）

```
Python:    3.11.9
pytest:    9.1.1
httpx:     0.28.1
fastapi:   0.139.2
starlette: 1.3.1

$ python -X utf8 -m pytest -m "not integration" -x -v
====================== 102 passed, 8 deselected in 0.86s =======================
```

102 passed + `-W error::DeprecationWarning` = 零 deprecation warning。

`-Wd`（顯示所有警告）模式下同樣零 warnings summary。

## 結論

**不需要任何程式碼變更。** 本專案的測試已完全避開所有即將失效的 API：

- 不使用 `fastapi.testclient.TestClient`
- 不使用 `starlette.testclient.TestClient`
- `httpx.AsyncClient` 初始化已採用 `ASGITransport` 模式（httpx 0.28+ 兼容）
- `pyproject.toml` 的 `-W error` 閘確保未來任何 deprecated 使用會立即暴露
