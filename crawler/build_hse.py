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

# 같은 공고가 여러 곳에 올라왔을 때 남길 순서.
# 블로그 글은 보건관리자가 직접 정리한 것이라 기업리뷰·근무지 같은 설명이 함께 붙는다.
SOURCE_PRIORITY = ("naverblog", "jobkorea", "catch", "peoplenjob")

# 사이트마다 같은 공고를 '채용' 과 '영입' 으로 다르게 적는다.
HIRING_WORDS = re.compile(r"채용|영입|모집|구인|공고")

# 회사명에 붙는 법인격 표기. ㈜ 는 기호라 저절로 빠지지만 (주) 는 '주' 가 남는다.
ENTITY_MARK = re.compile(r"주식회사|유한회사|\(주\)|\(유\)")

# 잡코리아는 한글 음차로, 캐치·블로그는 영문 약자로 적는 회사가 있다
# (에스케이실트론 / SK실트론). 같은 회사로 읽히도록 맞춘다. 새로 보이면 한 줄 더한다.
COMPANY_ALIASES = {
    "에스케이": "sk", "엘지": "lg", "엘엑스": "lx", "지에스": "gs",
    "씨제이": "cj", "에이치디": "hd", "엘에스": "ls", "제이에스알": "jsr",
    "이앤에이": "ea", "마이크로": "micro", "코리아": "korea",
}

# 블로그 제목에서 회사를 찾을 때, 이름이 짧으면 엉뚱한 글에 걸린다.
MIN_COMPANY_LEN = 3

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


def _flat(text):
    """표기 차이를 지운 비교용 문자열. 기호·공백을 빼고 회사명 표기를 맞춘다."""
    text = ENTITY_MARK.sub("", text or "").lower()
    for korean, english in COMPANY_ALIASES.items():
        text = text.replace(korean, english)
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def _same_posting(job):
    """같은 공고인지 판단할 열쇠.

    회사명은 사이트마다 표기가 갈리고(SK㈜ AX / SK(주) AX), 제목은 끝에 붙는
    '채용'·'영입' 만 다른 경우가 많다. 둘 다 지우고 비교한다.
    """
    return _flat(job["company"]), _flat(HIRING_WORDS.sub("", job["position"] or ""))


def _covered_by_blog(job, blog_titles):
    """이 공고를 다룬 블로그 글이 이미 있는지.

    블로그 글은 회사명 자리에 글쓴이가 들어가 있어 회사로 짝지을 수 없다.
    대신 공고의 회사명이 블로그 제목 안에 있는지 본다.
    """
    company = _flat(job["company"])
    if len(company) < MIN_COMPANY_LEN:
        return False
    return any(company in title for title in blog_titles)


def drop_duplicates(jobs):
    """같은 공고를 하나만 남긴다. 짝짓는 방법이 달라 두 단계로 나눈다.

    회사가 잡코리아와 캐치에 같이 올리거나, 한 사이트에 두 번 올리는 일이 흔하다.
    """
    rank = {name: i for i, name in enumerate(SOURCE_PRIORITY)}
    blogs = [job for job in jobs if job["source"] == "naverblog"]
    posts = [job for job in jobs if job["source"] != "naverblog"]

    # 1단계: 공고끼리. 회사와 제목이 같으면 우선순위가 높은 쪽만 남긴다.
    chosen = {}
    for job in posts:
        key = _same_posting(job)
        kept = chosen.get(key)
        if kept is None or rank.get(job["source"], 99) < rank.get(kept["source"], 99):
            chosen[key] = job

    # 2단계: 블로그가 이미 다룬 공고는 블로그 글만 남긴다.
    blog_titles = [_flat(blog["position"]) for blog in blogs]
    picked = [job for job in chosen.values() if not _covered_by_blog(job, blog_titles)]

    return blogs + picked, len(posts) - len(picked), len(chosen) - len(picked)


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

    jobs, duplicates, by_blog = drop_duplicates(jobs)
    if duplicates:
        print(f"중복 공고 {duplicates}건 정리 (블로그 글과 겹친 {by_blog}건 포함)")

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
