import socket

import pytest

from note_filler.domain import detect_domain
from note_filler.llm import FakeLLM


def _grok_reachable(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def test_detect_domain_law():
    llm = FakeLLM(["law"])
    assert detect_domain("行政程序法第92條所稱行政處分,係指行政機關就公法上具體事件所為之決定。", llm) == "law"


def test_detect_domain_admin():
    llm = FakeLLM(["admin"])
    assert detect_domain("本府各單位公文簽核流程、用印規定與檔案歸檔作業要點。", llm) == "admin"


def test_detect_domain_exam():
    llm = FakeLLM(["exam"])
    assert detect_domain("高普考行政法申論題作答架構與歷屆考古題重點整理。", llm) == "exam"


def test_detect_domain_noise_falls_back_to_other():
    # LLM 回不可辨識的雜訊 → 必須 fallback 到 "other"
    llm = FakeLLM(["嗯...我不太確定這是什麼耶🤔"])
    assert detect_domain("今天天氣不錯,午餐吃了牛肉麵。", llm) == "other"


def test_detect_domain_label_with_trailing_punctuation():
    # LLM 回帶標點/雜訊但含合法標籤 → 仍須抽出正確 Domain
    llm = FakeLLM(["law."])
    assert detect_domain("民法第184條規定侵權行為之損害賠償責任。", llm) == "law"


def test_detect_domain_uppercase_and_whitespace():
    # 大小寫與前後空白皆須容忍
    llm = FakeLLM(["  ADMIN  "])
    assert detect_domain("機關內部差勤與請假作業規範。", llm) == "admin"


@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_detect_domain_real_grok_returns_law():
    # 真打 grok(http://127.0.0.1:8318/v1, grok-4.3);明顯法律文字須回 law
    from note_filler.llm import GrokClient

    llm = GrokClient()
    text = (
        "刑法第271條規定,殺人者處死刑、無期徒刑或十年以上有期徒刑;"
        "前項之未遂犯罰之。本條為普通殺人罪之構成要件與法定刑度。"
    )
    assert detect_domain(text, llm) == "law"
