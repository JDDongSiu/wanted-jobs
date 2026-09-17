"""보건관리자·HSE 공고 크롤러가 공유하는 설정과 도구.

프론트엔드 쪽(common.py)과 저장 경로·제목 패턴만 다르고 나머지는 그대로 쓴다.
"""

import re

from common import ROOT, normalize_location

JSON_PATH = ROOT / "public" / "jobs-hse.json"
CSV_PATH = ROOT / "jobs-hse.csv"

# 제목으로 보건관리자 공고를 골라내는 패턴.
# 채용사이트들은 보건관리자 직무로 조회해도 같은 회사가 함께 올린 품질·전기·토목 공고까지
# 딸려 보낸다. '보건' 한 단어만 걸어도 그런 공고는 걸러지고 안전보건·산업보건은 함께 걸린다.
KEYWORD_WORD = re.compile(r"보건|산업위생|health\s*manager", re.IGNORECASE)

# 약어는 대문자일 때만 인정한다. 소문자까지 받으면 영어 문장의 she 가 전부 걸린다.
# 앞뒤에 알파벳이 붙은 낱말(SHELF 등)도 제외한다.
KEYWORD_ABBR = re.compile(r"(?<![A-Za-z])(?:QHSE|HSEQ|SHEQ|HSE|EHS|ESH|SHE)(?![A-Za-z])")


def matches(text):
    """제목이 보건관리자·HSE 공고로 읽히는지."""
    if not text:
        return False
    return bool(KEYWORD_WORD.search(text) or KEYWORD_ABBR.search(text))


def to_location(text):
    """지역 표기를 (화면 문구, 대표 지역) 으로 바꾼다.

    '서울/전국', '경기도 / 평택' 처럼 사이트마다 여러 지역을 한 칸에 몰아 쓴다.
    필터는 하나로 묶여야 하므로 맨 앞 지역만 따로 뽑는다.
    """
    parts = [normalize_location(p.strip()) for p in (text or "").split("/") if p.strip()]
    if not parts:
        return "", ""
    return " / ".join(parts), parts[0].split()[0]


# "3~5년", "7년 이상", "5년↑" 에서 숫자를 뽑는다.
RANGE = re.compile(r"(\d+)\s*[~-]\s*(\d+)")
MIN_ONLY = re.compile(r"(\d+)\s*년?\s*[↑+]|(\d+)\s*년\s*이상")


def parse_career(text):
    """경력 표기를 (최소, 최대, 신입여부, 화면 문구) 로 바꾼다.

    사이트마다 표기가 제각각이라 숫자를 못 뽑는 경우가 많다.
    그때는 최소·최대를 None 으로 두고 원문을 그대로 보여준다.
    """
    text = (text or "").strip()
    if not text:
        return None, None, False, ""

    if "무관" in text:
        return None, None, False, "경력무관"

    is_newbie = "신입" in text

    m = RANGE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2)), is_newbie, f"경력 {m.group(1)}-{m.group(2)}년"

    m = MIN_ONLY.search(text)
    if m:
        years = int(m.group(1) or m.group(2))
        return years, None, is_newbie, f"경력 {years}년 이상"

    if is_newbie:
        return 0, None, True, "신입"

    return None, None, False, text
