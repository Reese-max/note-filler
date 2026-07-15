from __future__ import annotations

from .parse import parse_note                 # T2
from .domain import detect_domain              # T3
from .questions import generate_questions      # T4
from .gap import detect_gaps                   # T5
from .retrieve import retrieve_for_gap          # T9
from .write import write_supplement            # Q3
from .verify import cross_validate            # T10
from .knowledge.law_citation_check import check_law_citations   # T8
from .correction import assemble_correction       # T12


def run_pipeline(path, llm, twinkle, law):
    """串 parse→domain→questions→gaps→(每 gap)retrieve→write→cross_validate→assemble。
    每個 gap:傳 law+llm 給 retrieve_for_gap 啟用法條 Level A;寫作產 written;
    validations 只跑實際引用(used)之來源。law 領域對補充段再跑 check_law_citations。
    回傳 CorrectionDoc。
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
        retrieved[gap.question] = sources
        written[gap.question] = w
        validations[gap.question] = cross_validate(gap.question, used)  # T10(只驗 used)

    correction = assemble_correction(doc, gaps, retrieved, written, validations)  # T12

    if domain == "law":
        _verify_law_citations(correction, law)

    return correction


def _verify_law_citations(correction, law):
    """law 領域:對每個補充段跑法規引用檢查;引用之法條在離線庫找不到時,
    保守把該段降為 pending_evidence(C6:只降級、保留不刪,絕不升級)。
    """
    for seg in correction.segments:
        if seg.type != "supplement":
            continue
        findings = check_law_citations(text=seg.text, lookup=law)  # C2:第一參數用 text 名
        if any(f.get("kind") == "article_not_found" for f in findings):
            seg.confidence = "pending_evidence"
