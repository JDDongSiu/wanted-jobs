"""리멤버 커리어(Remember) 프론트엔드 공고 수집.

리멤버 웹사이트가 브라우저에서 호출하는 비공식 API(career-api.rememberapp.co.kr)를 사용한다.
로그인 없이도 공개 공고 검색은 응답한다.
robots.txt 는 일반 크롤러에게 /job/ 을 허용한다. (API 도메인에는 robots.txt 가 없다.)
"""

import time
from datetime import datetime

import requests
from common import FE_TITLE, HEADERS, KST, normalize_location

API_URL = "https://career-api.rememberapp.co.kr/job_postings/search"
SITE = "https://career.rememberapp.co.kr"
KEYWORD = "프론트엔드"
PAGE_SIZE = 30
MAX_PAGES = 20

POST_HEADERS = {
    **HEADERS,
    "Content-Type": "application/json",
    "Origin": SITE,
    "Referer": f"{SITE}/job/postings",
    "Sec-Fetch-Site": "same-site",
}


def fetch_raw():
    items = []
    seen = set()

    for page in range(1, MAX_PAGES + 1):
        resp = requests.post(
            API_URL,
            json={
                "search": {"keywords": [KEYWORD], "includeAppliedJobPosting": False},
                "sort": "starts_at_desc",
                "page": page,
                "per": PAGE_SIZE,
            },
            headers=POST_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()

        batch = body.get("data") or []
        ids = {item.get("id") for item in batch}
        if not batch or ids <= seen:
            break
        seen |= ids
        items.extend(batch)

        if page >= (body.get("meta") or {}).get("total_pages", 0):
            break
        time.sleep(0.3)  # 서버 부하 방지

    return items


def is_open(item):
    """마감일이 지난 공고는 뺀다. 상시채용은 ends_at 이 비어 있다."""
    if item.get("status") != "published":
        return False
    ends_at = item.get("ends_at")
    return not ends_at or datetime.fromisoformat(ends_at) >= datetime.now(KST)


def is_frontend(item):
    """키워드 검색은 본문만 걸려도 돌려줘서 백엔드 공고가 절반 넘게 섞인다. 제목으로 거른다."""
    return bool(FE_TITLE.search(item.get("title") or ""))


def to_record(item):
    addresses = item.get("addresses") or []
    location = ""
    if addresses:
        first = addresses[0]
        location = " ".join(
            part for part in (first.get("address_level1"), first.get("address_level2"))
            if part and part != "전체"  # 시·도 전역 공고는 2단계가 "전체"다
        )

    categories = [c.get("level2") for c in item.get("job_categories") or [] if c.get("level2")]
    min_exp = item.get("min_experience")

    return {
        "source": "remember",
        "id": f"remember-{item.get('id')}",
        "position": item.get("title"),
        "company": (item.get("organization") or {}).get("name"),
        "location": normalize_location(location),
        "category": ", ".join(categories) or None,
        "annual_from": min_exp,
        "annual_to": item.get("max_experience"),
        "is_newbie": min_exp == 0,
        "employment_type": None,
        "reward_total": None,
        "skills": [],
        "thumbnail": None,
        "url": f"{SITE}/job/posting/{item.get('id')}",
        "flags": {},
    }


def fetch():
    raw = fetch_raw()
    records = [to_record(item) for item in raw if is_open(item) and is_frontend(item)]
    unique = {r["id"]: r for r in records}
    print(f"  리멤버: 검색 {len(raw)}건 → 프론트엔드 {len(unique)}건")
    return list(unique.values())
