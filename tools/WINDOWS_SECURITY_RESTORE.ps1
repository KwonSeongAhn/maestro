#Requires -Version 5.1
<#
    WINDOWS_SECURITY_RESTORE.ps1

    목적: CHITUBOX_DIAG.txt 에서 실측된 보안 상태 이상을 정상으로 되돌린다.
          설치 문제와 별개이며, 우선순위가 더 높다.

    실측된 이상 (2026-08-21 진단):
      - RealTimeProtection : False                  (실시간 보호 꺼짐)
      - Defender 가 자기 설정 변조를 위협으로 2회 탐지:
          hklm\...\Windows Defender\Threats\ThreatSeverityDefaultAction\\5
      - C:\AppCache\x86\svchost.exe                 (UPX 다중 패킹)
      - C:\Program Files (x86)\AW Manager\Windows Manager\Windows Updater.exe
        + 예약작업 AdvancedUpdater ({D9563113-9B94-4F03-A588-494597C64BA3})
      - updater.exe 30.0.3.25 가 매시 정각 0xc0000005 크래시 (시간당 1회 실행 중)
      - SmartScreen : 0
      - Chrome 확장 knemcdpkggnbhpoaaagmjiigenifejfo (Profile 3)

    기본 동작 : Defender/SmartScreen 정상화, 변조 키 제거, 제외 항목 해제,
                악성 예약작업 비활성화, 시그니처 갱신 + 빠른 검사, 전체 보고
    -DeepRepair : 위 + 전체 검사 + DISM /RestoreHealth + sfc /scannow (30분 이상)
    -Quarantine : 위 + 실측된 의심 파일을 삭제하지 않고 백업 폴더로 격리 이동
    -DryRun     : 아무것도 바꾸지 않고 현재 상태만 보고

    사용법 (관리자 PowerShell):
        powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\WINDOWS_SECURITY_RESTORE.ps1" -DeepRepair -Quarantine
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$DeepRepair,
    [switch]$Quarantine
)

$ErrorActionPreference = 'Continue'

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[중단] 관리자 권한이 필요합니다." -ForegroundColor Red
    exit 1
}

$stamp     = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path ([Environment]::GetFolderPath('Desktop')) "SECURITY_BACKUP_$stamp"
$regDir    = Join-Path $backupDir 'registry'
$qDir      = Join-Path $backupDir 'quarantine'
$logPath   = Join-Path $backupDir 'SECURITY_LOG.txt'
New-Item -ItemType Directory -Path $regDir -Force | Out-Null
New-Item -ItemType Directory -Path $qDir   -Force | Out-Null

$script:log = New-Object System.Collections.Generic.List[string]
function Say([string]$m, [string]$c = 'Gray') { Write-Host $m -ForegroundColor $c; $script:log.Add($m) }

function Backup-RegKey([string]$native, [string]$label) {
    $safe = ($label -replace '[^A-Za-z0-9_.-]', '_')
    $out  = Join-Path $regDir "$safe.reg"
    $i = 1
    while (Test-Path $out) { $out = Join-Path $regDir ("{0}_{1}.reg" -f $safe, $i); $i++ }
    $null = & reg.exe export "$native" "$out" /y 2>&1
    return ($LASTEXITCODE -eq 0)
}

$mode = 'APPLY'
if ($DryRun) { $mode = 'DRY-RUN (변경 없음)' }
Say "==============================================================="
Say " WINDOWS SECURITY RESTORE  /  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Say " 모드      : $mode   DeepRepair=$DeepRepair  Quarantine=$Quarantine"
Say " 백업위치  : $backupDir"
Say "==============================================================="

# ------------------------------------------------------ [1] 현재 보안 상태
Say ""
Say "[1] 복구 전 상태"
$status = $null
try {
    $status = Get-MpComputerStatus -ErrorAction Stop
    Say "    AMServiceEnabled          : $($status.AMServiceEnabled)"
    Say "    AntivirusEnabled          : $($status.AntivirusEnabled)"
    Say "    RealTimeProtectionEnabled : $($status.RealTimeProtectionEnabled)"
    Say "    IsTamperProtected         : $($status.IsTamperProtected)"
    Say "    AntivirusSignatureAge     : $($status.AntivirusSignatureAge) 일"
    Say "    QuickScanAge              : $($status.QuickScanAge) 일"
} catch {
    Say "    ! Defender 상태를 읽을 수 없음: $($_.Exception.Message)" 'Red'
    Say "      Defender 서비스 자체가 손상되었을 수 있습니다. -DeepRepair 로 재실행하십시오."
}

# --------------------------------- [2] Threats\ThreatSeverityDefaultAction
Say ""
Say "[2] ThreatSeverityDefaultAction 변조 키"
Say "    (심각도별 '기본 조치'를 강제로 바꿔 위협을 무시하게 만드는 항목. 기본값은 '없음')"
$tsdaPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows Defender\Threats\ThreatSeverityDefaultAction',
    'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender\Threats\ThreatSeverityDefaultAction'
)
$tsdaFound = $false
foreach ($tp in $tsdaPaths) {
    if (-not (Test-Path $tp)) { continue }
    $tsdaFound = $true
    $native = (Get-Item $tp).Name
    Say "    발견: $native" 'Yellow'
    $props = Get-ItemProperty -LiteralPath $tp
    $props.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {
        Say "      severity $($_.Name) = $($_.Value)   [2=격리 3=제거 6=차단 9=무시 10=허용]"
    }
    if ($DryRun) { Say "    (dry-run) 제거 예정" 'Cyan'; continue }
    if (Backup-RegKey $native "tsda_$($tp -replace '[:\\ ]','_')") {
        try {
            Remove-Item -LiteralPath $tp -Recurse -Force -ErrorAction Stop
            Say "    - 제거됨 (기본 조치가 Windows 기본값으로 복귀)" 'Green'
        } catch { Say "    ! 제거 실패: $($_.Exception.Message)" 'Yellow' }
    } else { Say "    ! 백업 실패 -> 제거 건너뜀" 'Yellow' }
}
if (-not $tsdaFound) { Say "    없음 (정상)." 'Green' }

# ----------------------------------------- [3] Defender 무력화 정책 키 제거
Say ""
Say "[3] Defender 무력화 정책 값"
$policyTargets = @(
    @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender';
       Names = @('DisableAntiSpyware', 'DisableAntiVirus', 'DisableRoutinelyTakingAction') },
    @{ Path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection';
       Names = @('DisableRealtimeMonitoring', 'DisableBehaviorMonitoring',
                 'DisableOnAccessProtection', 'DisableScanOnRealtimeEnable', 'DisableIOAVProtection') }
)
$polHit = 0
foreach ($t in $policyTargets) {
    if (-not (Test-Path $t.Path)) { continue }
    $native = (Get-Item $t.Path).Name
    $backed = $false
    foreach ($n in $t.Names) {
        $v = Get-ItemProperty -LiteralPath $t.Path -Name $n -ErrorAction SilentlyContinue
        if (-not $v) { continue }
        $polHit++
        Say "    발견: $($t.Path)\$n = $($v.$n)" 'Yellow'
        if ($DryRun) { Say "    (dry-run) 제거 예정" 'Cyan'; continue }
        if (-not $backed) { Backup-RegKey $native "policy_defender_$polHit" | Out-Null; $backed = $true }
        Remove-ItemProperty -LiteralPath $t.Path -Name $n -Force -ErrorAction SilentlyContinue
        Say "    - 제거됨" 'Green'
    }
}
if ($polHit -eq 0) { Say "    무력화 정책 없음 (정상)." 'Green' }

# ------------------------------------------------- [4] Defender 제외 항목
Say ""
Say "[4] Defender 검사 제외 항목"
try {
    $pref = Get-MpPreference -ErrorAction Stop
    $exPath = @($pref.ExclusionPath);      $exProc = @($pref.ExclusionProcess)
    $exExt  = @($pref.ExclusionExtension); $exIp   = @($pref.ExclusionIpAddress)
    $total  = $exPath.Count + $exProc.Count + $exExt.Count + $exIp.Count
    if ($total -eq 0) {
        Say "    제외 항목 없음 (정상)." 'Green'
    } else {
        $exPath | ForEach-Object { Say "    Path      : $_" 'Yellow' }
        $exProc | ForEach-Object { Say "    Process   : $_" 'Yellow' }
        $exExt  | ForEach-Object { Say "    Extension : $_" 'Yellow' }
        $exIp   | ForEach-Object { Say "    IpAddress : $_" 'Yellow' }
        @($exPath + $exProc + $exExt + $exIp) |
            Set-Content -Path (Join-Path $backupDir 'DEFENDER_EXCLUSIONS_ORIGINAL.txt') -Encoding UTF8
        if ($DryRun) {
            Say "    (dry-run) 전부 해제 예정" 'Cyan'
        } else {
            if ($exPath.Count) { Remove-MpPreference -ExclusionPath      $exPath -ErrorAction SilentlyContinue }
            if ($exProc.Count) { Remove-MpPreference -ExclusionProcess   $exProc -ErrorAction SilentlyContinue }
            if ($exExt.Count)  { Remove-MpPreference -ExclusionExtension $exExt  -ErrorAction SilentlyContinue }
            if ($exIp.Count)   { Remove-MpPreference -ExclusionIpAddress $exIp   -ErrorAction SilentlyContinue }
            Say "    - 제외 항목 $total 개 해제됨 (원본은 DEFENDER_EXCLUSIONS_ORIGINAL.txt)" 'Green'
        }
    }
} catch {
    Say "    ! 제외 항목을 읽을 수 없음: $($_.Exception.Message)" 'Yellow'
}

# --------------------------------------------- [5] 실시간 보호 다시 켜기
Say ""
Say "[5] 실시간 보호 및 보호 기능 활성화"
if ($DryRun) {
    Say "    (dry-run) 변경 없음" 'Cyan'
} elseif ($status -and $status.IsTamperProtected) {
    Say "    ! 변조 방지(Tamper Protection)가 켜져 있어 스크립트로는 변경할 수 없습니다." 'Yellow'
    Say "      Windows 보안 > 바이러스 및 위협 방지 > 설정 관리 에서 직접 켜십시오."
} else {
    $toggles = @{
        DisableRealtimeMonitoring   = $false
        DisableBehaviorMonitoring   = $false
        DisableIOAVProtection       = $false
        DisableScriptScanning       = $false
        DisableBlockAtFirstSeen     = $false
        DisableArchiveScanning      = $false
        DisableRemovableDriveScanning = $false
    }
    # 개별로 적용한다. 하나가 실패해도 나머지는 적용되도록.
    foreach ($k in @($toggles.Keys)) {
        $splat = @{ $k = $toggles[$k]; ErrorAction = 'Stop' }
        try {
            Set-MpPreference @splat
            Say "    - $k = $($toggles[$k])" 'Green'
        } catch {
            Say "    ! $k 설정 실패: $($_.Exception.Message)" 'Yellow'
        }
    }
    try {
        Set-MpPreference -MAPSReporting Advanced -SubmitSamplesConsent SendSafeSamples -ErrorAction Stop
        Say "    - 클라우드 보호(MAPS) 활성화" 'Green'
    } catch { Say "    ! MAPS 설정 실패: $($_.Exception.Message)" 'Yellow' }

    foreach ($svc in @('WinDefend', 'WdNisSvc', 'SecurityHealthService')) {
        $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if (-not $s) { Say "    ! 서비스 없음: $svc" 'Yellow'; continue }
        if ($s.Status -ne 'Running') {
            try { Start-Service -Name $svc -ErrorAction Stop; Say "    - 서비스 시작: $svc" 'Green' }
            catch { Say "    ! 서비스 시작 실패: $svc ($($_.Exception.Message))" 'Yellow' }
        } else { Say "    서비스 정상: $svc" }
    }
}

# ------------------------------------------------------ [6] SmartScreen
Say ""
Say "[6] SmartScreen"
$ssExplorer = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer'
$cur = (Get-ItemProperty -LiteralPath $ssExplorer -Name 'SmartScreenEnabled' -ErrorAction SilentlyContinue).SmartScreenEnabled
Say "    현재 SmartScreenEnabled = '$cur'"
if (-not $DryRun) {
    Backup-RegKey (Get-Item $ssExplorer).Name 'explorer_smartscreen' | Out-Null
    Set-ItemProperty -LiteralPath $ssExplorer -Name 'SmartScreenEnabled' -Value 'Warn' -Type String -Force
    Say "    - SmartScreenEnabled = 'Warn' 로 복구" 'Green'
    $ssPolicy = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'
    if (Test-Path $ssPolicy) {
        $ev = Get-ItemProperty -LiteralPath $ssPolicy -Name 'EnableSmartScreen' -ErrorAction SilentlyContinue
        if ($ev -and $ev.EnableSmartScreen -eq 0) {
            Backup-RegKey (Get-Item $ssPolicy).Name 'policy_smartscreen' | Out-Null
            Remove-ItemProperty -LiteralPath $ssPolicy -Name 'EnableSmartScreen' -Force -ErrorAction SilentlyContinue
            Say "    - SmartScreen 강제 해제 정책 제거" 'Green'
        }
    }
} else { Say "    (dry-run) 변경 없음" 'Cyan' }

# -------------------------------------- [7] 악성 예약작업 / 지속성 항목
Say ""
Say "[7] 예약작업 점검 (매시 크래시하는 updater.exe 의 출처)"
$badTaskNames = @('AdvancedUpdater')
$suspectPat   = @('*\AppCache\*', '*AW Manager*', '*Windows Manager*')

$allTasks = @()
try { $allTasks = Get-ScheduledTask -ErrorAction Stop } catch { Say "    ! 예약작업 목록 실패: $($_.Exception.Message)" 'Yellow' }

$taskHit = 0
foreach ($t in $allTasks) {
    $exes = @()
    foreach ($a in @($t.Actions)) { if ($a.Execute) { $exes += "$($a.Execute)" } }
    $joined = ($exes -join ' | ')

    $isNamed   = ($badTaskNames -contains $t.TaskName)
    $isSuspect = $false
    foreach ($pat in $suspectPat) { if ($joined -like $pat) { $isSuspect = $true } }
    $isUpdater = ($joined -like '*updater.exe*' -and $joined -notlike '*\Microsoft\*' -and $joined -notlike '*\Windows\*')

    if (-not ($isNamed -or $isSuspect -or $isUpdater)) { continue }
    $taskHit++
    $info = $t | Get-ScheduledTaskInfo -ErrorAction SilentlyContinue
    Say "    작업: $($t.TaskPath)$($t.TaskName)   상태=$($t.State)" 'Yellow'
    Say "          실행: $joined"
    if ($info) { Say "          마지막실행=$($info.LastRunTime)  결과=0x$('{0:X}' -f $info.LastTaskResult)  다음=$($info.NextRunTime)" }

    if ($DryRun) { Say "          (dry-run) 비활성화 예정" 'Cyan'; continue }
    try {
        Disable-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath -ErrorAction Stop | Out-Null
        Say "          - 비활성화됨 (삭제 아님. 되돌리려면 작업 스케줄러에서 사용으로 변경)" 'Green'
    } catch { Say "          ! 비활성화 실패: $($_.Exception.Message)" 'Yellow' }
}
if ($taskHit -eq 0) { Say "    해당 예약작업 없음." 'Green' }

Say ""
Say "    자동 시작(Run/RunOnce) 항목 — 보고만 합니다:"
$runKeys = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
)
foreach ($rk in $runKeys) {
    if (-not (Test-Path $rk)) { continue }
    $rp = Get-ItemProperty -LiteralPath $rk
    $rp.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {
        Say "      [$rk] $($_.Name) = $($_.Value)"
    }
}

# ------------------------------------------ [8] 실측된 의심 경로 상태 확인
Say ""
Say "[8] 진단에서 위협으로 탐지된 경로 (현재 존재 여부)"
$flagged = @(
    'C:\AppCache\x86\svchost.exe',
    'C:\AppCache',
    "${env:ProgramFiles(x86)}\AW Manager\Windows Manager\Windows Updater.exe",
    "${env:ProgramFiles(x86)}\AW Manager",
    'C:\WINDOWS\System32\Tasks\AdvancedUpdater'
)
foreach ($f in $flagged) {
    if ([string]::IsNullOrWhiteSpace($f)) { continue }
    $exists = Test-Path -LiteralPath $f -ErrorAction SilentlyContinue
    if (-not $exists) { Say "    absent  $f" 'Green'; continue }
    $item = Get-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
    $size = ''
    if ($item -and -not $item.PSIsContainer) { $size = "  $([math]::Round($item.Length/1MB,2)) MB" }
    Say "    PRESENT $f$size" 'Red'
    try {
        $sig = Get-AuthenticodeSignature -LiteralPath $f -ErrorAction SilentlyContinue
        if ($sig) { Say "            서명: $($sig.Status)  $($sig.SignerCertificate.Subject)" }
    } catch { }

    if ($Quarantine -and -not $DryRun -and $item -and -not $item.PSIsContainer) {
        $dest = Join-Path $qDir ($f -replace '[:\\]', '_')
        try {
            Move-Item -LiteralPath $f -Destination $dest -Force -ErrorAction Stop
            Say "            - 격리 폴더로 이동됨 (삭제 아님)" 'Green'
        } catch {
            Say "            ! 이동 실패(사용 중일 수 있음): $($_.Exception.Message)" 'Yellow'
            Say "              Defender 전체 검사에 맡깁니다."
        }
    }
}

$chromeExt = Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data\Profile 3\Extensions\knemcdpkggnbhpoaaagmjiigenifejfo'
if (Test-Path -LiteralPath $chromeExt) {
    Say "    PRESENT $chromeExt" 'Red'
    Say "            Chrome 확장은 자동으로 지우지 않습니다. 브라우저에서 직접 제거하십시오:"
    Say "            chrome://extensions -> Profile 3 -> 해당 확장 삭제"
} else {
    Say "    absent  Chrome 확장 knemcdpkggnbhpoaaagmjiigenifejfo" 'Green'
}

# ------------------------------------------------ [9] 시그니처 갱신 + 검사
Say ""
Say "[9] 시그니처 갱신 및 검사"
if ($DryRun) {
    Say "    (dry-run) 건너뜀" 'Cyan'
} else {
    try { Update-MpSignature -ErrorAction Stop; Say "    - 시그니처 갱신 완료" 'Green' }
    catch { Say "    ! 시그니처 갱신 실패: $($_.Exception.Message)" 'Yellow' }

    $scanType = 'QuickScan'
    if ($DeepRepair) { $scanType = 'FullScan' }
    Say "    - $scanType 시작 (FullScan 은 수십 분 걸립니다)"
    try { Start-MpScan -ScanType $scanType -ErrorAction Stop; Say "    - 검사 완료" 'Green' }
    catch { Say "    ! 검사 실패: $($_.Exception.Message)" 'Yellow' }

    Say "    검사 후 탐지 내역:"
    $th = Get-MpThreatDetection -ErrorAction SilentlyContinue |
          Sort-Object InitialDetectionTime -Descending | Select-Object -First 15
    if (-not $th) { Say "      (없음)" 'Green' }
    else {
        foreach ($d in $th) {
            Say "      $($d.InitialDetectionTime)  action=$($d.ActionSuccess)  $($d.Resources -join ' ; ')"
        }
    }
}

# ------------------------------------------------- [10] 시스템 파일 무결성
Say ""
Say "[10] 시스템 파일 무결성"
if (-not $DeepRepair) {
    Say "    건너뜀. 실행하려면 -DeepRepair 를 붙이십시오 (30분 이상 소요)."
} elseif ($DryRun) {
    Say "    (dry-run) 건너뜀" 'Cyan'
} else {
    Say "    - DISM /Online /Cleanup-Image /RestoreHealth 실행 중..."
    $d = & dism.exe /Online /Cleanup-Image /RestoreHealth 2>&1
    $d | Select-Object -Last 6 | ForEach-Object { Say "      $_" }
    Say "    - sfc /scannow 실행 중..."
    $sf = & sfc.exe /scannow 2>&1
    ($sf -join ' ') -split "`n" | Select-Object -Last 6 | ForEach-Object { Say "      $_" }
}

# ------------------------------------------------------ [11] 복구 후 상태
Say ""
Say "[11] 복구 후 상태"
try {
    $after = Get-MpComputerStatus -ErrorAction Stop
    Say "    RealTimeProtectionEnabled : $($after.RealTimeProtectionEnabled)   (기대값 True)"
    Say "    AntivirusEnabled          : $($after.AntivirusEnabled)   (기대값 True)"
    Say "    BehaviorMonitorEnabled    : $($after.BehaviorMonitorEnabled)   (기대값 True)"
    Say "    AntivirusSignatureAge     : $($after.AntivirusSignatureAge) 일   (기대값 0)"
} catch { Say "    ! 상태 읽기 실패: $($_.Exception.Message)" 'Red' }
Say "    ThreatSeverityDefaultAction 잔존: $((Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows Defender\Threats\ThreatSeverityDefaultAction'))   (기대값 False)"
$ssNow = (Get-ItemProperty -LiteralPath $ssExplorer -Name 'SmartScreenEnabled' -ErrorAction SilentlyContinue).SmartScreenEnabled
Say "    SmartScreenEnabled        : '$ssNow'   (기대값 Warn)"

Say ""
Say "==============================================================="
Say " 완료. 로그: $logPath"
Say " 되돌리기: $regDir 의 .reg 더블클릭 / $qDir 의 파일 원위치"
Say ""
Say " 주의: 실시간 보호가 켜지면 크랙 패치된 EXE 는 다시 삭제됩니다."
Say "       '완전 정상' 상태와 크랙본 실행은 동시에 성립하지 않습니다."
Say "==============================================================="

$script:log | Set-Content -Path $logPath -Encoding UTF8
