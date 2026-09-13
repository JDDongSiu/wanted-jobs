"""여러 채용사이트에서 프론트엔드 공고를 모아 public/jobs.json 과 jobs.csv 로 저장한다."""

import csv
import json
import sys
from datetime import datetime

import jobkorea
import jumpit
import saramin
import wanted
from common import CSV_PATH, JSON_PATH, KST, ROOT
from wanted import CONDITIONS

SOURCES = (wanted, jumpit, saramin, jobkorea)

CSV_FIELDS = [
    "source",
    "position",
    "company",
    "location",
    "category",
    "annual_from",
    "annual_to",
    "employment_type",
    "reward_total",
    "url",
]


def is_matched(record):
    """원티드 조건을 모두 충족했는지. 조건은 원티드 태그라 다른 소스에는 적용하지 않는다."""
    return record["source"] == "wanted" and all(record["flags"].values())


def load_previous_by_source():
    """직전 수집 결과를 소스별로 나눠 둔다. 수집 실패한 소스의 공고를 살리는 데 쓴다."""
    if not JSON_PATH.exists():
        return {}

    with open(JSON_PATH, encoding="utf-8") as f:
        previous = json.load(f)

    by_source = {}
    for job in previous.get("jobs", []):
        by_source.setdefault(job["source"], []).append(job)
    return by_source


def collect():
    """소스별로 수집하되, 한 곳이 실패해도 나머지는 계속 진행한다.

    원티드·점핏은 비공식 API라 차단(403)이나 사이트 변경으로 언제든 실패할 수 있다.
    실패한 소스를 빈 값으로 덮으면 멀쩡하던 공고가 통째로 사라지므로 직전 데이터를 유지한다.
    """
    previous = load_previous_by_source()
    jobs = []
    stale = []

    for module in SOURCES:
        name = module.__name__
        try:
            jobs.extend(module.fetch())
        except Exception as exc:
            kept = previous.get(name, [])
            stale.append(name)
            jobs.extend(kept)
            print(f"  {name}: 수집 실패 ({exc})")
            print(f"  {name}: 직전 데이터 {len(kept)}건을 그대로 둠")

    return jobs, stale


def main():
    print("공고 수집 중...")
    jobs, stale = collect()

    if len(stale) == len(SOURCES):
        print("\n모든 소스 수집에 실패했습니다.")
        sys.exit(1)

    counts = {}
    for job in jobs:
        counts[job["source"]] = counts.get(job["source"], 0) + 1

    payload = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "sources": counts,
        "stale_sources": stale,
        "total_count": len(jobs),
        "matched_count": sum(1 for job in jobs if is_matched(job)),
        "conditions": list(CONDITIONS),
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
    print(f"원티드 조건 충족: {payload['matched_count']}건")
    print(f"저장 완료: {JSON_PATH.relative_to(ROOT)}, {CSV_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
