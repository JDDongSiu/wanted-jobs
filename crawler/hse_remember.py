"""리멤버(Remember) 보건관리자·HSE 공고 수집.

리멤버 웹사이트가 호출하는 비공식 API를 사용한다.
API 호스트(career-api.rememberapp.co.kr)에는 robots.txt 가 없고(404),
공고 상세 주소(/job/posting/<번호>)는 웹 쪽 robots.txt 가 명시적으로 허용한다.

검색 목록은 화면이 자바스크립트로 불러와서 HTML 에는 없다. 그래서 API 를 쓴다.
"""

import time

import requests
from common import HEADERS
from hse_common import matches, to_location

API_URL = "https://career-api.rememberapp.co.kr/job_postings/search"
SITE_URL = "https://career.rememberapp.co.kr"

# 리멤버는 검색어를 형태소로 쪼개서 '보건관리자' 로 찾으면 '관리자' 공고까지 걸린다.
# 표기가 갈려서 나눠 조회하고, 제목으로 한 번 더 거른다.
KEYWORDS = ("보건관리자", "안전보건", "산업보건", "EHS", "HSE", "SHE")
PER_PAGE = 30
MAX_PAGES = 10


def fetch_keyword(keyword):
    headers = {
        **HEADERS,
        "Content-Type": "application/json",
        "Origin": SITE_URL,
        "Referer": f"{SITE_URL}/",
    }
    items = []

    for page in range(1, MAX_PAGES + 1):
        resp = requests.post(
            API_URL,
            json={
                "search": {
                    "keywords": [keyword],
                    "include_applied_job_posting": False,
                    "leader_position": False,
                    "organization_type": "all",
                    "application_type": "all",
                },
                "sort": "starts_at_desc",
                "page": page,
                "per": PER_PAGE,
            },
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()

        batch = body.get("data") or []
        items.extend(batch)
        if not batch or page >= (body.get("meta") or {}).get("total_pages", 0):
            break
        time.sleep(0.3)  # 서버 부하 방지

    return items


def _career(item):
    """최소·최대 경력(년)을 (최소, 최대, 신입여부, 표시문구) 로 바꾼다.

    둘 다 비어 있으면 화면에 '경력 무관' 으로 나온다.
    """
    low, high = item.get("min_experience"), item.get("max_experience")

    if low is None and high is None:
        return None, None, False, "경력무관"
    if not low:
        return 0, high, True, f"신입-경력 {high}년" if high else "신입"
    if high:
        return low, high, False, f"경력 {low}-{high}년"
    return low, None, False, f"경력 {low}년 이상"


def to_record(item):
    annual_from, annual_to, is_newbie, career_text = _career(item)

    places = [
        f"{a.get('address_level1') or ''} {a.get('address_level2') or ''}".strip()
        for a in item.get("addresses") or []
    ]
    location, region = to_location(" / ".join(p for p in places if p))

    return {
        "source": "remember",
        "id": f"remember-{item['id']}",
        "position": item.get("title"),
        "company": (item.get("organization") or {}).get("name"),
        "location": location,
        "region": region,
        "category": None,
        "annual_from": annual_from,
        "annual_to": annual_to,
        "is_newbie": is_newbie,
        "career_text": career_text,
        "employment_type": None,
        "url": f"{SITE_URL}/job/posting/{item['id']}",
    }


def fetch():
    unique = {}
    total = 0

    for keyword in KEYWORDS:
        raw = fetch_keyword(keyword)
        total += len(raw)
        hit = [to_record(item) for item in raw if matches(item.get("title"))]
        for record in hit:
            unique.setdefault(record["id"], record)
        print(f"    {keyword}: 검색 {len(raw)}건 → {len(hit)}건")

    print(f"  리멤버: 검색 {total}건 → {len(unique)}건")
    return list(unique.values())
