"""잡코리아(JobKorea) 프론트엔드 공고 수집.

공식 API가 없어 목록 페이지의 HTML을 파싱한다.
robots.txt 는 일반 크롤러에게 /recruit/joblist 와 /Recruit/GI_Read 를 명시적으로 허용한다.
(금지 경로는 로그인·회원 영역과 검색 쿼리 URL 이다.)
"""

import re
import time

from bs4 import BeautifulSoup
from common import FE_TITLE, HEADERS

import requests

LIST_URL = "https://www.jobkorea.co.kr/Recruit/Home/_GI_List/"
REFERER = "https://www.jobkorea.co.kr/recruit/joblist?duty=1000230"
DUTY_FRONTEND = "1000230"  # 프론트엔드개발자

MAX_PAGES = 25  # 한 페이지 40건. 넉넉히 잡되 무한 루프는 막는다.

CAREER_RANGE = re.compile(r"경력\s*(\d+)\s*~\s*(\d+)\s*년")
CAREER_MIN = re.compile(r"경력\s*(\d+)\s*년?\s*[↑이상]")


def _parse_career(cells):
    """'경력5년↑', '경력2~5년', '신입', '경력무관' 같은 표기를 숫자로 바꾼다."""
    for cell in cells:
        if "경력무관" in cell or "신입" in cell:
            return None, None, True

        m = CAREER_RANGE.search(cell)
        if m:
            return int(m.group(1)), int(m.group(2)), False

        m = CAREER_MIN.search(cell)
        if m:
            return int(m.group(1)), None, False

    return None, None, False


def _parse_row(row):
    title_el = row.select_one("td.tplTit a[title]")
    company_el = row.select_one("td.tplCo a.link")
    if not title_el or not company_el:
        return None

    gno = row.get("data-gno")
    cells = [c.get_text(strip=True) for c in row.select("p.etc span.cell") if c.get_text(strip=True)]

    # cell 순서가 고정이 아니라 내용으로 구분한다.
    location = next((c for c in cells if re.match(r"^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|해외)", c)), "")
    employment = next((c for c in cells if c in ("정규직", "계약직", "인턴", "파견직", "도급", "프리랜서", "아르바이트", "병역특례")), None)
    annual_from, annual_to, is_newbie = _parse_career(cells)

    return {
        "source": "jobkorea",
        "id": f"jobkorea-{gno}",
        "position": title_el.get("title", "").strip(),
        "company": company_el.get_text(strip=True),
        "location": location,
        "category": "프론트엔드개발자",
        "annual_from": annual_from,
        "annual_to": annual_to,
        "is_newbie": is_newbie,
        "employment_type": employment,
        "reward_total": None,
        "skills": [],
        "thumbnail": None,
        "url": f"https://www.jobkorea.co.kr/Recruit/GI_Read/{gno}",
        "flags": {},
    }


def fetch_raw():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(REFERER, timeout=30)  # 세션 쿠키 확보

    headers = {
        "Referer": REFERER,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    rows = []
    seen = set()

    for page in range(1, MAX_PAGES + 1):
        resp = session.post(
            LIST_URL,
            data={"duty": DUTY_FRONTEND, "Page": page},
            headers=headers,
            timeout=30,
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


def is_frontend(record):
    return bool(FE_TITLE.search(record["position"]))


def fetch():
    raw = fetch_raw()
    records = [r for r in (_parse_row(row) for row in raw) if r]
    records = [r for r in records if is_frontend(r)]

    # 같은 공고가 여러 페이지에 걸쳐 나오는 경우가 있어 한 번 더 정리한다.
    unique = {r["id"]: r for r in records}
    print(f"  잡코리아: 목록 {len(raw)}건 → 프론트엔드 {len(unique)}건")
    return list(unique.values())
