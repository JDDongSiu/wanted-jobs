import { useEffect, useMemo, useState } from 'react'
import './App.css'

const EMPLOYMENT_LABELS = {
  regular: '정규직',
  contract: '계약직',
  intern: '인턴',
  freelance: '프리랜서',
  parttime: '파트타임',
}

// 소스별 조건. 각 사이트 고유 태그라 해당 소스 공고에만 적용한다.
// 두 그룹 모두 체크한 것 중 하나라도 해당하면 통과(OR)한다.
const CONDITION_GROUPS = {
  wanted: {
    label: '원티드 조건',
    labels: {
      established: '설립 4년 이상',
      rapid_growth: '인원 급성장',
      equipment: '장비지원',
    },
  },
  jobkorea: {
    label: '잡코리아 복리후생',
    labels: {
      incentive: '인센티브',
      club: '사내 동호회',
      refresh: '리프레시 휴가',
      stock: '스톡옵션',
    },
  },
}

// 지역 필터에서 위로 올릴 순서. 나머지는 가나다순으로 뒤에 붙는다.
const REGION_PRIORITY = ['서울', '경기', '인천', '부산', '충남']

const ALL_CONDITION_LABELS = Object.fromEntries(
  Object.values(CONDITION_GROUPS).flatMap((g) => Object.entries(g.labels)),
)

const SOURCE_LABELS = {
  wanted: '원티드',
  jumpit: '점핏',
  saramin: '사람인',
  jobkorea: '잡코리아',
  catch: '캐치',
}

// 잡플래닛은 평점 데이터를 스크립트로 가져올 수 없어(검색 경로 차단) 링크만 건다.
function jobplanetUrl(company) {
  return `https://www.jobplanet.co.kr/search?query=${encodeURIComponent(company)}`
}

// 상한 없음을 원티드는 100, 잡코리아·사람인은 null 로 표현한다.
function formatCareer(job) {
  const { annual_from: from, annual_to: to, is_newbie: isNewbie } = job
  const open = to == null || to >= 100
  if (from == null && to == null) return '경력무관'
  if (isNewbie) return open ? '신입' : `신입-경력 ${to}년`
  if (open) return `경력 ${from}년 이상`
  return `경력 ${from}-${to}년`
}

function formatUpdatedAt(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function JobCard({ job }) {
  return (
    <div className="card">
      <a className="card-main" href={job.url} target="_blank" rel="noreferrer">
        {job.thumbnail && (
          <img className="card-thumb" src={job.thumbnail} alt="" loading="lazy" />
        )}
        <div className="card-body">
        <span className={`source source-${job.source}`}>
          {SOURCE_LABELS[job.source] ?? job.source}
        </span>
        <h2 className="card-title">{job.position}</h2>
        <p className="card-company">{job.company}</p>
        <p className="card-meta">
          {[job.location, formatCareer(job), EMPLOYMENT_LABELS[job.employment_type]]
            .filter(Boolean)
            .join(' · ')}
        </p>
        {job.category && <p className="card-category">직무 · {job.category}</p>}
        {job.skills?.length > 0 && (
          <p className="card-skills">{job.skills.slice(0, 6).join(' · ')}</p>
        )}
        <div className="card-tags">
          {Object.keys(ALL_CONDITION_LABELS)
            .filter((key) => job.flags?.[key])
            .map((key) => (
              <span key={key} className="tag tag-cond">
                {ALL_CONDITION_LABELS[key]}
              </span>
            ))}
          {job.reward_total && <span className="tag tag-reward">보상금 {job.reward_total}</span>}
        </div>
        </div>
      </a>
      {job.company && (
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
              fill="#fff"
            />
          </svg>
          잡플래닛 평점보기(5점 만점)
        </a>
      )}
    </div>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [conditions, setConditions] = useState(() =>
    Object.fromEntries(Object.keys(ALL_CONDITION_LABELS).map((key) => [key, true])),
  )
  const [region, setRegion] = useState('all')
  const [source, setSource] = useState('all')

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}jobs.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`jobs.json 응답 오류 (${res.status})`)
        return res.json()
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  const regions = useMemo(() => {
    if (!data) return []
    const set = new Set(
      data.jobs.map((job) => job.location?.split(' ')[0]).filter(Boolean),
    )
    const rank = (name) => {
      const i = REGION_PRIORITY.indexOf(name)
      return i === -1 ? REGION_PRIORITY.length : i
    }
    return [...set].sort(
      (a, b) => rank(a) - rank(b) || a.localeCompare(b, 'ko'),
    )
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    const keyword = query.trim().toLowerCase()
    return data.jobs.filter((job) => {
      if (source !== 'all' && job.source !== source) return false

      // 조건은 각 사이트 고유 태그라, 해당 소스의 공고에만 적용한다.
      const group = CONDITION_GROUPS[job.source]
      if (group) {
        const checked = Object.keys(group.labels).filter((key) => conditions[key])
        if (checked.length > 0) {
          if (!checked.some((key) => job.flags?.[key])) return false
        }
      }

      if (region !== 'all' && !job.location?.startsWith(region)) return false
      if (keyword) {
        const haystack = `${job.position} ${job.company}`.toLowerCase()
        if (!haystack.includes(keyword)) return false
      }
      return true
    })
  }, [data, query, conditions, region, source])

  if (error) {
    return (
      <main className="state">
        <p className="state-title">데이터를 불러오지 못했습니다</p>
        <p className="state-desc">{error}</p>
        <p className="state-desc">
          <code>python crawler/build_jobs.py</code> 를 먼저 실행해 주세요.
        </p>
      </main>
    )
  }

  if (!data) return <main className="state">불러오는 중...</main>

  return (
    <>
      <header className="header">
        <div className="header-inner">
          <h1 className="header-title">원티드 프론트엔드 채용공고</h1>
          <p className="header-sub">
            프론트엔드 공고 {data.total_count}건 (
            {Object.entries(data.sources ?? {})
              .map(([key, n]) => `${SOURCE_LABELS[key] ?? key} ${n}`)
              .join(', ')}
            ) · 마지막 갱신 {formatUpdatedAt(data.updated_at)}
          </p>
          {data.stale_sources?.length > 0 && (
            <p className="header-warn">
              {data.stale_sources.map((key) => SOURCE_LABELS[key] ?? key).join(', ')}{' '}
              수집에 실패해 이전 데이터를 표시하고 있습니다
            </p>
          )}
        </div>
      </header>

      <main className="main">
        <section className="filters">
          <input
            className="search"
            type="search"
            placeholder="포지션 또는 회사명 검색"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
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
          </div>
          <details className="cond-panel">
            <summary className="cond-summary">사이트별 보기 옵션 설정</summary>
            {Object.entries(CONDITION_GROUPS).map(([source, group]) => (
              <div className="cond-group" key={source}>
                <span className="cond-group-label">{group.label}</span>
                {Object.entries(group.labels).map(([key, label]) => (
                  <label className="check" key={key}>
                    <input
                      type="checkbox"
                      checked={conditions[key]}
                      onChange={(e) =>
                        setConditions((prev) => ({ ...prev, [key]: e.target.checked }))
                      }
                    />
                    {label}
                  </label>
                ))}
              </div>
            ))}
          </details>

          <p className="result-count">{filtered.length}건</p>
        </section>

        {filtered.length === 0 ? (
          <p className="empty">조건에 맞는 공고가 없습니다.</p>
        ) : (
          <section className="grid">
            {filtered.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </section>
        )}
      </main>
    </>
  )
}
