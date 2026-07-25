"""論點角度覆蓋（angle coverage）：標籤／類型、涵蓋面向、重複／同義判定。

設計目標：
- 每個 argument 明確記錄 angle_type 與 angle_labels
- 可機器讀出 covered_facets（涵蓋哪些不同面向）
- 以 angle_key 判定 exact 重複；以 type + token 重疊判定同義
- 依首次出現保留有效角度，輸出排除結果與筆記層門檻摘要
- 純函式、無 LLM、可 deterministically 重現
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

AngleRelationKind = Literal["unique", "duplicate", "synonym"]

# 角度類型：順序即優先匹配順序（越具體越前）
_ANGLE_TYPE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("definition", ("定義", "何謂", "什麼是", "係指", "如何定義", "意義", "概念")),
    ("limitation", ("限制", "不得", "禁止", "上限", "拘束", "限度")),
    ("requirement", ("要件", "條件", "應具備", "必要條件", "構成")),
    ("effect", ("效力", "效果", "法律效果", "後果", "失效", "生效")),
    ("procedure", ("程序", "流程", "步驟", "如何辦理", "手續", "流程")),
    ("exception", ("例外", "但書", "除外", "不適用")),
    ("comparison", ("比較", "區別", "差異", "對照", "不同")),
    ("application", ("適用", "適用範圍", "案例", "實務", "如何適用")),
)

_VALID_ANGLE_TYPES = frozenset(t for t, _ in _ANGLE_TYPE_RULES) | frozenset({"other"})

# 同義：同 angle_type 且 token Jaccard ≥ 門檻、但 angle_key 不同
_SYNONYM_JACCARD = 0.5

# 筆記只有一個論點時要求一個；兩個以上論點至少保留兩個有效角度。
MIN_EFFECTIVE_ANGLE_COUNT = 2
# exact duplicate 與 synonym 排除後，最多容許一半論點重複。
MAX_DUPLICATE_RATIO = 0.5

_NON_WORD = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)
_CJK_OR_WORD = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")


def classify_angle_type(text: str) -> str:
    """依問題／論點文字關鍵詞判定主角度類型；無命中則 other。"""
    s = (text or "").strip()
    if not s:
        return "other"
    for angle_type, keywords in _ANGLE_TYPE_RULES:
        for kw in keywords:
            if kw in s:
                return angle_type
    return "other"


def normalize_angle_text(text: str) -> str:
    """正規化文字供 angle_key 與同義比對（去標點、小寫、壓空白）。"""
    s = unicodedata.normalize("NFKC", text or "")
    s = s.casefold()
    s = _NON_WORD.sub(" ", s)
    return " ".join(s.split())


def angle_tokens(text: str) -> frozenset[str]:
    """抽取可比對 token（CJK 單字 + 英數字詞）。"""
    return frozenset(_CJK_OR_WORD.findall(normalize_angle_text(text)))


def build_angle_key(angle_type: str, question_or_text: str) -> str:
    """精確重複判定用鍵：type + 正規化文字。"""
    at = angle_type if angle_type in _VALID_ANGLE_TYPES else "other"
    norm = normalize_angle_text(question_or_text)
    return f"{at}:{norm}" if norm else f"{at}:"


def build_angle_coverage(
    *,
    question: str = "",
    argument_text: str = "",
    functional_gap: str = "",
    user_value: str = "",
    angle_type: str | None = None,
    angle_labels: list[str] | None = None,
) -> dict[str, Any]:
    """組出可序列化的 angle_coverage 結構。

    欄位：
      - angle_type: 主角度類型
      - angle_labels: 角度標籤清單（含 type 與必要性面向標籤）
      - covered_facets: 機器可讀面向識別碼
      - angle_key: 精確重複鍵
    """
    seed = (question or "").strip() or (argument_text or "").strip()
    at = (angle_type or "").strip() or classify_angle_type(seed)
    if at not in _VALID_ANGLE_TYPES:
        at = "other"

    labels: list[str] = []
    if angle_labels:
        for lab in angle_labels:
            if isinstance(lab, str) and lab.strip() and lab.strip() not in labels:
                labels.append(lab.strip())
    if at not in labels:
        labels.insert(0, at)

    facets: list[str] = [f"angle:{at}"]
    if (functional_gap or "").strip():
        if "functional_gap" not in labels:
            labels.append("functional_gap")
        facets.append("necessity:functional_gap")
    if (user_value or "").strip():
        if "user_value" not in labels:
            labels.append("user_value")
        facets.append("necessity:user_value")
    if seed:
        facets.append("question")

    key = build_angle_key(at, seed)

    return {
        "angle_type": at,
        "angle_labels": labels,
        "covered_facets": facets,
        "angle_key": key,
    }


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def detect_angle_relation(
    self_index: int,
    coverages: list[dict[str, Any]],
    *,
    synonym_threshold: float = _SYNONYM_JACCARD,
) -> dict[str, Any]:
    """相對整份論點清單判定本論點的角度關係。

    - duplicate: 存在其他論點 angle_key 完全相同
    - synonym: 同 angle_type、不同 key、token Jaccard ≥ 門檻
    - unique: 以上皆非
    若同時命中 duplicate 與 synonym，優先標 duplicate。
    """
    if self_index < 0 or self_index >= len(coverages):
        return {
            "kind": "unique",
            "related_argument_indices": [],
            "duplicate_of": [],
            "synonym_of": [],
        }

    self_cov = coverages[self_index] or {}
    self_key = self_cov.get("angle_key") or ""
    self_type = self_cov.get("angle_type") or "other"
    # 以 angle_key 去 type 前綴後的文字取 token；無則用 labels
    self_norm = self_key.split(":", 1)[1] if ":" in self_key else ""
    self_toks = angle_tokens(self_norm) if self_norm else frozenset(
        self_cov.get("angle_labels") or []
    )

    dup: list[int] = []
    syn: list[int] = []
    for j, other in enumerate(coverages):
        if j == self_index:
            continue
        o_key = (other or {}).get("angle_key") or ""
        o_type = (other or {}).get("angle_type") or "other"
        if self_key and o_key and self_key == o_key:
            dup.append(j)
            continue
        if self_type != o_type or self_type == "other":
            continue
        o_norm = o_key.split(":", 1)[1] if ":" in o_key else ""
        o_toks = angle_tokens(o_norm) if o_norm else frozenset(
            (other or {}).get("angle_labels") or []
        )
        if _jaccard(self_toks, o_toks) >= synonym_threshold:
            syn.append(j)

    if dup:
        kind: AngleRelationKind = "duplicate"
        related = sorted(dup)
    elif syn:
        kind = "synonym"
        related = sorted(syn)
    else:
        kind = "unique"
        related = []

    return {
        "kind": kind,
        "related_argument_indices": related,
        "duplicate_of": sorted(dup),
        "synonym_of": sorted(syn),
    }


def attach_relations(
    coverages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """加上關係、有效角度數及重複排除結果（不修改輸入）。"""
    out: list[dict[str, Any]] = []
    for i, cov in enumerate(coverages):
        base = dict(cov) if cov else {}
        relation = detect_angle_relation(i, coverages)
        earlier_duplicates = [j for j in relation["duplicate_of"] if j < i]
        earlier_synonyms = [j for j in relation["synonym_of"] if j < i]
        if earlier_duplicates:
            related = min(earlier_duplicates)
            reason = "duplicate"
        elif earlier_synonyms:
            related = min(earlier_synonyms)
            reason = "synonym"
        else:
            related = i
            reason = None

        kept_index = (
            out[related]["duplicate_exclusion"]["kept_argument_index"]
            if related < len(out)
            else i
        )
        excluded = reason is not None
        base["relation"] = relation
        base["effective_angle_count"] = 0 if excluded else 1
        base["duplicate_exclusion"] = {
            "excluded": excluded,
            "reason": reason,
            "kept_argument_index": kept_index,
        }
        out.append(base)
    return out


def summarize_angle_coverage(
    coverages_with_relation: list[dict[str, Any]],
) -> dict[str, Any]:
    """整份報告的角度覆蓋量測與門檻摘要（機器可讀）。"""
    types: list[str] = []
    facets_union: list[str] = []
    dup_pairs: list[list[int]] = []
    syn_pairs: list[list[int]] = []
    seen_dup: set[tuple[int, int]] = set()
    seen_syn: set[tuple[int, int]] = set()

    for i, cov in enumerate(coverages_with_relation):
        if cov.get("effective_angle_count") == 1:
            at = cov.get("angle_type") or "other"
            if at not in types:
                types.append(at)
            for f in cov.get("covered_facets") or []:
                if f not in facets_union:
                    facets_union.append(f)
        rel = cov.get("relation") or {}
        for j in rel.get("duplicate_of") or []:
            pair = tuple(sorted((i, int(j))))
            if pair[0] != pair[1] and pair not in seen_dup:
                seen_dup.add(pair)
                dup_pairs.append([pair[0], pair[1]])
        for j in rel.get("synonym_of") or []:
            pair = tuple(sorted((i, int(j))))
            if pair[0] != pair[1] and pair not in seen_syn:
                seen_syn.add(pair)
                syn_pairs.append([pair[0], pair[1]])

    argument_count = len(coverages_with_relation)
    effective_count = sum(
        cov.get("effective_angle_count") == 1
        for cov in coverages_with_relation
    )
    excluded_count = argument_count - effective_count
    duplicate_ratio = excluded_count / argument_count if argument_count else 0.0
    required_count = min(MIN_EFFECTIVE_ANGLE_COUNT, argument_count)
    sufficient = effective_count >= required_count
    acceptable_duplicates = duplicate_ratio <= MAX_DUPLICATE_RATIO

    return {
        "unique_angle_types": types,
        "covered_facets_union": facets_union,
        "duplicate_pairs": sorted(dup_pairs),
        "synonym_pairs": sorted(syn_pairs),
        "argument_count_with_angles": argument_count,
        "effective_angle_count": effective_count,
        "excluded_angle_count": excluded_count,
        "duplicate_ratio": duplicate_ratio,
        "required_effective_angle_count": required_count,
        "max_duplicate_ratio": MAX_DUPLICATE_RATIO,
        "has_sufficient_angles": sufficient,
        "has_acceptable_duplicate_ratio": acceptable_duplicates,
        "coverage_ok": sufficient and acceptable_duplicates,
    }


def coverage_from_segment(seg: Any) -> dict[str, Any]:
    """從 Segment 欄位重建 angle_coverage（缺省時依文字推導）。"""
    stored_type = getattr(seg, "angle_type", None) or ""
    stored_labels = list(getattr(seg, "angle_labels", None) or [])
    stored_key = getattr(seg, "angle_key", None) or ""
    fg = getattr(seg, "functional_gap", "") or ""
    uv = getattr(seg, "user_value", "") or ""
    text = getattr(seg, "text", "") or ""

    # 從 user_value「補齊讀者對「…」所需的說明」還原 question 種子
    question = ""
    if isinstance(uv, str):
        m = re.search(r"「([^」]+)」", uv)
        if m:
            question = m.group(1)

    cov = build_angle_coverage(
        question=question,
        argument_text=text,
        functional_gap=fg if isinstance(fg, str) else str(fg),
        user_value=uv if isinstance(uv, str) else str(uv),
        angle_type=stored_type or None,
        angle_labels=stored_labels or None,
    )
    # 若 segment 已寫入 angle_key 且與 type 一致，優先保留（避免序列化漂移）
    if stored_key and stored_key.startswith(f"{cov['angle_type']}:"):
        cov["angle_key"] = stored_key
    return cov


def is_angle_coverage_complete(cov: dict[str, Any] | None) -> bool:
    """結構完整：有 type、非空 labels、非空 facets、有 key。"""
    if not isinstance(cov, dict):
        return False
    at = cov.get("angle_type")
    labels = cov.get("angle_labels")
    facets = cov.get("covered_facets")
    key = cov.get("angle_key")
    if not isinstance(at, str) or not at.strip():
        return False
    if not isinstance(labels, list) or not labels or not all(
        isinstance(x, str) and x.strip() for x in labels
    ):
        return False
    if not isinstance(facets, list) or not facets or not all(
        isinstance(x, str) and x.strip() for x in facets
    ):
        return False
    if not isinstance(key, str) or not key.strip():
        return False
    return True
