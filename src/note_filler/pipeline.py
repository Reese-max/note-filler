from __future__ import annotations

import logging

from .audit import audit_event
from .parse import parse_note                 # T2
from .domain import detect_domain              # T3
from .questions import generate_questions      # T4
from .gap import detect_gaps                   # T5
from .retrieve import retrieve_for_gap          # T9
from .write import write_supplement            # Q3
from .verify import cross_validate            # T10
from .knowledge.law_citation_check import check_law_citations   # T8
from .correction import assemble_correction       # T12

logger = logging.getLogger(__name__)


def require_non_empty_note_product(correction, *, source: object = "pipeline") -> None:
    """硬性產出檢查：補齊流程完成後必須有至少一份可追溯、非空實際筆記內容。

    通過條件：至少一個 original 或 supplement 段的 text 去空白後非空。
    失敗條件（表面成功但無成品）：
      - 無 segments / 全文與段皆空白
      - 僅空白段、無實質筆記文字（等同空白或僅稽核摘要）
    失敗時寫 note_product_empty 稽核事件並 raise RuntimeError（含明確原因）。
    """
    segments = list(getattr(correction, "segments", None) or [])
    note_types: list[str] = []
    for seg in segments:
        text = getattr(seg, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        stype = getattr(seg, "type", None)
        if stype in ("original", "supplement"):
            note_types.append(stype)

    if note_types:
        return

    original = getattr(correction, "original", None)
    full_text = ""
    if original is not None:
        full_text = (getattr(original, "full_text", None) or "").strip()
    data_id = getattr(original, "source_path", None) if original is not None else source
    if data_id is None or data_id == "":
        data_id = source

    if not segments and not full_text:
        reason = "結果為空白（無任何 original/supplement 段與原文）"
    elif not full_text:
        reason = "結果無實質筆記內容（空白段或僅稽核摘要）"
    else:
        # full_text 有值但未進入任何非空 original/supplement 段 → 組裝/轉送缺口
        reason = "原文未轉送為可追溯筆記段（僅有內部狀態/稽核、無成品段）"

    audit_event(
        logger,
        "note_product_empty",
        data_id,
        reason=reason,
        segment_count=len(segments),
        outcome="failed",
    )
    raise RuntimeError(
        f"補齊流程完成但未產生非空實際筆記：{reason}；拒絕視為成功"
    )


def require_traceable_note_product(correction, *, source: object = "pipeline") -> None:
    """逐段確認成品可回指原始輸入、實際來源 ID 或 gap 處理紀錄。"""
    errors: list[str] = []
    paragraphs = {
        paragraph.idx: paragraph
        for paragraph in getattr(getattr(correction, "original", None), "paragraphs", ())
    }
    source_path = getattr(getattr(correction, "original", None), "source_path", None)

    for index, seg in enumerate(getattr(correction, "segments", ())):
        if not isinstance(getattr(seg, "text", None), str) or not seg.text.strip():
            continue
        refs = getattr(seg, "traceability", None) or []
        if seg.type == "original":
            paragraph = paragraphs.get(seg.anchor_idx)
            expected = {
                "kind": "original_input",
                "id": source_path,
                "paragraph_idx": seg.anchor_idx,
            }
            if paragraph is None or seg.text != paragraph.text or refs != [expected]:
                errors.append(f"segment[{index}] original_input 對應失敗")
            continue

        source_ids = [item.id for item in seg.sources]
        if source_ids:
            expected = [{"kind": "source", "id": source_id} for source_id in source_ids]
            if (
                refs != expected
                or not all(isinstance(source_id, str) and source_id.strip() for source_id in source_ids)
            ):
                errors.append(f"segment[{index}] source ID 對應失敗")
        elif (
            seg.confidence != "pending_evidence"
            or len(refs) != 1
            or not isinstance(refs[0], dict)
            or refs[0].get("kind") != "processing_record"
            or not refs[0].get("id")
            or not refs[0].get("question")
            or refs[0].get("outcome") != seg.confidence
        ):
            errors.append(f"segment[{index}] processing_record 對應失敗")

    if errors:
        audit_event(
            logger,
            "note_traceability_failed",
            source,
            errors=errors,
            outcome="failed",
        )
        raise RuntimeError(f"成品筆記來源追溯驗證失敗：{'；'.join(errors)}")


def run_pipeline(path, llm, twinkle, law):
    """串 parse→domain→questions→gaps→(每 gap)retrieve→write→cross_validate→assemble。
    每個 gap:傳 law+llm 給 retrieve_for_gap 啟用法條 Level A;寫作產 written;
    validations 只跑實際引用(used)之來源。law 領域對補充段再跑 check_law_citations。
    回傳 CorrectionDoc。補齊完成後硬性檢查至少一份非空實際筆記，否則失敗。
    """
    doc = parse_note(path)                                  # T2
    domain = detect_domain(doc.full_text, llm)             # T3(1 次 llm.complete)
    questions = generate_questions(doc.full_text, domain, llm)  # T4(1 次 llm.complete)
    gaps = detect_gaps(questions, doc.full_text, llm)      # T5(1 次 llm.complete)

    retrieved: dict[str, list] = {}
    written: dict = {}
    validations: dict = {}
    for gap in gaps:                                       # 只對 partial/missing gap(T5 已過濾)
        sources = retrieve_for_gap(gap, domain, twinkle, law, llm)  # T9(law+llm 啟用 Level A)
        w = write_supplement(gap, sources, llm)            # Q3(寫出補充,解析 [^n])
        used = [s for s in sources if s.id in w.used_source_ids]
        omitted_ids = [s.id for s in sources if s.id not in w.used_source_ids]
        if omitted_ids:
            audit_event(
                logger,
                "sources_not_forwarded_to_validation",
                gap.question,
                level=logging.INFO,
                source_ids=omitted_ids,
                reason="not actually cited by generated supplement",
            )
        retrieved[gap.question] = sources
        written[gap.question] = w
        validations[gap.question] = cross_validate(gap.question, used)  # T10(只驗 used)

    correction = assemble_correction(doc, gaps, retrieved, written, validations)  # T12

    if domain == "law":
        _verify_law_citations(correction, law)

    # 硬性產出閘：空白或僅稽核摘要不得表面成功
    require_non_empty_note_product(correction, source=path)
    require_traceable_note_product(correction, source=path)
    return correction


def _verify_law_citations(correction, law):
    """law 領域:對每個補充段跑法規引用檢查;引用之法條在離線庫找不到時,
    保守把該段降為 pending_evidence(C6:只降級、保留不刪,絕不升級)。
    penalty_mismatch 同樣降級,因為罰則金額與法規庫不符時不可聲稱 verified。
    """
    for seg in correction.segments:
        if seg.type != "supplement":
            continue
        findings = check_law_citations(text=seg.text, lookup=law)  # C2:第一參數用 text 名
        missing = [f for f in findings if f.get("kind") == "article_not_found"]
        if missing:
            audit_event(
                logger,
                "law_citation_not_forwarded_as_verified",
                seg.text[:80],
                findings=missing,
                outcome="pending_evidence",
            )
            seg.confidence = "pending_evidence"
        if any(f.get("kind") == "penalty_mismatch" for f in findings):
            logger.warning(
                "penalty_mismatch in segment for '%s': %s",
                seg.text[:80],
                [f["detail"] for f in findings if f.get("kind") == "penalty_mismatch"],
            )
            seg.confidence = "pending_evidence"
