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

`.github/workflows/update-jobs.yml` 이 매일 06:00(KST)에 크롤러를 돌려
`public/jobs.json` 을 갱신하고 커밋한다. GitHub에 저장소를 올린 뒤부터 동작한다.
사람인까지 수집하려면 저장소 Settings → Secrets 에 `SARAMIN_API_KEY` 를 등록한다.
수동 실행은 Actions 탭의 `Run workflow` 로 가능하다.

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
| `jobs[].flags` | 조건별 충족 여부 (원티드만, 나머지는 빈 객체) |
