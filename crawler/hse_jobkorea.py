"""잡코리아 보건관리자·HSE 공고 수집.

공식 API가 없어 목록 페이지의 HTML을 파싱한다.
robots.txt 는 일반 크롤러에게 /recruit/joblist 와 /Recruit/GI_Read 를 명시적으로 허용한다.
(금지 경로는 로그인·회원 영역과 /Search 검색 주소다.)
"""

import re
import time

from bs4 import BeautifulSoup
from common import HEADERS, REGION_NAMES
from hse_common import matches, to_location

import requests

LIST_URL = "https://www.jobkorea.co.kr/Recruit/Home/_GI_List/"
JOBLIST_URL = "https://www.jobkorea.co.kr/recruit/joblist"

# 잡코리아 직무 코드. 안전관리자 쪽은 순수 안전 공고가 대부분이지만
# HSE·안전보건 공고가 이 분류에만 달려 있는 경우가 있어 함께 훑는다.
DUTIES = {
    "1000410": "보건관리자",
    "1000361": "안전관리자",
}

MAX_PAGES = 50  # 한 페이지 40건. 안전관리자가 2천 건 가까워 넉넉히 잡는다.

CAREER_RANGE = re.compile(r"경력\s*(\d+)\s*~\s*(\d+)\s*년")
CAREER_MIN = re.compile(r"경력\s*(\d+)\s*년?\s*[↑이상]")

# cell 순서가 고정이 아니라 지역은 내용으로 골라낸다.
LOCATION_START = re.compile(r"^(?:%s)" % "|".join(REGION_NAMES))

EMPLOYMENT_TYPES = {
    "정규직", "계약직", "인턴", "파견직", "도급",
    "프리랜서", "아르바이트", "병역특례", "위촉직",
}


def _parse_career(cells):
    """'경력5년↑', '경력2~5년', '신입', '경력무관' 을 (최소, 최대, 신입여부, 표시문구) 로 바꾼다."""
    for cell in cells:
        if "경력무관" in cell:
            return None, None, False, "경력무관"

        m = CAREER_RANGE.search(cell)
        if m:
            return int(m.group(1)), int(m.group(2)), "신입" in cell, f"경력 {m.group(1)}-{m.group(2)}년"

        m = CAREER_MIN.search(cell)
        if m:
            return int(m.group(1)), None, "신입" in cell, f"경력 {m.group(1)}년 이상"

        if "신입" in cell:
            return 0, None, True, "신입"

    return None, None, False, ""


def _parse_row(row, duty_name):
    title_el = row.select_one("td.tplTit a[title]")
    company_el = row.select_one("td.tplCo a.link")
    if not title_el or not company_el:
        return None

    gno = row.get("data-gno")
    cells = [c.get_text(strip=True) for c in row.select("p.etc span.cell") if c.get_text(strip=True)]

    location, region = to_location(next((c for c in cells if LOCATION_START.match(c)), ""))
    employment = next((c for c in cells if c in EMPLOYMENT_TYPES), None)
    annual_from, annual_to, is_newbie, career_text = _parse_career(cells)

    return {
        "source": "jobkorea",
        "id": f"jobkorea-{gno}",
        "position": title_el.get("title", "").strip(),
        "company": company_el.get_text(strip=True),
        "location": location,
        "region": region,
        "category": duty_name,
        "annual_from": annual_from,
        "annual_to": annual_to,
        "is_newbie": is_newbie,
        "career_text": career_text,
        "employment_type": employment,
        "url": f"https://www.jobkorea.co.kr/Recruit/GI_Read/{gno}",
    }


def _fetch_rows(session, duty):
    """한 직무의 공고 행을 끝까지 모은다."""
    rows = []
    seen = set()

    headers = {
        "Referer": f"{JOBLIST_URL}?duty={duty}",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    for page in range(1, MAX_PAGES + 1):
        resp = session.post(
            LIST_URL, data={"duty": duty, "Page": page}, headers=headers, timeout=30
        )
        resp.raise_for_status()

        page_rows = BeautifulSoup(resp.text, "lxml").select("tr.devloopArea")
        if not page_rows:
            break

        # 마지막 페이지를 넘어가면 같은 내용을 계속 돌려주므로 중복으로 판단한다.
        gnos = {r.get("data-gno") for r in page_rows}
        if gnos <= seen:
            break
        seen |= gnos
        rows.extend(page_rows)

        time.sleep(0.4)  # 서버 부하 방지

    return rows


def fetch():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(JOBLIST_URL, timeout=30)  # 세션 쿠키 확보

    unique = {}
    for duty, name in DUTIES.items():
        raw = _fetch_rows(session, duty)
        records = [r for r in (_parse_row(row, name) for row in raw) if r]
        records = [r for r in records if matches(r["position"])]

        # 같은 공고가 여러 직무·여러 페이지에 걸쳐 나온다. 먼저 담은 쪽을 남긴다.
        for record in records:
            unique.setdefault(record["id"], record)
        print(f"    {name}: 목록 {len(raw)}건 → {len(records)}건")

    print(f"  잡코리아: {len(unique)}건")
    return list(unique.values())
