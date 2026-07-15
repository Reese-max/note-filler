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


def test_single_used_source_stays_pending():
    """只引用 1 個來源(不足 2 獨立)→ pending_evidence。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="partial", reason="僅片段")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    retrieved = {q: [s1]}
    written = {q: WrittenSupplement(text="訴願期間為30日[^1]。", used_source_ids=["1"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"
    assert [s.id for s in sup.sources] == ["1"]


def test_two_used_but_same_title_not_independent():
    """used 2 個但 title 相同(url 不同)→ 非獨立 → pending_evidence。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    s2 = _src("2", "訴願法第14條", "https://law.moj.gov.tw/b", level="A")
    retrieved = {q: [s1, s2]}
    written = {q: WrittenSupplement(text="甲[^1],乙[^2]。", used_source_ids=["1", "2"])}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved,
                             written=written, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"


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
