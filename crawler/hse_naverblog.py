"""네이버 블로그에 올라온 보건관리자 채용글 수집(최근 1주일).

네이버는 robots.txt 로 검색·블로그 페이지를 모든 크롤러에게 막아 놓았다.
정식 경로인 검색 API를 쓴다.

검색 API는 네이버 개발자센터에서 네이버 클라우드 플랫폼 API Hub 로 옮겨갔다.
주소가 openapi.naver.com → naverapihub.apigw.ntruss.com 으로 바뀌었고
인증 헤더 이름도 X-Naver-Client-* → X-NCP-APIGW-API-KEY* 로 바뀌었다.
NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없으면 이 소스는 건너뛴다.
"""

import html
import os
import re
import time
from datetime import datetime, timedelta

from common import KST
from hse_common import to_location

import requests

API_URL = "https://naverapihub.apigw.ntruss.com/search/v1/blog"

QUERY = "보건관리자 채용"

DISPLAY = 100  # API 최대값
MAX_START = 1000  # API 가 받는 start 최대값
RECENT_DAYS = 7

TAG = re.compile(r"<[^>]+>")
REGION_IN_TITLE = re.compile(
    r"서울|부산|대구|인천|대전|울산|광주|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주"
)

# '보건관리자 채용' 으로 검색해도 자격증 학원 광고, 안전보건 위탁기관 영업글,
# 면접학원 후기, 다른 직무 채용글이 함께 걸린다. 제목을 세 겹으로 거른다.
# 직무와 채용을 둘 다 말하면서, 공고가 아닌 글의 표시어가 없어야 남긴다.
ROLE = re.compile(r"보건\s*관리자|산업\s*간호사|health\s*manager", re.IGNORECASE)
HIRING = re.compile(r"채용|공고|모집|구인|영입")
NOT_POSTING = re.compile(
    r"응시\s*자격|선임\s*자격|자격증|시험|합격|면접|학원|되는\s*법|난이도"
)


def is_posting(title):
    """공고를 소개하는 글인지. 정보글·광고글을 걸러낸다."""
    return bool(ROLE.search(title) and HIRING.search(title)) and not NOT_POSTING.search(title)


def _clean(text):
    """검색어와 겹치는 부분에 <b> 태그가 붙어 온다."""
    return html.unescape(TAG.sub("", text or "")).strip()


def _posted(item):
    try:
        return datetime.strptime(item.get("postdate", ""), "%Y%m%d").date()
    except ValueError:
        return None


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
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }
    cutoff = datetime.now(KST).date() - timedelta(days=RECENT_DAYS - 1)

    unique = {}
    total = 0
    dropped = 0
    # 최신순으로 받다가 기간을 벗어나는 글이 나오면 멈춘다.
    for start in range(1, MAX_START + 1, DISPLAY):
        resp = requests.get(
            API_URL,
            params={"query": QUERY, "display": DISPLAY, "start": start, "sort": "date"},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()

        items = resp.json().get("items") or []
        if not items:
            break
        total += len(items)

        for item in items:
            posted = _posted(item)
            if not posted or posted < cutoff:
                continue
            record = to_record(item, posted)
            if not is_posting(record["position"]):
                dropped += 1
                continue
            unique.setdefault(record["id"], record)

        oldest = _posted(items[-1])
        if oldest and oldest < cutoff:
            break
        time.sleep(0.2)  # 서버 부하 방지

    print(
        f"  네이버블로그: 검색 {total}건 → 최근 {RECENT_DAYS}일 {len(unique)}건"
        f" (공고 아닌 글 {dropped}건 제외)"
    )
    return list(unique.values())
