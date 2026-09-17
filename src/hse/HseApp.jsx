import { useEffect, useMemo, useState } from 'react'
import '../App.css'
import './hse.css'

const SOURCE_LABELS = {
  jobkorea: '잡코리아',
  catch: '캐치',
  peoplenjob: '피플앤잡',
  naverblog: '네이버블로그',
}

// 지역 필터에서 위로 올릴 순서. 나머지는 가나다순으로 뒤에 붙는다.
const REGION_PRIORITY = ['서울', '경기', '인천', '부산', '충남']

// 요구경력 구간. 사이트마다 표기가 달라 최소 경력 기준으로 묶는다.
// 피플앤잡은 연차 대신 직급을, 블로그 글은 아무것도 적지 않아 '미표기'를 따로 둔다.
const CAREER_BUCKETS = [
  { key: 'newbie', label: '신입' },
  { key: '1-3', label: '1-3년' },
  { key: '4-6', label: '4-6년' },
  { key: '7-9', label: '7-9년' },
  { key: '10+', label: '10년 이상' },
  { key: 'any', label: '경력무관' },
  { key: 'unknown', label: '경력 미표기' },
]

function careerBucket(job) {
  if (job.is_newbie) return 'newbie'
  const from = job.annual_from
  if (from != null) {
    if (from <= 3) return '1-3'
    if (from <= 6) return '4-6'
    if (from <= 9) return '7-9'
    return '10+'
  }
  if (job.career_text?.includes('무관')) return 'any'
  return 'unknown'
}

// 공고를 처음 본 날짜로 묶는다. 블로그 글은 글이 올라온 날이 그 자리에 들어간다.
const DAY_GROUPS = [
  { key: 'today', label: '오늘' },
  { key: 'yesterday', label: '어제' },
  { key: 'week', label: '최근 7일' },
  { key: 'older', label: '이전' },
]

function daysAgo(isoDate) {
  const seen = new Date(`${isoDate}T00:00:00+09:00`)
  const now = new Date()
  const todayKst = new Date(
    `${now.toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' })}T00:00:00+09:00`,
  )
  return Math.round((todayKst - seen) / 86400000)
}

function dayGroup(job) {
  if (!job.first_seen) return 'older'
  const diff = daysAgo(job.first_seen)
  if (diff <= 0) return 'today'
  if (diff === 1) return 'yesterday'
  if (diff <= 7) return 'week'
  return 'older'
}

// 잡플래닛은 평점 데이터를 스크립트로 가져올 수 없어(검색 경로 차단) 링크만 건다.
function jobplanetUrl(company) {
  return `https://www.jobplanet.co.kr/search?query=${encodeURIComponent(company)}`
}

function formatUpdatedAt(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function readParams() {
  return new URLSearchParams(window.location.search)
}

function JobCard({ job, isNew }) {
  // 블로그 글은 글쓴이가 회사가 아니라서 잡플래닛을 걸 곳이 없다.
  const hasCompanyPage = job.source !== 'naverblog' && job.company

  const meta = [job.company, job.location, job.career_text, job.employment_type]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="card">
      <a className="card-main" href={job.url} target="_blank" rel="noreferrer">
        <div className="card-head">
          {isNew && <span className="badge-new">NEW</span>}
          <span className={`source source-${job.source}`}>
            {SOURCE_LABELS[job.source] ?? job.source}
          </span>
        </div>
        <h2 className="card-title">{job.position}</h2>
        <p className={`card-meta${meta ? '' : ' card-meta-faint'}`}>
          {meta || '지역·경력 미표기'}
        </p>
        {job.category && <p className="card-category">직무 · {job.category}</p>}
      </a>
      {hasCompanyPage && (
        <a
          className="card-jp"
          href={jobplanetUrl(job.company)}
          target="_blank"
          rel="noreferrer"
        >
          <svg className="jp-mark" viewBox="0 0 16 16" aria-hidden="true">
            <circle cx="8" cy="8" r="8" fill="currentColor" />
            <path
              d="M5 4.4h5.2v6.1a2.6 2.6 0 0 1-2.6 2.6A2.6 2.6 0 0 1 5 10.5h1.9a.7.7 0 0 0 1.4 0V6.3H5z"
              fill="#14161a"
            />
          </svg>
          잡플래닛 평점보기(5점 만점)
        </a>
      )}
    </div>
  )
}

export default function HseApp() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [region, setRegion] = useState(() => readParams().get('region') ?? 'all')
  const [source, setSource] = useState(() => readParams().get('source') ?? 'all')
  const [career, setCareer] = useState(() => readParams().get('career') ?? 'all')

  // 필터 상태를 주소에 남긴다. 공고 링크를 눌렀다가 뒤로 와도 필터가 유지된다.
  useEffect(() => {
    const params = new URLSearchParams()
    if (source !== 'all') params.set('source', source)
    if (region !== 'all') params.set('region', region)
    if (career !== 'all') params.set('career', career)

    const search = params.toString()
    window.history.replaceState(
      null,
      '',
      search ? `?${search}` : window.location.pathname,
    )
  }, [source, region, career])

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}jobs-hse.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`jobs-hse.json 응답 오류 (${res.status})`)
        return res.json()
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  const regions = useMemo(() => {
    if (!data) return []
    const set = new Set(data.jobs.map((job) => job.region).filter(Boolean))
    const rank = (name) => {
      const i = REGION_PRIORITY.indexOf(name)
      return i === -1 ? REGION_PRIORITY.length : i
    }
    return [...set].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b, 'ko'))
  }, [data])

  // 구간별 건수를 함께 보여준다. 고르기 전에 몇 건인지 알 수 있다.
  const careerCounts = useMemo(() => {
    const counts = {}
    for (const job of data?.jobs ?? []) {
      const key = careerBucket(job)
      counts[key] = (counts[key] ?? 0) + 1
    }
    return counts
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    return data.jobs.filter((job) => {
      if (source !== 'all' && job.source !== source) return false
      if (region !== 'all' && job.region !== region) return false
      if (career !== 'all' && careerBucket(job) !== career) return false
      return true
    })
  }, [data, region, career, source])

  // 처음 본 날짜로 묶어 새로 올라온 공고가 위로 오게 한다.
  const grouped = useMemo(() => {
    const buckets = Object.fromEntries(DAY_GROUPS.map((g) => [g.key, []]))
    for (const job of filtered) buckets[dayGroup(job)].push(job)
    return DAY_GROUPS.map((g) => ({ ...g, jobs: buckets[g.key] })).filter(
      (g) => g.jobs.length > 0,
    )
  }, [filtered])

  if (error) {
    return (
      <main className="state">
        <p className="state-title">데이터를 불러오지 못했습니다</p>
        <p className="state-desc">{error}</p>
        <p className="state-desc">
          <code>python crawler/build_hse.py</code> 를 먼저 실행해 주세요.
        </p>
      </main>
    )
  }

  if (!data) return <main className="state">불러오는 중...</main>

  return (
    <div className="content">
      <header className="header">
        <div className="header-inner">
          <span className="hse-title">
            라보<span className="hero-ext">.azit</span>
            <span className="hse-title-ext"> 보건·HSE</span>
          </span>
          <span className="header-sub">
            {Object.entries(data.sources ?? {})
              .map(([key, n]) => `${SOURCE_LABELS[key] ?? key} ${n}`)
              .join(' · ')}{' '}
            · 갱신 {formatUpdatedAt(data.updated_at)}
          </span>
          {data.stale_sources?.length > 0 && (
            <span className="header-warn">
              {data.stale_sources.map((key) => SOURCE_LABELS[key] ?? key).join(', ')}{' '}
              수집 실패 · 이전 데이터 표시 중
            </span>
          )}
        </div>
      </header>

      <main className="main">
        <section className="filters">
          <div className="filter-row">
            <select
              className="select"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            >
              <option value="all">전체 사이트</option>
              {Object.keys(data.sources ?? {}).map((key) => (
                <option key={key} value={key}>
                  {SOURCE_LABELS[key] ?? key} ({data.sources[key]})
                </option>
              ))}
            </select>
            <select
              className="select"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            >
              <option value="all">전체 지역</option>
              {regions.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <select
              className="select"
              value={career}
              onChange={(e) => setCareer(e.target.value)}
            >
              <option value="all">전체 경력</option>
              {CAREER_BUCKETS.filter(({ key }) => careerCounts[key]).map(
                ({ key, label }) => (
                  <option key={key} value={key}>
                    {label} ({careerCounts[key]})
                  </option>
                ),
              )}
            </select>
            <span className="result-count">{filtered.length}건</span>
          </div>
        </section>

        {grouped.length === 0 ? (
          <p className="empty">조건에 맞는 공고가 없습니다.</p>
        ) : (
          <div className="timeline">
            {grouped.map((group) => (
              <section className="day" key={group.key}>
                <div className="day-label">
                  <span className="day-name">{group.label}</span>
                  <span className="day-count">{group.jobs.length}건</span>
                </div>
                <div
                  className={`day-rail${group.key === 'today' ? ' day-rail-new' : ''}`}
                />
                <div className="day-jobs">
                  {group.jobs.map((job) => (
                    <JobCard key={job.id} job={job} isNew={group.key === 'today'} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
