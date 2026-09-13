"""여러 채용사이트 크롤러가 공유하는 설정과 도구."""

import re
from datetime import timedelta, timezone
from pathlib import Path

try:
    # 사내망/보안 소프트웨어가 TLS를 검사하는 환경에서 인증서 검증 실패를 막는다.
    # CI 환경에는 없어도 되므로 실패해도 넘어간다.
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import requests  # noqa: E402

# 채용사이트들이 브라우저가 아닌 요청을 막기 때문에 실제 브라우저와 같은 헤더를 보낸다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

KST = timezone(timedelta(hours=9))

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "public" / "jobs.json"
CSV_PATH = ROOT / "jobs.csv"

# 채용사이트들은 '프론트엔드' 직무로 조회해도 그 직무를 부가로만 단 공고까지 함께 준다.
# 제목으로 한 번 더 거르기 위한 패턴.
FE_TITLE = re.compile(r"프론트\s*엔드|프론트|front[\s\-_]?end|frontend", re.IGNORECASE)


# 사이트마다 지역 표기가 달라(세종 / 세종특별자치시) 화면 필터가 갈라진다.
# 주소의 첫 토큰을 짧은 이름으로 통일한다.
REGION_ALIASES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "광주광역시": "광주",
    "세종특별자치시": "세종",
    "세종시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "강원도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라북도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
    "제주도": "제주",
    "전남광주통합특별시": "전남광주",
}

REGION_NAMES = sorted(
    set(REGION_ALIASES) | set(REGION_ALIASES.values()) | {"해외"},
    key=len,
    reverse=True,
)


def normalize_location(location):
    if not location:
        return ""
    parts = location.split()
    parts[0] = REGION_ALIASES.get(parts[0], parts[0])
    return " ".join(parts)


def get_json(url, params=None, timeout=20, referer=None):
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
