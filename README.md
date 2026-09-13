# 프론트엔드 채용공고 모음

원티드·점핏·사람인의 프론트엔드 개발자 공고를 모아서 웹으로 보는 사이트.

## 구조

```
crawler/wanted.py   ┐
crawler/jumpit.py   ├→ crawler/build_jobs.py → public/jobs.json → React 화면
crawler/saramin.py  ┘                        └→ jobs.csv
```

크롤러가 JSON을 만들고 화면은 그 JSON만 읽는다. 별도 백엔드 서버가 없다.

## 수집 소스

| 소스 | 방식 | 비고 |
| --- | --- | --- |
| 원티드 | 비공식 API (`api/chaos/navigation/v1/results`) | 공식 문서 없음. 사이트 변경 시 깨질 수 있음 |
| 점핏 | 비공식 API (`jumpit-api.saramin.co.kr/api/positions`) | 위와 같음 |
| 사람인 | 공식 오픈 API (`oapi.saramin.co.kr/job-search`) | `access-key` 필요. 일일 요청 한도 있음 |
| 잡코리아 | HTML 파싱 (`Recruit/Home/_GI_List/`) | 공식 API 없음. 마크업 변경 시 깨질 수 있음 |
| 캐치 | 비공식 API (`api/v1.0/recruit/information/getRecruitList`) | robots.txt 가 로그 경로만 금지 |

### 수집 대상 선정과 robots.txt

각 사이트의 robots.txt 에서 일반 크롤러(`User-agent: *`) 규칙을 확인하고 정했다.

- **잡코리아**: `/recruit/joblist` 와 `/Recruit/GI_Read` 를 **명시적으로 허용**한다.
  금지된 것은 로그인·회원 영역과 검색 쿼리 URL(`/Search?TS_Search=`) 이라 목록 수집에는 해당하지 않는다.
- **캐치**: `Allow: /` 이고 `/api/v1.0/recruit/` 중 로그 수집 경로만 금지한다. 목록 조회는 해당 없다.
- **인크루트**: `User-agent: *` 에 `Disallow: /` — 전면 금지라 **수집 대상에서 제외**했다.
- **링크드인**: `User-agent: *` 에 `Disallow: /` 이고, 크롤링하려면 화이트리스트를 신청하라고
  robots.txt 에 명시했다. **제외**.
- **로켓펀치**: 허용되어 있어 추가 후보다.

### 수집하지 못한 곳

- **인디드**: robots.txt 는 허용하지만 실제 요청이 모두 403 이다(루트 페이지 포함). 봇 차단.
- **프로그래머스**: `career.programmers.co.kr` 서브도메인이 없어졌다. 채용 서비스 자체가 사라졌다.
- **리멤버**: 목록이 전부 클라이언트 렌더링이라 HTML 에 공고 데이터가 없다.
  수집하려면 headless 브라우저가 필요해 비용 대비 효과가 낮다고 보고 보류했다.
- **잡플래닛 평점**: 회사명으로 평점을 찾으려면 검색이 필요한데,
  검색 페이지는 robots.txt 가 금지하고 검색 API 는 스크립트에서 400/403 이다.
  대신 카드마다 잡플래닛 검색 링크를 걸어 클릭으로 확인하게 했다.

사람인은 환경변수 `SARAMIN_API_KEY` 로 키를 넘긴다. 키가 없으면 사람인만 건너뛰고 나머지는 정상 수집한다.

```bash
# Windows PowerShell
$env:SARAMIN_API_KEY = "발급받은키"
```

## 실행

데이터 갱신:

```bash
python crawler/build_jobs.py
```

개발 서버:

```bash
npm run dev
```

배포용 빌드:

```bash
npm run build
```

## 필터 조건

기본 화면은 아래 조건을 모두 충족한 공고만 보여주고, 체크박스로 조건을 풀면 범위가 넓어진다.

- **설립 4년 이상** (설립4~9년 `10408` 또는 설립10년이상 `10409`)
- **인원 급성장** (`10401`)
- **장비지원** (`10439`)

**이 조건은 원티드 공고에만 적용된다.** 원티드 고유의 기업 태그라 점핏·사람인에는
대응하는 값이 없기 때문이다. 다른 소스의 공고는 조건과 무관하게 표시되며,
카드의 출처 배지와 상단의 사이트 선택으로 구분한다.

조건은 `crawler/wanted.py` 의 `CONDITIONS` 에서 바꾼다.
화면의 체크박스는 `src/App.jsx` 의 `CONDITION_LABELS` 가 같은 키를 쓴다.

## 프론트엔드 공고 선별 기준

채용사이트들은 '프론트엔드' 직무로 조회해도, 그 직무를 **부가로만** 단 공고까지 함께 준다.
실제로 서버 개발자·DevOps·프로덕트 매니저 공고가 섞여 들어온다.

그렇다고 대표 직무가 프론트엔드인 공고만 남기면, 진짜 프론트엔드 공고를
`웹 개발자` 로 등록한 회사가 많아 정상 공고가 대거 잘려나간다.

그래서 **대표 직무가 프론트엔드이거나, 제목에 프론트엔드 키워드가 있는 공고**만 남긴다
(각 소스 모듈의 `is_frontend`). 원티드 354 → 192건, 점핏 68 → 25건.

## 자동 갱신

갱신 경로가 두 개다. **원티드가 클라우드 IP를 차단(403)하기 때문이다.**

| | 실행 위치 | 주기 | 원티드 수집 | 저장소에 커밋 |
| --- | --- | --- | --- | --- |
| GitHub Actions | GitHub 서버 | 매일 06:00 KST | 실패 (403) | 안 함 |
| 작업 스케줄러 | 이 PC | 매일 09:00 | 정상 | 함 |

GitHub Actions 에서 원티드는 403 으로 실패하지만, 그 경우 **직전 데이터를 그대로 유지**하므로
기존 공고가 사라지지 않는다. 화면 상단에도 "이전 데이터를 표시하고 있습니다" 안내가 뜬다.
점핏·잡코리아·사람인은 양쪽 모두에서 정상 수집된다.

**데이터 파일을 커밋하는 쪽은 이 PC 하나뿐이다.** 양쪽이 함께 커밋하면
`public/jobs.json` 을 두고 매번 리베이스 충돌이 난다. CI 는 커밋하지 않아도
그 실행에서 새로 수집한 데이터로 사이트를 배포하므로, 커밋할 이유가 없다.
저장소의 데이터는 CI 가 원티드를 못 가져올 때 쓰는 직전 값으로 남는다.

브라우저와 동일한 헤더를 붙여도 403 이라 IP 기반 차단으로 판단했다.
프록시로 우회하는 대신, 일반 가정용 회선인 이 PC에서 수집한다.

### 작업 스케줄러 등록

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register-task.ps1
```

`scripts/update-jobs.ps1` 이 수집 → 커밋 → 푸시를 수행하고, 푸시가 일어나면
GitHub Actions 가 이어받아 사이트를 재배포한다. 실행 기록은 `logs/` 에 월별로 쌓인다.
PC가 꺼져 있어 놓친 일정은 켜진 뒤에 실행된다(`StartWhenAvailable`).

바로 실행해 보려면:

```powershell
Start-ScheduledTask -TaskName "wanted-jobs 수집"
```

해제하려면:

```powershell
Unregister-ScheduledTask -TaskName "wanted-jobs 수집" -Confirm:$false
```

### 사람인 키 등록

저장소 Settings → Secrets and variables → Actions 에 `SARAMIN_API_KEY` 를 등록한다.
이 PC에서는 환경변수로 넣는다.

## 배포

`https://<계정>.github.io/<저장소명>/` 으로 배포된다.

수집과 배포를 한 워크플로에 합쳐 두었다. GITHUB_TOKEN 으로 만든 커밋은 다른 워크플로를
트리거하지 않아서, 배포를 분리하면 데이터 갱신 후 배포가 실행되지 않기 때문이다.

## 데이터

`public/jobs.json` 형식:

| 필드 | 설명 |
| --- | --- |
| `updated_at` | 수집 시각 (KST) |
| `sources` | 소스별 수집 건수 |
| `total_count` | 전체 공고 수 |
| `matched_count` | 원티드 조건을 모두 충족한 공고 수 |
| `jobs[].source` | `wanted` / `jumpit` / `saramin` |
| `jobs[].category` | 공고의 직무 |
| `jobs[].skills` | 기술스택 (점핏·사람인) |
| `jobs[].flags` | 조건별 충족 여부 (해당 소스만, 나머지는 빈 객체) |
| `jobs[].first_seen` | 공고를 처음 본 날짜 (YYYY-MM-DD) |
| `new_count` | 이번 수집에서 처음 나타난 공고 수 |

`first_seen` 은 직전 `public/jobs.json` 에 없던 공고에만 오늘 날짜를 찍는다.
이 기능을 넣기 전부터 있던 공고는 언제 올라왔는지 알 수 없어 `null` 로 둔다.
오늘 날짜를 찍으면 전부 신착으로 보이기 때문이다.

화면의 요구경력 필터는 `annual_from` 과 `is_newbie` 로 구간을 나눈다
(`src/App.jsx` 의 `careerBucket`). 사이트마다 경력 표기가 달라 최소 경력을 기준으로 묶는다.
