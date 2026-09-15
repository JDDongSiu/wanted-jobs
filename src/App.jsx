import { useEffect, useId, useMemo, useRef, useState } from 'react'
import Quote from './quote/quote.tsx'
import Character from './characters/charactes.tsx'
import './App.css'
import './characters/characters-interactive.css'


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
    label: '원티드',
    labels: {
      established: '설립 4년 이상',
      rapid_growth: '인원 급성장',
      equipment: '장비지원',
    },
  },
  jobkorea: {
    label: '잡코리아',
    labels: {
      incentive: '인센티브',
      club: '사내 동호회',
      refresh: '리프레시 휴가',
      stock: '스톡옵션',
    },
  },
}

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

// 지역 필터에서 위로 올릴 순서. 나머지는 가나다순으로 뒤에 붙는다.
const REGION_PRIORITY = ['서울', '경기', '인천', '부산', '충남']

// 요구경력 구간. 사이트마다 표기가 달라 최소 경력 기준으로 묶는다.
const CAREER_BUCKETS = [
  { key: 'newbie', label: '신입' },
  { key: '1-3', label: '1-3년' },
  { key: '4-6', label: '4-6년' },
  { key: '7-9', label: '7-9년' },
  { key: '10+', label: '10년 이상' },
  { key: 'any', label: '경력무관' },
]

function careerBucket(job) {
  if (job.is_newbie) return 'newbie'
  const from = job.annual_from
  if (from == null) return 'any'
  if (from <= 3) return '1-3'
  if (from <= 6) return '4-6'
  if (from <= 9) return '7-9'
  return '10+'
}

// 공고를 처음 본 날짜로 묶는다. first_seen 이 없는 건 기록을 시작하기 전부터
// 있던 공고라 언제 올라왔는지 알 수 없으므로 '이전'으로 보낸다.
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

// 필터 상태를 주소에 남긴다. 공고 링크를 눌렀다가 뒤로 와도 필터가 유지된다.
// 기본값이 모두 켜짐이라, 꺼둔 조건만 off 로 기록해 주소를 짧게 유지한다.
function readParams() {
  return new URLSearchParams(window.location.search)
}

function initialConditions() {
  const off = new Set((readParams().get('off') ?? '').split(',').filter(Boolean))
  return Object.fromEntries(
    Object.keys(ALL_CONDITION_LABELS).map((key) => [key, !off.has(key)]),
  )
}

// 토끼와 강아지. 두 캐릭터 모두 몸을 여러 조각으로 나눠 그리되,
// 조각 경계선이 보이지 않도록 합집합의 바깥 윤곽만 남긴다.
// 강아지는 원 두 개의 교점을 계산해 호로 잇고, 토끼는 조각을 두 번 겹쳐 그린다.
const INK = '#4A3B25'
const LW = 2.6
const FUR = '#FAE8B4' // 토끼 몸 색
const RABBIT_LW = 1.9 // 토끼는 선을 더 가늘게 쓴다
// 토끼 몸을 이루는 조각들. 아래에서 두 번 그려 합집합 윤곽만 남긴다.
// 몸통은 위가 넓고 아래로 갈수록 좁아지며, 발 사이가 벌어져 Y 자로 갈라진다.
const HEAD_TILT = 'rotate(7 76 100)'
const RABBIT_PARTS = (
  <>
    <rect x="62" y="8" width="13" height="54" rx="6.5" transform={`${HEAD_TILT} rotate(-9 68.5 60)`} />
    <rect x="77" y="8" width="13" height="54" rx="6.5" transform={`${HEAD_TILT} rotate(9 83.5 60)`} />
    <path
      d="M76 40C102.94 40 114 49.31 114 72C114 94.69 102.94 104 76 104C49.06 104 38 94.69 38 72C38 49.31 49.06 40 76 40Z"
      transform={HEAD_TILT}
    />
    <path
      d="M49.5 88L56 118C56 123.5 64 125.5 76 125.5C88 125.5 96 123.5 96 118L102.5 88Z"
      transform="rotate(-5 76 125)"
    />
    <ellipse cx="98" cy="110" rx="2.8" ry="4.8" transform="rotate(10 98 110)" />
    <ellipse cx="67" cy="129" rx="5" ry="5" />
    <ellipse cx="85" cy="129" rx="5" ry="5" />
  </>
)

// 앞으로 들어올린 팔. 몸을 그린 뒤에 얹어야 앞뒤가 읽힌다.
const RABBIT_ARM = (
  <>
    <ellipse cx="64" cy="107" rx="2.8" ry="6" transform="rotate(35 64 107)" />
    <circle cx="68" cy="100" r="2.5" />
  </>
)
const DOG_LW = 1.9
// 바깥 윤곽은 하나로 이어지고, 얼굴과 몸의 구분은 턱선 하나로만 준다.
// 몸통을 머리 아래 너비보다 조금 넓게 잡아 턱선이 몸 안쪽에 들어오게 했다.
const DOG_TILT = 'rotate(-6 76 58)'
const DOG_HEAD =
  'M64 24C52 24 44 32 44 44L44 86C44 94 50 98 58 98L94 98C102 98 108 94 108 86L108 44C108 32 100 24 88 24Z'
const DOG_PARTS = (
  <>
    <ellipse cx="46" cy="40" rx="8.8" ry="12" transform={`${DOG_TILT} rotate(20 46 40)`} />
    <ellipse cx="107" cy="39" rx="9.2" ry="11.5" transform={`${DOG_TILT} rotate(-30 107 39)`} />
    <path d={DOG_HEAD} transform={DOG_TILT} />
    <path d="M54 88L58 116C58 121 94 121 94 116L98 88Z" />
    <ellipse cx="54" cy="104" rx="3.5" ry="6" transform="rotate(-6 54 104)" />
    <ellipse cx="98" cy="104" rx="3.5" ry="6" transform="rotate(6 98 104)" />
    <rect x="67" y="116" width="6" height="12" rx="3" />
    <rect x="81" y="116" width="6" height="12" rx="3" />
  </>
)

// mascots.html 미리보기 페이지에서도 쓴다

function JobCard({ job, isNew }) {
  return (
    <div className="card">
      <a className="card-main" href={job.url} target="_blank" rel="noreferrer">
        <div className="card-head">
          {isNew && <span className="badge-new">NEW</span>}
          <span className={`source source-${job.source}`}>
            {SOURCE_LABELS[job.source] ?? job.source}
          </span>
          {job.reward_total && (
            <span className="card-reward">보상금 {job.reward_total}</span>
          )}
        </div>
        <h2 className="card-title">{job.position}</h2>
        <p className="card-meta">
          {[
            job.company,
            job.location,
            formatCareer(job),
            EMPLOYMENT_LABELS[job.employment_type] ?? job.employment_type,
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>
        {job.category && <p className="card-category">직무 · {job.category}</p>}
        {(job.skills?.length > 0 ||
          Object.keys(ALL_CONDITION_LABELS).some((key) => job.flags?.[key])) && (
          <div className="card-tags">
            {Object.keys(ALL_CONDITION_LABELS)
              .filter((key) => job.flags?.[key])
              .map((key) => (
                <span key={key} className="tag tag-cond">
                  {ALL_CONDITION_LABELS[key]}
                </span>
              ))}
            {job.skills?.slice(0, 6).map((skill) => (
              <span key={skill} className="tag tag-skill">
                {skill}
              </span>
            ))}
          </div>
        )}
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
              fill="#14161a"
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
  const [query, setQuery] = useState(() => readParams().get('q') ?? '')
  const [conditions, setConditions] = useState(initialConditions)
  const [region, setRegion] = useState(() => readParams().get('region') ?? 'all')
  const [source, setSource] = useState(() => readParams().get('source') ?? 'all')
  const [career, setCareer] = useState(() => readParams().get('career') ?? 'all')

  useEffect(() => {
    const params = new URLSearchParams()
    if (query) params.set('q', query)
    if (source !== 'all') params.set('source', source)
    if (region !== 'all') params.set('region', region)
    if (career !== 'all') params.set('career', career)

    const off = Object.keys(conditions).filter((key) => !conditions[key])
    if (off.length) params.set('off', off.join(','))

    const search = params.toString()
    window.history.replaceState(
      null,
      '',
      search ? `?${search}` : window.location.pathname,
    )
  }, [query, source, region, career, conditions])

  // 스냅은 표지와 목록 첫머리 사이에서만 쓸모가 있다. 목록 안으로 충분히 들어오면
  // 꺼버려서, 아래 정보를 읽을 때는 아무것도 걸리지 않게 한다.
  const snapLocked = useRef(false)
  useEffect(() => {
    const html = document.documentElement
    const apply = () => {
      if (snapLocked.current) return
      const hero = document.querySelector('.hero')
      const limit = (hero?.offsetHeight ?? 0) * 1.5
      html.style.scrollSnapType = window.scrollY > limit ? 'none' : ''
    }
    apply()
    window.addEventListener('scroll', apply, { passive: true })
    window.addEventListener('resize', apply)
    return () => {
      window.removeEventListener('scroll', apply)
      window.removeEventListener('resize', apply)
      html.style.scrollSnapType = ''
    }
  }, [])

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
    const keyword = query.trim().toLowerCase()
    return data.jobs.filter((job) => {
      if (source !== 'all' && job.source !== source) return false

      // 조건은 각 사이트 고유 태그라, 해당 소스의 공고에만 적용한다.
      const group = CONDITION_GROUPS[job.source]
      if (group) {
        const checked = Object.keys(group.labels).filter((key) => conditions[key])
        if (checked.length > 0 && !checked.some((key) => job.flags?.[key])) {
          return false
        }
      }

      if (region !== 'all' && !job.location?.startsWith(region)) return false
      if (career !== 'all' && careerBucket(job) !== career) return false
      if (keyword) {
        const haystack = `${job.position} ${job.company}`.toLowerCase()
        if (!haystack.includes(keyword)) return false
      }
      return true
    })
  }, [data, query, conditions, region, career, source])

  // 처음 본 날짜로 묶어 새로 올라온 공고가 위로 오게 한다.
  const grouped = useMemo(() => {
    const buckets = Object.fromEntries(DAY_GROUPS.map((g) => [g.key, []]))
    for (const job of filtered) buckets[dayGroup(job)].push(job)
    return DAY_GROUPS.map((g) => ({ ...g, jobs: buckets[g.key] })).filter(
      (g) => g.jobs.length > 0,
    )
  }, [filtered])

  const scrollToList = () => {
    const el = document.getElementById('list')
    if (!el) return

    const html = document.documentElement
    const target = el.offsetTop

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      window.scrollTo(0, target)
      return
    }

    // 미끄러지는 동안 스냅이 끼어들지 않게 잠가둔다
    snapLocked.current = true
    html.style.scrollSnapType = 'none'
    window.scrollTo({ top: target, behavior: 'smooth' })

    window.setTimeout(() => {
      // 탭이 숨겨져 있으면 브라우저가 부드러운 스크롤을 돌리지 않는다. 그때는 바로 맞춘다.
      if (Math.abs(window.scrollY - target) > 2) window.scrollTo(0, target)
      snapLocked.current = false
      html.style.scrollSnapType = ''
    }, 800)
  }

  // 표지에서는 한 번만 밀어도 목록까지 내려간다. 조금씩 걸쳐 멈추지 않게 한다.
  useEffect(() => {
    const onCover = () => {
      const hero = document.querySelector('.hero')
      return hero ? window.scrollY < hero.offsetHeight * 0.5 : false
    }

    const glide = (event) => {
      if (snapLocked.current || !onCover()) return
      event.preventDefault()
      scrollToList()
    }

    const onWheel = (event) => {
      if (event.deltaY > 0) glide(event)
    }

    const onKey = (event) => {
      const tag = event.target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (['ArrowDown', 'PageDown', ' '].includes(event.key)) glide(event)
    }

    let touchStart = 0
    const onTouchStart = (event) => {
      touchStart = event.touches[0].clientY
    }
    const onTouchMove = (event) => {
      if (touchStart - event.touches[0].clientY > 12) glide(event)
    }

    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('keydown', onKey)
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: false })
    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
    }
  }, [])

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

  const newCount = data.new_count ?? 0

  // 헤더가 sticky 라 scrollIntoView 가 듣지 않고, 스냅이 켜져 있으면 브라우저의
  // 부드러운 스크롤을 표지로 되돌려버린다. 그래서 직접 애니메이션하고 그동안 스냅을 끈다.
  return (
    <>
      <section className="hero">
  {/* 위 1/3 은 흰 바탕. 캐릭터가 그 경계선 위에 서 있다 */}
<div className="hero-sky">
  <Character priority />
</div>


  <div className="hero-inner">
    <h1 className="hero-brand">
      라보<span className="hero-ext">.azit</span>
    </h1>

    <Quote />

    <button
      className="hero-scroll"
      type="button"
      onClick={scrollToList}
    >
      <span>아래로 내려서 보기</span>

      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </button>
  </div>
</section>

      <div className="content" id="list">
      <header className="header">
        <div className="header-inner">
          <span className="header-brand">
            라보<span className="hero-ext">.azit</span>
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
          <div className="search-wrap">
            <svg
              className="search-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.2-3.2" />
            </svg>
            <input
              className="search"
              type="search"
              placeholder="포지션, 회사, 기술스택으로 검색해보세요"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

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
            <details className="cond-panel">
              <summary className="cond-summary">사이트별 보기 옵션 설정</summary>
              <div className="cond-popover">
                {Object.entries(CONDITION_GROUPS).map(([key, group]) => (
                  <div className="cond-group" key={key}>
                    <span className="cond-group-label">{group.label}</span>
                    {Object.entries(group.labels).map(([condKey, label]) => (
                      <label className="check" key={condKey}>
                        <input
                          type="checkbox"
                          checked={conditions[condKey]}
                          onChange={(e) =>
                            setConditions((prev) => ({
                              ...prev,
                              [condKey]: e.target.checked,
                            }))
                          }
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                ))}
              </div>
            </details>
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
    </>
  )
}
