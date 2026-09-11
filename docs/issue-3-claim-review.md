# Issue #3 — 主張級 Verify／Accept／Reject 審查佇列與決策履歷（設計）

Design deliverable for `Reese-max/note-filler#3`。
evidence 已存在（`argument_id / citation_spans / source_ids /
traceability`）；缺的是**持久化的 per-claim 審查決策**。

## 1. `ReviewDecision` ledger

```jsonc
{
  "decisionId": "rd_<ulid>",
  "argumentId": "arg_...",
  "decision": "ACCEPTED | REJECTED | NEEDS_MORE_EVIDENCE | EDITED_ACCEPTED",
  "reasonCode": "source_not_supporting | out_of_scope | duplicate | needs_primary_source | manual_edit",
  "note": "free-text",
  "reviewedAt": "...",
  "reviewerLabel": "local-operator",       // MVP 不做帳號系統
  "claimHash": "sha256(claim text)",
  "evidenceBundleHash": "sha256(source+citation hashes)",
  "previousDecision": "rd_... | null"      // 重審鏈
}
```

## 2. Claim review state（supplement/argument 層）

`UNREVIEWED → ACCEPTED | REJECTED | NEEDS_MORE_EVIDENCE | EDITED_ACCEPTED`

`STALE_REVIEW`：claim text、citation span、source content hash 或
validation contract 任一變更 → 舊 ACCEPTED 不沿用，自動標 stale 要求重審。

**`confidence=verified` 只是系統 evidence gate，不等於人類 ACCEPTED。**

## 3. Review card 內容

- claim text
- citation spans / source fragments
- source level、URL、文件日期/擷取日
- 系統 confidence / pending reason
- 多來源時各來源標 `supports | conflicts | context_only | unresolved`
  （deterministic/cross_validate 產生，不由 LLM 自評當結論）

## 4. Export gate（明確 mode）

| Mode | 內容 |
|---|---|
| `review-draft` | 含 UNREVIEWED / pending 標記 |
| `accepted-only` | 只輸出原稿 + 有效的 ACCEPTED/EDITED_ACCEPTED |

`REJECTED / STALE_REVIEW / NEEDS_MORE_EVIDENCE` 永不混入正式稿。

## 5. Review queue UX

結果頁新增：待審數量、pending/stale/rejected/accepted 篩選、
「下一個待審」、accept/reject/needs-evidence 按鈕、reason-code 快捷碼。

## 6. 不做什麼

- 不做多人 SaaS / DMS integration——先把單機 review 做完整。
- 不放寬「原稿不可變、無來源不進正文」的既有安全契約。
- 不讓 LLM 自評成為正式結論。
