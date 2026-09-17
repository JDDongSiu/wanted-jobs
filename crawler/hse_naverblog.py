"""네이버 블로그에 올라온 보건관리자·HSE 채용글 수집(최근 1주일).

네이버는 robots.txt 로 검색·블로그 페이지를 모든 크롤러에게 막아 놓았다.
정식 경로인 네이버 검색 오픈 API(https://developers.naver.com)를 쓴다.
NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없으면 이 소스는 건너뛴다.
"""

import html
import os
import re
import time
from datetime import datetime, timedelta

from common import HEADERS, KST
from hse_common import to_location

import requests

API_URL = "https://openapi.naver.com/v1/search/blog.json"

# 블로그 글은 제목이 자유로워서 채용 글만 남기려면 직무와 채용을 같이 걸어야 한다.
QUERIES = (
    "보건관리자 채용",
    "보건관리자 구인",
    "안전보건관리자 채용",
    "EHS 채용",
    "HSE 채용",
)

DISPLAY = 100  # API 최대값
RECENT_DAYS = 7

TAG = re.compile(r"<[^>]+>")
REGION_IN_TITLE = re.compile(
    r"서울|부산|대구|인천|대전|울산|광주|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주"
)


def _clean(text):
    """검색어와 겹치는 부분에 <b> 태그가 붙어 온다."""
    return html.unescape(TAG.sub("", text or "")).strip()


def fetch_query(query, headers):
    resp = requests.get(
        API_URL,
        params={"query": query, "display": DISPLAY, "sort": "date"},
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("items") or []


def to_record(item, posted):
    title = _clean(item.get("title"))
    region_match = REGION_IN_TITLE.search(title)
    location, region = to_location(region_match.group(0) if region_match else "")

    return {
        "source": "naverblog",
        "id": f"naverblog-{item.get('link')}",
        "position": title,
        "company": _clean(item.get("bloggername")),
        "location": location,
        "region": region,
        "category": "블로그 글",
        "annual_from": None,
        "annual_to": None,
        "is_newbie": False,
        "career_text": "",
        "employment_type": None,
        "url": item.get("link"),
        "first_seen": posted.isoformat(),
    }


def fetch():
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not (client_id and client_secret):
        print("  네이버블로그: NAVER_CLIENT_ID/SECRET 이 없어 건너뜀")
        return []

    headers = {
        **HEADERS,
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    cutoff = datetime.now(KST).date() - timedelta(days=RECENT_DAYS - 1)

    unique = {}
    total = 0
    for query in QUERIES:
        items = fetch_query(query, headers)
        total += len(items)
        for item in items:
            try:
                posted = datetime.strptime(item.get("postdate", ""), "%Y%m%d").date()
            except ValueError:
                continue
            if posted < cutoff:
                continue
            record = to_record(item, posted)
            unique.setdefault(record["id"], record)
        time.sleep(0.2)  # 서버 부하 방지

    print(f"  네이버블로그: 검색 {total}건 → 최근 {RECENT_DAYS}일 {len(unique)}건")
    return list(unique.values())
