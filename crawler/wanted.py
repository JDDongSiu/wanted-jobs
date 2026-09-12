"""원티드(Wanted) 프론트엔드 공고 수집.

원티드 웹사이트가 브라우저에서 호출하는 비공식 API를 사용한다.
"""

import time

from common import FE_TITLE, get_json

API_URL = "https://www.wanted.co.kr/api/chaos/navigation/v1/results"
JOB_GROUP_ID = 518  # 개발
JOB_ID = 669  # 프론트엔드 개발자

# 필터 조건: 조건 키 → 원티드 태그 ID (하나라도 있으면 충족).
# 조건을 바꾸려면 여기만 고치면 된다. 화면의 체크박스도 이 키를 따라간다.
# 원티드 고유 태그라 점핏·사람인 공고에는 적용되지 않는다.
CONDITIONS = {
    "established": (10408, 10409),  # 설립4~9년 또는 설립10년이상
    "rapid_growth": (10401,),  # 인원 급성장
    "equipment": (10439,),  # 장비지원
}

JOB_CATEGORIES = {
    660: "자바 개발자",
    665: "시스템,네트워크 관리자",
    669: "프론트엔드 개발자",
    672: "하드웨어 엔지니어",
    674: "DevOps / 시스템 관리자",
    872: "서버 개발자",
    873: "웹 개발자",
    876: "프로덕트 매니저",
    877: "개발 매니저",
    896: "영상,음성 엔지니어",
    899: "파이썬 개발자",
    900: "C,C++ 개발자",
    939: "웹 퍼블리셔",
    1024: "데이터 사이언티스트",
    1025: "빅데이터 엔지니어",
    1027: "블록체인 플랫폼 엔지니어",
    1634: "머신러닝 엔지니어",
    10111: "크로스플랫폼 앱 개발자",
}


def fetch_raw():
    postings = []
    offset = 0
    limit = 100

    while True:
        body = get_json(
            API_URL,
            {
                "job_group_id": JOB_GROUP_ID,
                "job_ids": JOB_ID,
                "country": "kr",
                "job_sort": "job.latest_order",
                "years": -1,
                "locations": "all",
                "limit": limit,
                "offset": offset,
            },
        )
        data = body.get("data", [])
        if not data:
            break
        postings.extend(data)

        if not body.get("links", {}).get("next"):
            break
        offset += limit
        time.sleep(0.2)  # 서버 부하 방지

    return postings


def is_frontend(job):
    """대표 직무가 프론트엔드이거나 제목이 명백히 프론트엔드인 공고만 남긴다.

    제목 조건이 필요한 이유: 실제 프론트엔드 공고를 '웹 개발자'(873)로 등록한 회사가 많다.
    """
    category_id = (job.get("category_tag") or {}).get("id")
    return category_id == JOB_ID or bool(FE_TITLE.search(job.get("position") or ""))


def to_record(job):
    address = job.get("address", {})
    location = " ".join(filter(None, [address.get("location"), address.get("district")]))
    tags = set(job.get("attraction_tags", []))
    category_id = (job.get("category_tag") or {}).get("id")

    return {
        "source": "wanted",
        "id": f"wanted-{job.get('id')}",
        "position": job.get("position"),
        "company": job.get("company", {}).get("name"),
        "location": location,
        "category": JOB_CATEGORIES.get(category_id),
        "annual_from": job.get("annual_from"),
        "annual_to": job.get("annual_to"),
        "is_newbie": job.get("is_newbie"),
        "employment_type": job.get("employment_type"),
        "reward_total": job.get("reward_total"),
        "skills": [],
        "thumbnail": (job.get("title_img") or {}).get("thumb"),
        "url": f"https://www.wanted.co.kr/wd/{job.get('id')}",
        "flags": {key: bool(tags.intersection(ids)) for key, ids in CONDITIONS.items()},
    }


def fetch():
    raw = fetch_raw()
    records = [to_record(job) for job in raw if is_frontend(job)]
    print(f"  원티드: API {len(raw)}건 → 프론트엔드 {len(records)}건")
    return records
