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


def get_json(url, params=None, timeout=20, referer=None):
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
