"""피플앤잡 보건관리자·HSE 공고 수집.

robots.txt 가 검색·직종별 목록 주소(/jobs?...)를 모든 크롤러에게 막아 놓아서
허용된 /jobs 한 장, 즉 그날 올라온 공고만 읽는다.
sitemap.xml 도 이 주소 하나만 싣고 있다.

그래서 하루에 걸리는 공고가 없을 수도 있다. 대신 매일 돌면서 그날 것을 줍는다.
"""

from bs4 import BeautifulSoup
from common import HEADERS
from hse_common import matches, parse_career, to_location

import requests

LIST_URL = "https://www.peoplenjob.com/jobs"

# 피플앤잡은 경력 연차 대신 직급으로 표기한다. 신입만 구간으로 옮길 수 있다.
NEWBIE_LEVELS = {"신입", "인턴"}


def _parse_card(card):
    title_el = card.select_one(".jd-card-title a")
    if not title_el or not title_el.get("href"):
        return None

    job_id = title_el["href"].rstrip("/").rsplit("/", 1)[-1]
    company_el = card.select_one(".jd-card-company")
    location_el = card.select_one(".jd-card-meta-location-text")
    career_el = card.select_one(".jd-card-meta-career-text")

    career_raw = career_el.get_text(strip=True) if career_el else ""
    if career_raw in NEWBIE_LEVELS:
        annual_from, annual_to, is_newbie, career_text = 0, None, True, career_raw
    else:
        annual_from, annual_to, is_newbie, career_text = parse_career(career_raw)

    location, region = to_location(location_el.get_text(strip=True) if location_el else "")

    return {
        "source": "peoplenjob",
        "id": f"peoplenjob-{job_id}",
        "position": title_el.get_text(strip=True),
        "company": company_el.get_text(strip=True) if company_el else "",
        "location": location,
        "region": region,
        "category": None,
        "annual_from": annual_from,
        "annual_to": annual_to,
        "is_newbie": is_newbie,
        "career_text": career_text,
        "employment_type": None,
        "url": f"https://www.peoplenjob.com/jobs/{job_id}",
    }


def fetch():
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    cards = BeautifulSoup(resp.text, "lxml").select("div.jd-card")
    records = [r for r in (_parse_card(c) for c in cards) if r]
    hit = [r for r in records if matches(r["position"])]

    print(f"  피플앤잡: 오늘 올라온 {len(records)}건 → {len(hit)}건")
    return hit
