"""캐치(Catch) 프론트엔드 공고 수집.

캐치 웹사이트가 호출하는 비공식 API를 사용한다.
robots.txt 는 /api/v1.0/recruit/ 중 로그 수집 경로(detail/log, log)만 금지하고
목록 조회 경로는 막지 않는다.
"""

import re
import time

from common import FE_TITLE, get_json, normalize_location

API_URL = "https://www.catch.co.kr/api/v1.0/recruit/information/getRecruitList"
REFERER = "https://www.catch.co.kr/NCS/RecruitSearch"
KEYWORD = "프론트엔드"
PAGE_SIZE = 30
MAX_PAGES = 20

# "7년↑", "3~5년", "신입" 같은 표기에서 숫자를 뽑는다.
RANGE = re.compile(r"(\d+)\s*~\s*(\d+)")
MIN_ONLY = re.compile(r"(\d+)\s*년?\s*[↑이상]")


def _parse_experience(record):
    text = record.get("ExperienceRange") or ""
    is_newbie = (record.get("CareerGubunCode") or "") in ("신입", "신입/경력")

    if record.get("IsNotCareCareer") or "무관" in text:
        return None, None, True

    m = RANGE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2)), is_newbie

    m = MIN_ONLY.search(text)
    if m:
        return int(m.group(1)), None, is_newbie

    return None, None, is_newbie


def fetch_raw():
    items = []
    seen = set()

    for page in range(1, MAX_PAGES + 1):
        body = get_json(
            API_URL,
            {
                "Keyword": KEYWORD,
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


def is_frontend(item):
    return bool(FE_TITLE.search(item.get("RecruitTitle") or ""))


def to_record(item):
    annual_from, annual_to, is_newbie = _parse_experience(item)
    recruit_id = item.get("RecruitID")

    return {
        "source": "catch",
        "id": f"catch-{recruit_id}",
        "position": item.get("RecruitTitle"),
        "company": item.get("CompName"),
        "location": normalize_location(item.get("WorkArea") or ""),
        "category": item.get("Depth"),
        "annual_from": annual_from,
        "annual_to": annual_to,
        "is_newbie": is_newbie,
        "employment_type": item.get("GubunCode"),
        "reward_total": None,
        "skills": [],
        "thumbnail": None,
        "url": f"https://www.catch.co.kr/Comp/CompRecruit/RecruitDetail/{recruit_id}",
        "flags": {},
    }


def fetch():
    raw = fetch_raw()
    records = [to_record(item) for item in raw if is_frontend(item)]
    unique = {r["id"]: r for r in records}
    print(f"  캐치: 목록 {len(raw)}건 → 프론트엔드 {len(unique)}건")
    return list(unique.values())
