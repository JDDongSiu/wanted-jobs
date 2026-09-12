"""사람인(Saramin) 프론트엔드 공고 수집.

사람인 공식 오픈 API(https://oapi.saramin.co.kr/job-search)를 사용한다.
access-key 는 환경변수 SARAMIN_API_KEY 로 넘긴다. 키가 없으면 이 소스는 건너뛴다.
"""

import os
import time

from common import FE_TITLE, get_json

API_URL = "https://oapi.saramin.co.kr/job-search"
KEYWORDS = "프론트엔드"
JOB_MID_CD = 22  # IT개발·데이터
PAGE_SIZE = 110  # API 최대값


def _text(value):
    """사람인 JSON은 값이 문자열이거나 {"name": ...} 형태로 온다."""
    if isinstance(value, dict):
        return value.get("name") or ""
    return value or ""


def fetch_raw(access_key):
    jobs = []
    start = 0

    while True:
        body = get_json(
            API_URL,
            {
                "access-key": access_key,
                "keywords": KEYWORDS,
                "job_mid_cd": JOB_MID_CD,
                "count": PAGE_SIZE,
                "start": start,
                "sort": "pd",
            },
        )
        if "jobs" not in body:
            raise RuntimeError(f"사람인 API 오류: {body}")

        batch = body["jobs"].get("job") or []
        if not batch:
            break
        jobs.extend(batch)

        total = int(body["jobs"].get("total") or 0)
        if len(jobs) >= total:
            break
        start += 1
        time.sleep(0.3)  # 일일 요청 한도가 있어 여유를 둔다

    return jobs


def is_frontend(job):
    title = _text((job.get("position") or {}).get("title"))
    return bool(FE_TITLE.search(title))


def to_record(job):
    position = job.get("position") or {}
    experience = position.get("experience-level") or {}
    code = experience.get("code")

    location = _text(position.get("location")).replace(" > ", " ")

    return {
        "source": "saramin",
        "id": f"saramin-{job.get('id')}",
        "position": _text(position.get("title")),
        "company": _text((job.get("company") or {}).get("name")),
        "location": location,
        "category": _text(position.get("job-code")),
        "annual_from": experience.get("min"),
        "annual_to": experience.get("max"),
        "is_newbie": code in (1, 3, "1", "3"),
        "employment_type": _text(position.get("job-type")),
        "reward_total": None,
        "skills": [k.strip() for k in (job.get("keyword") or "").split(",") if k.strip()],
        "thumbnail": None,
        "url": job.get("url"),
        "flags": {},
    }


def fetch():
    access_key = os.environ.get("SARAMIN_API_KEY")
    if not access_key:
        print("  사람인: SARAMIN_API_KEY 가 없어 건너뜀")
        return []

    raw = fetch_raw(access_key)
    records = [to_record(job) for job in raw if is_frontend(job)]
    print(f"  사람인: API {len(raw)}건 → 프론트엔드 {len(records)}건")
    return records
