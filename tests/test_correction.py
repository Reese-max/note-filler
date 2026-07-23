# tests/test_correction.py
from note_filler.correction import assemble_correction
from note_filler.parse import Document, Paragraph      # T2
from note_filler.gap import Gap                         # T5
from note_filler.retrieve.models import Source                 # T6
from note_filler.verify import Validation              # T10
from note_filler.write import WrittenSupplement        # Q3


def _doc(texts):
    paras = tuple(Paragraph(idx=i, text=t) for i, t in enumerate(texts))
    return Document(source_path="x.docx", paragraphs=paras, full_text="\n".join(texts))


def _src(sid, title, url, level="A"):
    return Source(
        id=sid, title=title, url=url, level=level,
        content=f"{title} 記錄全文", fetched_date="2026-07-15",
        doc_date=None, distance=0.4,
    )


def test_original_segments_verbatim_and_immutable():
    """原文段逐字全等輸入,順序/段數不變,confidence=verified。"""
    texts = ["行政程序法第92條規定行政處分之定義。", "第二段原始筆記內容,一字不改。"]
    doc = _doc(texts)
    cd = assemble_correction(doc, gaps=[], retrieved={}, written={}, validations={})
    originals = [s for s in cd.segments if s.type == "original"]
    assert [s.text for s in originals] == texts          # 逐字全等(immutable)
    assert [s.anchor_idx for s in originals] == [0, 1]   # anchor = 原段 idx
    assert all(s.confidence == "verified" for s in originals)
    assert all(s.sources == [] for s in originals)
    assert cd.original is doc                             # 原 Document 原封帶回


def test_written_two_independent_a_verified_only_used_sources():
    """written 引用 2 個獨立 A → verified,且 segment.sources 只含那 2 個。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="原文未提及")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    s2 = _src("2", "訴願法第90條", "https://law.moj.gov.tw/b", level="A")
    retrieved = {q: [s1, s2]}
    written = {q: WrittenSupplement(text="訴願期間為30日[^1],逾期不受理[^2]。",
                                    used_source_ids=["1", "2"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"
    assert [s.id for s in sup.sources] == ["1", "2"]      # 只掛 used 的 2 個


def test_pending_evidence_written_empty_sources():
    """written 為【待補證】→ pending_evidence 且 sources 空。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="原文未提及")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    retrieved = {q: [s1]}
    written = {q: WrittenSupplement(text="【待補證】現有來源未涵蓋訴願期間。",
                                    used_source_ids=[])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"
    assert sup.sources == []


def test_retrieved_five_but_only_two_cited():
    """retrieved 有 5 個但只引用 2 個 → segment 只掛那 2 個。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="")
    srcs = [_src(str(i), f"來源{i}", f"https://law.moj.gov.tw/{i}", level="A")
            for i in range(1, 6)]
    retrieved = {q: srcs}
    written = {q: WrittenSupplement(text="論點一[^2],論點二[^4]。",
                                    used_source_ids=["2", "4"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert [s.id for s in sup.sources] == ["2", "4"]
    assert sup.confidence == "verified"                  # 2 個獨立 A


def test_single_a_used_source_verified():
    """引用 1 個 level A(一手源即 grounded)→ verified。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="partial", reason="僅片段")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    retrieved = {q: [s1]}
    written = {q: WrittenSupplement(text="訴願期間為30日[^1]。", used_source_ids=["1"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"
    assert [s.id for s in sup.sources] == ["1"]


def test_three_articles_same_law_same_url_verified():
    """引 3 條同法《行政程序法》93/94/96(level A、url 相同、id/title 不同)→ verified。
    先前 url 相同被誤標 pending 的案例:一手法條原文即定論。
    """
    doc = _doc(["行政處分之定義。"])
    q = "附款相關規定?"
    gap = Gap(question=q, status="missing", reason="")
    url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055"
    s1 = _src("1", "行政程序法第93條", url, level="A")
    s2 = _src("2", "行政程序法第94條", url, level="A")
    s3 = _src("3", "行政程序法第96條", url, level="A")
    retrieved = {q: [s1, s2, s3]}
    written = {q: WrittenSupplement(text="甲[^1],乙[^2],丙[^3]。",
                                    used_source_ids=["1", "2", "3"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"


def test_two_distinct_b_verified():
    """引 2 個不同 level B(id 不同、無 A)→ verified(規則二)。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="")
    s1 = _src("1", "學說甲", "https://b.example/1", level="B")
    s2 = _src("2", "學說乙", "https://b.example/2", level="B")
    retrieved = {q: [s1, s2]}
    written = {q: WrittenSupplement(text="甲[^1],乙[^2]。", used_source_ids=["1", "2"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"


def test_single_b_no_a_pending():
    """引 1 個 level B、無 A → pending_evidence。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="partial", reason="僅片段")
    s1 = _src("1", "學說甲", "https://b.example/1", level="B")
    retrieved = {q: [s1]}
    written = {q: WrittenSupplement(text="學說主張如下[^1]。", used_source_ids=["1"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"
    assert [s.id for s in sup.sources] == ["1"]


def test_single_c_used_source_verified():
    """引 1 個 level C(官方/標準組織一手,如 owasp.org/NIST/CVE)→ verified。"""
    doc = _doc(["資安筆記。"])
    q = "XSS 防護?"
    gap = Gap(question=q, status="missing", reason="")
    s1 = _src("1", "OWASP Top 10", "https://owasp.org/x", level="C")
    retrieved = {q: [s1]}
    written = {q: WrittenSupplement(text="應做輸出編碼[^1]。", used_source_ids=["1"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"


def test_single_d_used_source_pending():
    """引 1 個 level D、無其他 → pending_evidence(單一二手不算定論)。"""
    doc = _doc(["資安筆記。"])
    q = "XSS 防護?"
    gap = Gap(question=q, status="partial", reason="僅片段")
    s1 = _src("1", "部落格摘要", "https://blog.example/d", level="D")
    retrieved = {q: [s1]}
    written = {q: WrittenSupplement(text="某部落格主張[^1]。", used_source_ids=["1"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"


def test_two_distinct_d_verified():
    """引 2 個相異 level D(id 不同)→ verified(多源佐證,規則三不限 level)。"""
    doc = _doc(["資安筆記。"])
    q = "XSS 防護?"
    gap = Gap(question=q, status="missing", reason="")
    s1 = _src("1", "部落格甲", "https://blog.example/1", level="D")
    s2 = _src("2", "論壇乙", "https://forum.example/2", level="D")
    retrieved = {q: [s1, s2]}
    written = {q: WrittenSupplement(text="甲[^1],乙[^2]。", used_source_ids=["1", "2"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"


def test_anchor_picks_keyword_overlap():
    doc = _doc(["訴願程序相關規定。", "完全無關的天氣內容。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="")
    written = {q: WrittenSupplement(text="補充內容。", used_source_ids=[])}
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.anchor_idx == 0        # 與「訴願」重疊之段


def test_anchor_none_when_no_overlap():
    doc = _doc(["天氣晴朗適合出遊。"])
    q = "ABC XYZ?"
    gap = Gap(question=q, status="missing", reason="")
    written = {q: WrittenSupplement(text="補充內容。", used_source_ids=[])}
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.anchor_idx is None


def test_missing_written_entry_is_trackable_and_logged(caplog):
    """gap 問題不在 written 時不得靜默空字串:須 warning +【待補證】+ pending_evidence。

    對照 docs/silent-data-loss-audit.md #1:written.get(q) 為 None 時先前以
    text=\"\" / sources=[] 產生補充段且無 log,屬高風險靜默資料遺失。
    """
    import logging

    from note_filler.correction import MISSING_WRITTEN_TEXT

    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="原文未提及")
    with caplog.at_level(logging.WARNING, logger="note_filler.correction"):
        cd = assemble_correction(
            doc, gaps=[gap], retrieved={}, written={}, validations={}
        )
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.text == MISSING_WRITTEN_TEXT
    assert sup.text.startswith("【待補證】")
    assert "written" in sup.text
    assert sup.confidence == "pending_evidence"
    assert sup.sources == []
    assert any(
        "written" in rec.message and "pending_evidence" in rec.message
        for rec in caplog.records
        if rec.levelno >= logging.WARNING
    ), "缺 written 時應有 warning 告警,不得靜默吞掉"
