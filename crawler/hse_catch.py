"""캐치(Catch) 보건관리자·HSE 공고 수집.

캐치 웹사이트가 호출하는 비공식 API를 사용한다.
robots.txt 는 /api/v1.0/recruit/ 중 로그 수집 경로(detail/log, log)만 금지하고
목록 조회 경로는 막지 않는다.
"""

import time

from common import get_json
from hse_common import matches, parse_career, to_location

API_URL = "https://www.catch.co.kr/api/v1.0/recruit/information/getRecruitList"
REFERER = "https://www.catch.co.kr/NCS/RecruitSearch"

# 캐치는 한 번에 한 단어만 받는다. 표기가 갈려서 나눠 조회한 뒤 합친다.
KEYWORDS = ("보건관리자", "안전보건", "산업보건", "EHS", "HSE", "SHE")
PAGE_SIZE = 30
MAX_PAGES = 20


def fetch_keyword(keyword):
    items = []
    seen = set()

    for page in range(1, MAX_PAGES + 1):
        body = get_json(
            API_URL,
            {
                "Keyword": keyword,
                "Sort": 0,
                "curpage": page,
                "pageSize": PAGE_SIZE,
                "onRecruitYN": "Y",
            },
            referer=REFERER,
        )
        batch = body.get("recruitData") or []
        if not batch:
            break

        ids = {r.get("RecruitID") for r in batch}
        if ids <= seen:
            break
        seen |= ids
        items.extend(batch)

        if len(items) >= (body.get("intTotalRecordCount") or 0):
            break
        time.sleep(0.3)  # 서버 부하 방지

    return items


def to_record(item):
    text = item.get("ExperienceRange") or item.get("CareerGubunCode") or ""
    annual_from, annual_to, is_newbie, career_text = parse_career(text)
    location, region = to_location(item.get("WorkArea"))
    recruit_id = item.get("RecruitID")

    return {
        "source": "catch",
        "id": f"catch-{recruit_id}",
        "position": item.get("RecruitTitle"),
        "company": item.get("CompName"),
        "location": location,
        "region": region,
        "category": item.get("Depth"),
        "annual_from": annual_from,
        "annual_to": annual_to,
        "is_newbie": is_newbie,
        "career_text": career_text,
        "employment_type": item.get("GubunCode"),
        "url": f"https://www.catch.co.kr/NCS/RecruitInfoDetails/{recruit_id}",
    }


def fetch():
    unique = {}
    total = 0

    for keyword in KEYWORDS:
        raw = fetch_keyword(keyword)
        total += len(raw)
        # 캐치는 본문까지 검색해서 '안전보건' 처럼 흔한 말에는 무관한 공고가 많이 걸린다.
        hit = [to_record(item) for item in raw if matches(item.get("RecruitTitle"))]
        for record in hit:
            unique.setdefault(record["id"], record)
        print(f"    {keyword}: 검색 {len(raw)}건 → {len(hit)}건")

    print(f"  캐치: 검색 {total}건 → {len(unique)}건")
    return list(unique.values())
