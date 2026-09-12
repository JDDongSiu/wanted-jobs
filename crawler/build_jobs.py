"""여러 채용사이트에서 프론트엔드 공고를 모아 public/jobs.json 과 jobs.csv 로 저장한다."""

import csv
import json
from datetime import datetime

import jumpit
import saramin
import wanted
from common import CSV_PATH, JSON_PATH, KST, ROOT
from wanted import CONDITIONS

SOURCES = (wanted, jumpit, saramin)

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


def main():
    print("공고 수집 중...")
    jobs = []
    for module in SOURCES:
        jobs.extend(module.fetch())

    counts = {}
    for job in jobs:
        counts[job["source"]] = counts.get(job["source"], 0) + 1

    payload = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "sources": counts,
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
    print(f"원티드 조건 충족: {payload['matched_count']}건")
    print(f"저장 완료: {JSON_PATH.relative_to(ROOT)}, {CSV_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
