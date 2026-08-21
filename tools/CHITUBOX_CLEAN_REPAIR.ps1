#Requires -Version 5.1
<#
    CHITUBOX_CLEAN_REPAIR.ps1

    목적: CHITUBOX 설치기(NSIS)가 "이미 설치됨" 분기에서 멈추게 만드는
          시스템 잔존물을 제거한다. 어떤 버전도 설치되지 않는 증상의 원인 3가지를
          되돌릴 수 있는 형태로 정리한다.

      (1) 고아(orphan) 언인스톨 레지스트리 항목  - 실제 폴더/Uninstall.exe 없음
      (2) 깨진 CHITUBOX_Thumbnail.dll 셸 확장 등록 - regsvr32 힙 손상(0xc0000374) 원인
      (3) PendingFileRenameOperations 잔류 항목   - 재부팅 대기 큐 적체

    안전장치: 삭제하는 레지스트리 키는 전부 .reg 로 내보내고,
              폴더는 삭제하지 않고 백업 폴더로 "이동"한다. 되돌리기 가능.

    사용법 (관리자 PowerShell):
        powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\CHITUBOX_CLEAN_REPAIR.ps1"
    변경 없이 점검만:
        ... -File "...\CHITUBOX_CLEAN_REPAIR.ps1" -DryRun

    이 스크립트는 백신을 끄거나 우회하지 않는다. Defender 설정은 읽기만 한다.
#>

[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'

# ---------------------------------------------------------------- [0] 준비
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[중단] 관리자 권한이 필요합니다. PowerShell 을 '관리자 권한으로 실행' 하십시오." -ForegroundColor Red
    exit 1
}

$stamp     = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path ([Environment]::GetFolderPath('Desktop')) "CHITUBOX_BACKUP_$stamp"
$regDir    = Join-Path $backupDir 'registry'
$fileDir   = Join-Path $backupDir 'folders'
$logPath   = Join-Path $backupDir 'REPAIR_LOG.txt'

New-Item -ItemType Directory -Path $regDir  -Force | Out-Null
New-Item -ItemType Directory -Path $fileDir -Force | Out-Null

$script:log = New-Object System.Collections.Generic.List[string]
function Say([string]$msg, [string]$color = 'Gray') {
    Write-Host $msg -ForegroundColor $color
    $script:log.Add($msg)
}

$mode = 'APPLY'
if ($DryRun) { $mode = 'DRY-RUN (변경 없음)' }

Say "==============================================================="
Say " CHITUBOX CLEAN REPAIR  /  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Say " 모드    : $mode"
Say " 백업위치: $backupDir"
Say "==============================================================="

# 레지스트리 키를 .reg 로 내보낸다. 성공하면 $true.
function Backup-RegKey([string]$nativePath, [string]$label) {
    $safe = ($label -replace '[^A-Za-z0-9_.-]', '_')
    $out  = Join-Path $regDir ("{0}.reg" -f $safe)
    $i = 1
    while (Test-Path $out) { $out = Join-Path $regDir ("{0}_{1}.reg" -f $safe, $i); $i++ }
    $null = & reg.exe export "$nativePath" "$out" /y 2>&1
    return ($LASTEXITCODE -eq 0)
}

function Remove-RegKeySafely([string]$nativePath, [string]$label) {
    if (-not (Backup-RegKey $nativePath $label)) {
        Say "    ! 백업 실패 -> 삭제 건너뜀: $nativePath" 'Yellow'
        return $false
    }
    if ($DryRun) { Say "    (dry-run) 삭제 예정: $nativePath" 'Cyan'; return $true }
    try {
        Remove-Item -LiteralPath "Registry::$nativePath" -Recurse -Force -ErrorAction Stop
        Say "    - 삭제됨: $nativePath" 'Green'
        return $true
    } catch {
        Say "    ! 삭제 실패: $nativePath  ($($_.Exception.Message))" 'Yellow'
        return $false
    }
}

# ------------------------------------------------- [1] 실행 중 프로세스 정지
Say ""
Say "[1] 실행 중인 CHITUBOX 프로세스 확인"
$procs = Get-Process -ErrorAction SilentlyContinue |
         Where-Object { $_.ProcessName -like '*CHITU*' }
if (-not $procs) {
    Say "    실행 중인 프로세스 없음."
} else {
    foreach ($p in $procs) {
        Say "    발견: $($p.ProcessName) (PID $($p.Id))"
        if (-not $DryRun) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Say "    - 종료됨" 'Green' }
            catch { Say "    ! 종료 실패: $($_.Exception.Message)" 'Yellow' }
        }
    }
}

# --------------------------------------------- [2] 고아 언인스톨 레지스트리
Say ""
Say "[2] 고아 언인스톨 항목 (실제 파일이 없는데 '설치됨'으로 남은 항목)"

$uninstallRoots = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
)

$orphanCount = 0
foreach ($root in $uninstallRoots) {
    if (-not (Test-Path $root)) { continue }
    foreach ($key in (Get-ChildItem -Path $root -ErrorAction SilentlyContinue)) {
        $props = Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction SilentlyContinue
        if (-not $props) { continue }

        $name = "$($props.DisplayName)"
        $pub  = "$($props.Publisher)"
        if (($name -notlike '*CHITU*') -and ($pub -notlike '*CHITU*')) { continue }

        $loc  = "$($props.InstallLocation)"
        $unin = "$($props.UninstallString)"

        # UninstallString 에서 실제 EXE 경로만 뽑아낸다
        $uninExe = ''
        if ($unin) {
            $m = [regex]::Match($unin, '^\s*"([^"]+)"')
            if ($m.Success) { $uninExe = $m.Groups[1].Value }
            else {
                $m2 = [regex]::Match($unin, '^\s*(\S+\.exe)')
                if ($m2.Success) { $uninExe = $m2.Groups[1].Value }
            }
        }

        $locMissing  = [bool]($loc     -and -not (Test-Path -LiteralPath $loc     -ErrorAction SilentlyContinue))
        $exeMissing  = [bool]($uninExe -and -not (Test-Path -LiteralPath $uninExe -ErrorAction SilentlyContinue))
        $noEvidence  = (-not $loc -and -not $uninExe)

        Say "    항목: '$name' v$($props.DisplayVersion)"
        Say "          key = $($key.Name)"
        $locState = '(값 없음)'
        if ($loc) { if ($locMissing) { $locState = '없음' } else { $locState = '존재' } }
        $exeState = '(값 없음)'
        if ($uninExe) { if ($exeMissing) { $exeState = '없음' } else { $exeState = '존재' } }
        Say "          InstallLocation  = '$loc'  ->  $locState"
        Say "          UninstallString  = '$uninExe'  ->  $exeState"

        if ($locMissing -or $exeMissing -or $noEvidence) {
            Say "          -> 고아 항목으로 판정. 제거합니다." 'Yellow'
            if (Remove-RegKeySafely $key.Name "uninstall_$($key.PSChildName)") { $orphanCount++ }
        } else {
            Say "          -> 실제 설치가 살아있음. 건드리지 않습니다." 'Green'
            Say "             (정상 제거를 원하면 '앱 및 기능'에서 먼저 제거하십시오.)"
        }
    }
}
if ($orphanCount -eq 0) { Say "    제거 대상 없음." }

# --------------------------------------- [3] CHITUBOX 자체 설정/설치 흔적 키
Say ""
Say "[3] CHITUBOX 제품 레지스트리 흔적"
$productKeys = @(
    'HKLM:\SOFTWARE\CHITUBOX',
    'HKLM:\SOFTWARE\WOW6432Node\CHITUBOX',
    'HKCU:\SOFTWARE\CHITUBOX'
)
$found3 = $false
foreach ($pk in $productKeys) {
    if (Test-Path $pk) {
        $found3 = $true
        $native = (Get-Item $pk).Name
        Say "    발견: $native"
        Remove-RegKeySafely $native "product_$($pk -replace '[:\\]','_')" | Out-Null
    }
}
if (-not $found3) { Say "    없음." }

# ------------------------------- [4] 깨진 썸네일 셸 확장(DLL) 등록 제거
Say ""
Say "[4] CHITUBOX_Thumbnail.dll 셸 확장 등록 (regsvr32 크래시 원인)"
Say "    * regsvr32 는 실행하지 않습니다. 그 프로세스가 힙 손상으로 죽는 것이 증상이므로"
Say "      DLL 을 호출하지 않고 레지스트리 등록만 제거합니다."

$clsidRoots = @(
    'Registry::HKEY_CLASSES_ROOT\CLSID',
    'Registry::HKEY_CLASSES_ROOT\WOW6432Node\CLSID'
)
$badGuids = New-Object System.Collections.Generic.List[string]

foreach ($cr in $clsidRoots) {
    if (-not (Test-Path $cr)) { continue }
    foreach ($c in (Get-ChildItem -Path $cr -ErrorAction SilentlyContinue)) {
        $ips = Join-Path $c.PSPath 'InprocServer32'
        if (-not (Test-Path $ips)) { continue }
        $dll = (Get-ItemProperty -LiteralPath $ips -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
        if ("$dll" -like '*CHITU*') {
            Say "    발견: $($c.PSChildName)  ->  $dll"
            if ($badGuids -notcontains $c.PSChildName) { $badGuids.Add($c.PSChildName) }
            Remove-RegKeySafely $c.Name "clsid_$($c.PSChildName)" | Out-Null
        }
    }
}

# Shell Extensions\Approved 목록에서 해당 GUID 제거
$approved = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved'
if ((Test-Path $approved) -and $badGuids.Count -gt 0) {
    Backup-RegKey (Get-Item $approved).Name 'shellext_approved' | Out-Null
    foreach ($g in $badGuids) {
        $v = Get-ItemProperty -Path $approved -Name $g -ErrorAction SilentlyContinue
        if ($v) {
            if ($DryRun) { Say "    (dry-run) Approved 에서 제거 예정: $g" 'Cyan' }
            else {
                Remove-ItemProperty -Path $approved -Name $g -Force -ErrorAction SilentlyContinue
                Say "    - Approved 에서 제거: $g" 'Green'
            }
        }
    }
}

# 3D 프린팅 확장자에 걸린 ShellEx 핸들러 정리
$extKeys = @('.ctb', '.cbddlp', '.photon', '.pws', '.pw0', '.cws', '.chitubox', '.zip.ctb')
foreach ($ext in $extKeys) {
    $shx = "Registry::HKEY_CLASSES_ROOT\$ext\ShellEx"
    if (-not (Test-Path $shx)) { continue }
    foreach ($h in (Get-ChildItem -Path $shx -Recurse -ErrorAction SilentlyContinue)) {
        $val = (Get-ItemProperty -LiteralPath $h.PSPath -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
        if ($val -and ($badGuids -contains "$val")) {
            Say "    발견: $($h.Name) -> $val"
            Remove-RegKeySafely $h.Name "shellex_$($ext -replace '\.','')" | Out-Null
        }
    }
}
if ($badGuids.Count -eq 0) { Say "    등록된 CHITUBOX 셸 확장 없음." }

# --------------------------- [5] PendingFileRenameOperations 잔류 항목 제거
Say ""
Say "[5] 재부팅 대기 파일 작업 (PendingFileRenameOperations)"
$smPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager'
$pfro = (Get-ItemProperty -Path $smPath -Name 'PendingFileRenameOperations' -ErrorAction SilentlyContinue).PendingFileRenameOperations

if (-not $pfro) {
    Say "    항목 없음 (정상)."
} else {
    $orig = @($pfro)
    Say "    현재 항목 수: $($orig.Count)"
    $orig | ForEach-Object { Say "      | $_" }

    # 원본 백업 (텍스트 + .reg)
    $orig | Set-Content -Path (Join-Path $backupDir 'PendingFileRenameOperations_ORIGINAL.txt') -Encoding Unicode
    Backup-RegKey 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager' 'session_manager' | Out-Null

    # 항목은 (원본, 대상) 쌍이다. 쌍 단위로 판정해야 큐가 깨지지 않는다.
    $kept = New-Object System.Collections.Generic.List[string]
    $removedPairs = 0
    for ($i = 0; $i -lt $orig.Count; $i += 2) {
        $src = $orig[$i]
        $dst = ''
        if (($i + 1) -lt $orig.Count) { $dst = $orig[$i + 1] }

        if (("$src" -like '*CHITU*') -or ("$dst" -like '*CHITU*')) {
            $removedPairs++
            continue
        }
        $kept.Add($src)
        $kept.Add($dst)
    }

    Say "    제거할 쌍: $removedPairs / 남길 항목: $($kept.Count)"
    if (-not $DryRun) {
        if ($kept.Count -eq 0) {
            Remove-ItemProperty -Path $smPath -Name 'PendingFileRenameOperations' -Force -ErrorAction SilentlyContinue
            Say "    - 값 전체 제거됨" 'Green'
        } else {
            Set-ItemProperty -Path $smPath -Name 'PendingFileRenameOperations' `
                             -Value ([string[]]$kept.ToArray()) -Type MultiString -Force
            Say "    - CHITUBOX 항목만 제거, 나머지 유지" 'Green'
        }
    } else {
        Say "    (dry-run) 변경 없음" 'Cyan'
    }
}

# ---------------------------------------------------- [6] 잔존 폴더 이동
Say ""
Say "[6] 잔존 폴더 (삭제하지 않고 백업 폴더로 이동)"
$candidates = @(
    "$env:ProgramFiles\CHITUBOX",
    "$env:ProgramFiles\CHITUBOX Pro",
    "${env:ProgramFiles(x86)}\CHITUBOX",
    "${env:ProgramFiles(x86)}\CHITUBOX Pro",
    "$env:LOCALAPPDATA\CHITUBOX",
    "$env:APPDATA\CHITUBOX",
    "$env:ProgramData\CHITUBOX"
)
$movedAny = $false
foreach ($p in $candidates) {
    if ([string]::IsNullOrWhiteSpace($p)) { continue }
    if (-not (Test-Path -LiteralPath $p)) { continue }
    $movedAny = $true
    Say "    발견: $p"
    if ($DryRun) { Say "    (dry-run) 이동 예정" 'Cyan'; continue }
    $dest = Join-Path $fileDir ((Split-Path $p -Parent).Replace(':','') -replace '[\\/]','_')
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    try {
        Move-Item -LiteralPath $p -Destination $dest -Force -ErrorAction Stop
        Say "    - 이동됨 -> $dest" 'Green'
    } catch {
        Say "    ! 이동 실패: $($_.Exception.Message)" 'Yellow'
        Say "      (파일이 사용 중일 수 있습니다. 재부팅 후 다시 실행하십시오.)"
    }
}
if (-not $movedAny) { Say "    잔존 폴더 없음." }

# ------------------------------------------------- [7] 수리 후 상태 재확인
Say ""
Say "[7] 수리 후 상태"
$leftUninstall = @()
foreach ($root in $uninstallRoots) {
    if (-not (Test-Path $root)) { continue }
    $leftUninstall += Get-ChildItem -Path $root -ErrorAction SilentlyContinue | Where-Object {
        $pp = Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
        $pp -and (("$($pp.DisplayName)" -like '*CHITU*') -or ("$($pp.Publisher)" -like '*CHITU*'))
    }
}
$leftPfro = (Get-ItemProperty -Path $smPath -Name 'PendingFileRenameOperations' -ErrorAction SilentlyContinue).PendingFileRenameOperations
$leftPfroChitu = @($leftPfro | Where-Object { "$_" -like '*CHITU*' }).Count

Say "    남은 CHITUBOX 언인스톨 항목 : $($leftUninstall.Count)  (기대값 0)"
Say "    남은 CHITU PendingRename   : $leftPfroChitu  (기대값 0)"
Say "    남은 Program Files 폴더     : $(@($candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) }).Count)  (기대값 0)"

# ------------------------------------- [8] 보안 상태 (읽기 전용 · 변경 안 함)
Say ""
Say "[8] 보안 상태 점검 (읽기 전용 — 이 스크립트는 아무것도 바꾸지 않습니다)"
try {
    $mp = Get-MpPreference -ErrorAction Stop
    $st = Get-MpComputerStatus -ErrorAction SilentlyContinue
    Say "    RealTimeProtectionEnabled : $($st.RealTimeProtectionEnabled)"
    Say "    DisableRealtimeMonitoring : $($mp.DisableRealtimeMonitoring)"
    Say "    ExclusionPath             : $($mp.ExclusionPath -join '; ')"
    Say "    ExclusionProcess          : $($mp.ExclusionProcess -join '; ')"
} catch {
    Say "    ! Defender 상태를 읽을 수 없음: $($_.Exception.Message)" 'Yellow'
}
$tsda = 'HKLM:\SOFTWARE\Microsoft\Windows Defender\Threats\ThreatSeverityDefaultAction'
if (Test-Path $tsda) {
    Say "    ThreatSeverityDefaultAction 이 설정되어 있습니다 (기본값은 '없음'):"
    $p = Get-ItemProperty -Path $tsda
    $p.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {
        Say "      severity $($_.Name) = $($_.Value)   [1=Clean 2=Quarantine 3=Remove 6=Block 8=UserDefined 9=NoAction 10=Allow]"
    }
} else {
    Say "    ThreatSeverityDefaultAction : 없음 (정상)"
}

# ------------------------------------------------------------------ 마무리
Say ""
Say "==============================================================="
Say " 완료. 로그: $logPath"
Say " 다음 단계:"
Say "   1) 반드시 재부팅 하십시오. (PendingFileRenameOperations 큐 반영)"
Say "   2) 재부팅 후 REPAIR_LOG.txt 의 [7] 항목이 전부 0 인지 확인"
Say "   3) chitubox.com 공식 설치기로 설치"
Say " 되돌리기: $regDir 의 .reg 파일 더블클릭 + $fileDir 의 폴더를 원위치로 이동"
Say "==============================================================="

$script:log | Set-Content -Path $logPath -Encoding UTF8
