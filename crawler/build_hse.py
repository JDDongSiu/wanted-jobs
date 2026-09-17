"""여러 채용사이트에서 보건관리자·HSE 공고를 모아 public/jobs-hse.json 과 jobs-hse.csv 로 저장한다.

프론트엔드 쪽(build_jobs.py)과 데이터가 섞이지 않도록 파일을 따로 쓴다.
"""

import csv
import json
import re
import sys
from datetime import datetime

import hse_catch
import hse_jobkorea
import hse_naverblog
import hse_peoplenjob
from common import KST, ROOT
from hse_common import CSV_PATH, JSON_PATH

SOURCES = (hse_jobkorea, hse_catch, hse_peoplenjob, hse_naverblog)

# 같은 공고가 여러 사이트에 올라왔을 때 남길 순서.
# 잡코리아가 경력·고용형태를 가장 잘 채워 준다.
SOURCE_PRIORITY = ("jobkorea", "catch", "peoplenjob")

# 사이트마다 같은 공고를 '채용' 과 '영입' 으로 다르게 적는다.
HIRING_WORDS = re.compile(r"채용|영입|모집|구인|공고")

CSV_FIELDS = [
    "source",
    "position",
    "company",
    "location",
    "category",
    "career_text",
    "employment_type",
    "url",
]


def source_name(module):
    """모듈 이름과 공고의 source 값을 맞춘다(hse_jobkorea → jobkorea)."""
    return module.__name__.removeprefix("hse_")


def load_previous():
    if not JSON_PATH.exists():
        return []

    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f).get("jobs", [])


def group_by_source(jobs):
    """수집 실패한 소스의 공고를 살리는 데 쓴다."""
    by_source = {}
    for job in jobs:
        by_source.setdefault(job["source"], []).append(job)
    return by_source


def _same_posting(job):
    """같은 공고인지 판단할 열쇠.

    회사명은 사이트마다 표기가 갈리고(SK㈜ AX / SK AX), 제목은 끝에 붙는
    '채용'·'영입' 만 다른 경우가 많다. 둘 다 지우고 비교한다.
    """
    def flat(text):
        return re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())

    return flat(job["company"]), flat(HIRING_WORDS.sub("", job["position"] or ""))


def drop_duplicates(jobs):
    """같은 공고를 하나만 남긴다.

    회사가 잡코리아와 캐치에 같이 올리거나, 한 사이트에 두 번 올리는 일이 흔하다.
    블로그 글은 공고가 아니라 공고를 소개하는 글이라 대상에서 뺀다.
    """
    rank = {name: i for i, name in enumerate(SOURCE_PRIORITY)}
    chosen = {}
    blogs = []

    for job in jobs:
        if job["source"] == "naverblog":
            blogs.append(job)
            continue

        key = _same_posting(job)
        kept = chosen.get(key)
        if kept is None or rank.get(job["source"], 99) < rank.get(kept["source"], 99):
            chosen[key] = job

    picked = list(chosen.values())
    dropped = len(jobs) - len(blogs) - len(picked)
    return picked + blogs, dropped


def apply_first_seen(jobs, previous):
    """공고를 처음 본 날짜를 남긴다. 화면에서 신착을 구분하는 근거가 된다.

    블로그 글은 작성일을 이미 들고 오므로 그대로 둔다.
    """
    today = datetime.now(KST).date().isoformat()
    known = {job["id"]: job.get("first_seen") for job in previous}

    for job in jobs:
        if job.get("first_seen"):
            continue
        job["first_seen"] = known.get(job["id"], today)

    return sum(1 for job in jobs if job["first_seen"] == today)


def collect():
    """소스별로 수집하되, 한 곳이 실패해도 나머지는 계속 진행한다.

    비공식 API나 HTML 파싱이라 차단이나 사이트 변경으로 언제든 실패할 수 있다.
    실패한 소스를 빈 값으로 덮으면 멀쩡하던 공고가 통째로 사라지므로 직전 데이터를 유지한다.
    """
    previous = load_previous()
    by_source = group_by_source(previous)
    jobs = []
    stale = []

    for module in SOURCES:
        name = source_name(module)
        try:
            jobs.extend(module.fetch())
        except Exception as exc:
            kept = by_source.get(name, [])
            stale.append(name)
            jobs.extend(kept)
            print(f"  {name}: 수집 실패 ({exc})")
            print(f"  {name}: 직전 데이터 {len(kept)}건을 그대로 둠")

    return jobs, stale, previous


def main():
    print("보건관리자 공고 수집 중...")
    jobs, stale, previous = collect()

    if len(stale) == len(SOURCES):
        print("\n모든 소스 수집에 실패했습니다.")
        sys.exit(1)

    jobs, duplicates = drop_duplicates(jobs)
    if duplicates:
        print(f"중복 공고 {duplicates}건 정리")

    new_count = apply_first_seen(jobs, previous)

    counts = {}
    for job in jobs:
        counts[job["source"]] = counts.get(job["source"], 0) + 1

    payload = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "sources": counts,
        "stale_sources": stale,
        "total_count": len(jobs),
        "new_count": new_count,
        "jobs": jobs,
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)

    print(f"\n합계 {len(jobs)}건 {counts}")
    if stale:
        print(f"갱신 실패(직전 데이터 유지): {', '.join(stale)}")
    print(f"오늘 새로 나타난 공고: {new_count}건")
    print(f"저장 완료: {JSON_PATH.relative_to(ROOT)}, {CSV_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
