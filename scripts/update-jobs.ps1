# 이 PC에서 채용공고를 수집해 GitHub에 올린다.
# 원티드와 캐치가 클라우드 IP를 차단해서 GitHub Actions 에서는 두 곳 수집이 안 된다.
# 프론트엔드(build_jobs.py)와 보건관리자(build_hse.py) 둘 다 여기서 수집해 올린다.
# 푸시가 일어나면 GitHub Actions 가 이어받아 사이트를 다시 배포한다.
#
# 작업 스케줄러 등록은 scripts/register-task.ps1 참고.

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $projectRoot 'logs'
$logFile = Join-Path $logDir ('update-{0}.log' -f (Get-Date -Format 'yyyy-MM'))

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$utf8 = New-Object System.Text.UTF8Encoding $false

function Write-Log {
    param([string]$Message)
    $line = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Write-Output $line
    [System.IO.File]::AppendAllText($logFile, $line + [Environment]::NewLine, $utf8)
}

# git 은 정상 진행 상황도 stderr 로 낸다. PowerShell 은 그걸 오류로 취급해
# $ErrorActionPreference='Stop' 에서 멈춰버리므로, 종료 코드로만 성공을 판단한다.
function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & git @Arguments 2>&1 | ForEach-Object { $_.ToString() }
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    foreach ($line in $output) {
        if ($line.Trim()) { Write-Log ('  ' + $line) }
    }
    if ($code -ne 0) {
        throw ('git {0} 실패 (exit {1})' -f ($Arguments -join ' '), $code)
    }
    return $output
}

# 두 사이트의 크롤러가 같은 방식으로 돈다.
function Invoke-Crawler {
    param([string]$Script)

    $output = & python (Join-Path $projectRoot $Script) 2>&1 |
        ForEach-Object { $_.ToString() }
    $code = $LASTEXITCODE
    foreach ($line in $output) {
        if ($line.Trim()) { Write-Log ('  ' + $line) }
    }
    if ($code -ne 0) {
        throw ('{0} 실패 (exit {1})' -f $Script, $code)
    }
}

try {
    # 작업 스케줄러는 로그인 세션의 PATH를 물려받지 않는다.
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:PYTHONIOENCODING = 'utf-8'

    # 작업 스케줄러로 실행하면 출력 코드페이지가 cp949 라서
    # UTF-8 로 나오는 파이썬 출력이 깨진 채로 기록된다.
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

    Set-Location $projectRoot
    Write-Log '=== 수집 시작 ==='

    # 작업 중인 변경을 건드리지 않도록, 데이터 파일 외 변경이 없을 때만 진행한다.
    $dirty = & git status --porcelain -- . `
        ':!public/jobs.json' ':!jobs.csv' ':!public/jobs-hse.json' ':!jobs-hse.csv'
    if ($dirty) {
        throw ('커밋하지 않은 변경이 있어 중단합니다: {0}' -f ($dirty -join ', '))
    }

    # 원격이 앞서 있을 수 있다 (GitHub Actions 가 점핏 데이터를 커밋한다).
    Invoke-Git pull --rebase origin main | Out-Null

    $env:PYTHONPATH = Join-Path $projectRoot 'crawler'
    Invoke-Crawler 'crawler\build_jobs.py'
    Invoke-Crawler 'crawler\build_hse.py'

    Invoke-Git add public/jobs.json jobs.csv public/jobs-hse.json jobs-hse.csv | Out-Null

    & git diff --staged --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Log '데이터 변경 없음. 푸시를 건너뜁니다.'
        Write-Log '=== 완료 ==='
        exit 0
    }

    Invoke-Git commit -m 'chore: update job data (local)' | Out-Null
    Invoke-Git push origin main | Out-Null

    Write-Log '푸시 완료. GitHub Actions 가 사이트를 재배포합니다.'
    Write-Log '=== 완료 ==='
}
catch {
    Write-Log ('오류: {0}' -f $_.Exception.Message)
    exit 1
}
