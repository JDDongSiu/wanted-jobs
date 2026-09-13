"""점핏(Jumpit) 프론트엔드 공고 수집.

점핏 웹사이트가 브라우저에서 호출하는 비공식 API(jumpit-api.saramin.co.kr)를 사용한다.
"""

import time

from common import FE_TITLE, get_json, normalize_location

API_URL = "https://jumpit-api.saramin.co.kr/api/positions"
JOB_CATEGORY_FE = 2  # 프론트엔드 개발자
FE_CATEGORY_NAME = "프론트엔드 개발자"


def fetch_raw():
    positions = []
    page = 1

    while True:
        body = get_json(
            API_URL,
            {
                "jobCategory": JOB_CATEGORY_FE,
                "sort": "rsp_rate",
                "highlight": "false",
                "page": page,
            },
            referer="https://jumpit.saramin.co.kr/positions",
        )
        batch = body.get("result", {}).get("positions", [])
        if not batch:
            break
        positions.extend(batch)
        page += 1
        time.sleep(0.2)  # 서버 부하 방지

    return positions


def is_frontend(position):
    """직무가 프론트엔드 하나뿐이거나, 제목이 명백히 프론트엔드인 공고만 남긴다.

    점핏은 한 공고에 여러 직무를 달 수 있어서, 프론트엔드를 곁다리로 단
    백엔드·게임 공고까지 함께 조회된다.
    """
    categories = [c.strip() for c in (position.get("jobCategory") or "").split(",")]
    if categories == [FE_CATEGORY_NAME]:
        return True
    return bool(FE_TITLE.search(position.get("title") or ""))


def to_record(position):
    celebration = position.get("celebration")
    locations = position.get("locations") or []

    return {
        "source": "jumpit",
        "id": f"jumpit-{position.get('id')}",
        "position": position.get("title"),
        "company": position.get("companyName"),
        "location": normalize_location(locations[0]) if locations else "",
        "category": position.get("jobCategory"),
        "annual_from": position.get("minCareer"),
        "annual_to": position.get("maxCareer"),
        "is_newbie": position.get("newcomer"),
        "employment_type": None,
        "reward_total": f"{celebration}만원" if celebration else None,
        "skills": position.get("techStacks") or [],
        "thumbnail": position.get("imagePath"),
        "url": f"https://jumpit.saramin.co.kr/position/{position.get('id')}",
        "flags": {},
    }


def fetch():
    raw = fetch_raw()
    records = [to_record(p) for p in raw if is_frontend(p)]
    print(f"  점핏: API {len(raw)}건 → 프론트엔드 {len(records)}건")
    return records
