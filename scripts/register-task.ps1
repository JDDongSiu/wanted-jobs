# update-jobs.ps1 을 매일 실행하도록 Windows 작업 스케줄러에 등록한다.
# 한 번만 실행하면 된다. 관리자 권한은 필요 없다.
#
#   powershell -ExecutionPolicy Bypass -File scripts\register-task.ps1
#
# 해제하려면:
#   Unregister-ScheduledTask -TaskName 'wanted-jobs 수집' -Confirm:$false

$ErrorActionPreference = 'Stop'

$taskName = 'wanted-jobs 수집'
$scriptPath = Join-Path $PSScriptRoot 'update-jobs.ps1'
$runTime = '09:00'

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $scriptPath)

$trigger = New-ScheduledTaskTrigger -Daily -At $runTime

# StartWhenAvailable: PC가 꺼져 있어 놓친 일정을 켜진 뒤에 실행한다.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description '원티드·점핏 채용공고를 수집해 GitHub에 올린다.' `
    -Force | Out-Null

Write-Output ('등록 완료: "{0}" — 매일 {1}' -f $taskName, $runTime)
Write-Output '지금 바로 시험 실행하려면:'
Write-Output ('  Start-ScheduledTask -TaskName "{0}"' -f $taskName)
