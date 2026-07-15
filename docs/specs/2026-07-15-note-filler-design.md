# 筆記補齊(Note-Filler)設計 Spec

- 日期:2026-07-15
- 狀態:草案(待使用者複審)
- 開發方式:autodev-ng backlog 驅動 + codex-spark 引擎
- 專案路徑:`D:/Users/Administrator/Desktop/筆記補齊`

---

## 1. 目標與一句話定義

輸入一份既有筆記(Word/純文字)→ AI 自主找出知識缺口 → 檢索台灣官方一手來源 → 交叉驗證 → 產出一份「**訂正稿**」:原文完整保留、補進去的內容就地標記、每個補充點掛一手來源註腳。

與坊間工具的差異:不是「一句話生成新文件」,而是「**輸入既有筆記、原地補洞、每筆補充都開得到一手源**」。

## 2. 範圍

### MVP(本 spec 聚焦)
- 領域:**法律 / 行政 / 國考**(twinkle-hub + 官方結構化源已覆蓋,零外部搜尋依賴)
- 輸入:單份 Word / txt
- 研究層 LLM:**grok**(本機 proxy `http://127.0.0.1:8318/v1`,model `grok-4.3`)
- 部署:本機 on-demand,需要時喚起(非 24/7)
- 產出:訂正稿(結構化 JSON → web 雙欄檢視 + 可導出)

### 後續(不在 MVP)
- 資安/IT/一般學科的**開放網路研究**(需 search backend,如本機 SearXNG 或 Tavily)
- 批次補齊多份
- 多用戶 / 帳號 / 計費 / 對外部署
- PDF OCR、完整反爬
- 接其他模型 API(grok 之外)

## 3. 與「公文ai agent」的關係(復用策略)

**決策:獨立新專案,選擇性移植其模組**(不硬 import 整個成熟 repo,避免耦合到一個有 auto-engineer 在跑、持續變動的上游)。

新專案語言:**Python**(對齊可復用資產:litellm / 官方源 fetchers / LawVerifier)。

### 從公文ai agent 移植的模組(來源 `D:/Users/Administrator/Desktop/公文ai agent`)

| 移植項 | 上游路徑 | 用途 |
|---|---|---|
| 官方源 fetchers(法規/立法院/司法/大法官解釋/考試院/公報) | `src/knowledge/fetchers/` | 法律/行政/國考的一手源檢索層 |
| twinkle-hub MCP 接取 | `src/knowledge/mcp_law_source.py` | 立法院議案等即時查詢(Level B) |
| LawVerifier(法規驗證/防幻覺法條) | `src/knowledge/realtime_lookup.py`、`law_citation_check.py`、`law_lookup.py` | 補充內容引用的法條逐條比對 |
| cite「無來源不得新增」閘 | `src/agents/writer/cite.py`、`src/document/citation_formatter.py` | 無依據→留 `【待補依據】`不新增;`[^n]` 註腳 |
| 來源分級 A-D + 新鮮度 | `src/agents/fact_checker/`、`corpus_provenance.py`、`staleness.py` | 來源分級與資料日期 |
| 引用/事實查核 Agent(MVP 只取關鍵兩個) | `src/agents/citation_checker/`、`src/agents/fact_checker/` | 品質閘執行 |

**不移植**(MVP 不需要):ChromaDB 向量庫、六 Agent 全套審查迭代、FastAPI 大殼、docx 生成全套、graph/LangGraph、open_notebook。

**移植紀律**:每個移植的模組在新 repo 記錄來源 commit hash(便於日後對照上游更新);移植即精簡,只留 MVP 路徑。

## 4. 系統架構

```
輸入筆記(.docx/.txt)
  → [解析] 純文字 + 段落結構(保留原文 immutable)
  → [Topic 抽取] LLM 判定主題與領域(法律/行政/國考)
  → [研究問題生成] LLM 依主題生「該主題應涵蓋的關鍵問題」清單
  → [Gap 偵測] 研究問題 vs 現有筆記內容 → 缺口清單  ← 自建①
  → [分領域檢索] 每個缺口 → 官方源 fetchers + twinkle-hub(移植)
  → [交叉驗證] 每 claim 湊 ≥2 獨立一手源 / 衝突偵測 / 來源分級 / 標日期
  → [引用強制] 無來源的補充 → 程式擋下(移植 cite 閘)
  → [訂正稿組裝] 原文 + 標記補充段落 + 註腳  ← 自建②
  → 結構化 JSON → Web 雙欄檢視 / 導出
```

## 5. 自建兩塊(公文ai agent 沒有的)

### ① Gap 偵測模組
- 輸入:研究問題清單 + 現有筆記全文
- 作法:對每個研究問題,用 LLM 判定「筆記是否已充分涵蓋」(已涵蓋/部分/缺漏),部分與缺漏者進補充佇列;附「缺什麼」的一句話理由
- 產出:缺口清單 `[{question, status, reason}]`
- 註:上游 `classification.py`/`strategy.py` 只做需求分析,無 gap detection,需新寫

### ② 訂正稿資料結構與組裝
- 段落陣列,每段:
  ```json
  {
    "type": "original | supplement",
    "text": "...",
    "anchor": "接在哪個原文段之後(supplement 才有)",
    "sources": [{"id","title","url","level","fetched_date","doc_date"}],
    "confidence": "verified | pending_evidence"
  }
  ```
- 原文段 `immutable`;補充是 overlay,不改動原文一字(落實品質閘「保留原稿以差異顯示」)
- render:web 雙欄(左原稿、右訂正稿,補充高亮 + hover 看來源);導出 Markdown/docx

## 6. 8 品質閘 → 程式硬閘門

| 品質閘 | 落地 |
|---|---|
| 無來源不得新增 | 補充段 `sources` 為空 → 不進正文,降級為 `pending_evidence` |
| 優先一手源 | 來源分級 A-D,僅 A/B 可當主證據 |
| 重要敘述 ≥2 源 | 交叉驗證計數 <2 → 標 `pending_evidence`,不入正文 |
| 禁引用搜尋摘要 | fetcher 只收「開得到原文的條文/URL」,摘要頁黑名單 |
| 保留原稿以差異顯示 | 原文段 immutable,補充 overlay |
| 衝突偵測 | 同 claim 多源矛盾 → 標記並列,不自動選邊 |
| 標資料日期 | 每 source 存 `fetched_date` + `doc_date` |
| 來源分級 A-D | fetcher 依來源型別自動分級(法規原文=A) |

## 7. LLM 接法

- 研究層(topic/研究問題/gap 判定):grok proxy `http://127.0.0.1:8318/v1`,任意 key,model `grok-4.3`
- 用 OpenAI 相容 client 直打;`reasoning_effort` 合法值 `minimal|low|medium|high|xhigh`
- port 不通才手動拉:`hermes.exe proxy start --provider xai --port 8318`
- 抽象成單一 LLM client 介面,日後接其他 API 只換 base_url/model

## 8. UI(MVP 薄殼)
- 最小 web:上傳筆記 → 跑 → 雙欄檢視訂正稿(補充高亮 + hover 來源)→ 導出按鈕
- 技術先簡:單頁 + 後端一個 endpoint 跑 pipeline;不做帳號/歷史管理
- 框架選型待實作時定(FastAPI 薄殼或更輕的即可),不預先過度搭骨架

## 9. 開發方式(autodev-ng + codex-spark)
- 筆記補齊目錄需 `git init`(codex-spark 成功硬綁「新 commit」,產品目錄必須是 git repo)
- 加 `configs/note-filler.json`(projectPath / backlogFile / dataDir + engine=codex-spark)
- backlog 任務由**使用者**逐條加(autodev-ng 鐵律:不自生任務)
- adng daemon/web 維持 Disabled;本機 on-demand `run-once` 即可

## 10. MVP 不做清單(YAGNI)
- ❌ 開放網路研究(第二階段)
- ❌ 批次 / 多用戶 / 計費 / 對外
- ❌ ChromaDB 向量檢索、六 Agent 全套、PDF OCR
- ❌ grok 以外的模型

## 11. 風險與 open items
1. **移植耦合**:上游 fetchers 可能依賴上游其他模組;移植時需連帶處理依賴或做精簡替身。移植前先實測單一 fetcher 可獨立跑。
2. **grok 研究能力**:grok 做 gap 判定/研究問題生成的品質未實測；第一個 backlog 任務應是「用一份真實筆記端到端 smoke test」驗證可用度。
3. **twinkle-hub 覆蓋度**:國考考古題/大法官解釋等覆蓋是否足夠支撐「≥2 一手源」,需以真實筆記驗證。
4. **交叉驗證的「≥2 獨立源」**:上游只有語意相似度查核,非顯式雙源;此為自建重點,需定義「獨立」判準(不同機關/不同文件)。

## 12. 驗收標準(MVP done 的定義)
- 給一份真實的法律/行政/國考筆記,能產出訂正稿,且:
  - 每個補充段落都有 ≥1 個 A/B 級一手源註腳,否則標 `pending_evidence`
  - 原文一字未改(diff 只顯示新增)
  - 補充的法條引用經 LawVerifier 比對無幻覺
  - web 雙欄可檢視 + 可導出
- 有一條端到端自動測試涵蓋上述
