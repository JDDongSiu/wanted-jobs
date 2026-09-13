# 이 PC에서 채용공고를 수집해 GitHub에 올린다.
# 원티드가 클라우드 IP를 차단해서 GitHub Actions에서는 원티드 수집이 안 된다.
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

function Write-Log {
    param([string]$Message)
    $line = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

try {
    # 작업 스케줄러는 로그인 세션의 PATH를 물려받지 않는다.
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:PYTHONIOENCODING = 'utf-8'

    Set-Location $projectRoot
    Write-Log '=== 수집 시작 ==='

    # 작업 중인 변경을 건드리지 않도록, 깨끗한 상태에서만 진행한다.
    $dirty = git status --porcelain -- . ':!public/jobs.json' ':!jobs.csv'
    if ($dirty) {
        throw "커밋하지 않은 변경이 있어 중단합니다. 먼저 정리해 주세요:`n$dirty"
    }

    # 원격이 앞서 있을 수 있다 (GitHub Actions 가 점핏 데이터를 커밋한다).
    git pull --rebase origin main 2>&1 | ForEach-Object { Write-Log $_ }

    $output = python crawler/build_jobs.py 2>&1
    $output | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "크롤러가 실패했습니다 (exit $LASTEXITCODE)"
    }

    git add public/jobs.json jobs.csv
    git diff --staged --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Log '변경 없음. 푸시를 건너뜁니다.'
        Write-Log '=== 완료 ==='
        exit 0
    }

    git commit -m 'chore: update job data (local)' 2>&1 | ForEach-Object { Write-Log $_ }
    git push origin main 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "푸시가 실패했습니다 (exit $LASTEXITCODE)"
    }

    Write-Log '푸시 완료. GitHub Actions 가 사이트를 재배포합니다.'
    Write-Log '=== 완료 ==='
}
catch {
    Write-Log ('오류: {0}' -f $_.Exception.Message)
    exit 1
}
