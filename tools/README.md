# CHITUBOX 설치 불가 / Windows 정상화 스크립트

2026-08-21 `CHITUBOX_DIAG.txt` 실측 결과에 맞춰 작성됨. Windows 11 Pro 26200, 관리자 권한 필요.

## 실측으로 확정된 것

| 항목 | 측정값 | 판정 |
|---|---|---|
| `Uninstall\{44e68515-b730-4c31-9d62-2c3e0ec1f128}` | CHITUBOX v0.0.9, `InstallLocation=C:\Program Files\CHITUBOX` | 폴더 **absent** → 설치 차단 원인 |
| CHITUBOX 관련 폴더 6곳 | 전부 absent | 설치된 것이 없음 |
| `PendingFileRenameOperations` | count=12, 경로가 `...Thumbnail.dll\CHITUBOX_Thumbnail.dll` | 재부팅 대기 큐 적체 |
| `regsvr32.exe` → `ntdll.dll` | `0xc0000374` 7회, 오프셋 전부 `0x112165` | 썸네일 DLL 등록 시 힙 손상 |
| `CHITUBOX_WIN64_Installer_v3.0.1.exe` | Application Hang 1002 @16:06:03 | 위 크래시 직후 설치기 정지 |
| `msiserver` / `InProgress` | Stopped·Manual / False | **정상. 원인 아님** |
| VC++ v14 14.51, .NET 4.8 | 설치됨 | **정상. 원인 아님** |
| chitubox.com 443 / hosts / proxy | OK / 없음 / 없음 | **정상. 원인 아님** |
| `RealTimeProtection` | **False** | 보안 이상 |
| `ThreatSeverityDefaultAction\5` | Defender가 변조를 위협으로 2회 탐지 | 보안 이상 |
| `updater.exe 30.0.3.25` | 매시 정각 `0xc0000005` 크래시 | 시간당 1회 실행되는 예약작업 존재 |
| `SmartScreen` | 0 | 보안 이상 |

디스크 여유 291 GB, 네트워크 정상. 용량·네트워크는 원인이 아님.

## 실행 순서

두 스크립트 모두 **삭제하지 않는다.** 레지스트리는 `.reg`로 내보내고 파일은 백업 폴더로 이동하므로 전부 되돌릴 수 있다.
각 스크립트에 `-DryRun`을 붙이면 아무것도 바꾸지 않고 현재 상태만 보고한다.

두 파일 모두 저장 후 **우클릭 → 속성 → [차단 해제] 체크**. (진단에서 `.ps1` 하나가 `BLOCKED=True`로 나왔음)

### 1단계 — 설치 차단 요소 제거

```
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\CHITUBOX_CLEAN_REPAIR.ps1"
```

고아 언인스톨 키, 썸네일 셸 확장 등록, `PendingFileRenameOperations` 잔류 쌍, 깨진 바로가기, `%TEMP%` NSIS 잔여물,
IFEO 실행 하이재킹, 방화벽 규칙, 파일 차단, 아이콘·썸네일 캐시를 정리한다.
`regsvr32`는 호출하지 않는다 — 그 프로세스가 죽는 것이 증상이므로 레지스트리만 직접 손본다.

로그의 `[13] 수리 후 상태`가 전부 0이어야 한다.

### 2단계 — 재부팅

`PendingFileRenameOperations` 큐는 재부팅해야 반영된다. 건너뛰면 1단계가 무효가 된다.

### 3단계 — Windows 정상화

```
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\WINDOWS_SECURITY_RESTORE.ps1" -DeepRepair -Quarantine
```

실시간 보호·행위 감시·클라우드 보호·SmartScreen 복구, `ThreatSeverityDefaultAction` 변조 키 제거,
Defender 무력화 정책 및 검사 제외 항목 해제, 매시 실행되는 악성 예약작업 비활성화,
탐지된 경로 격리, 시그니처 갱신 후 전체 검사, DISM + SFC.

`-DeepRepair` 없이 실행하면 빠른 검사만 하고 DISM/SFC는 건너뛴다. 30분 이상 걸리므로 시간이 없을 때만.

로그의 `[11] 복구 후 상태`에서 `RealTimeProtectionEnabled=True`, `ThreatSeverityDefaultAction 잔존=False`를 확인한다.

### 4단계 — 재부팅 후 설치

chitubox.com 공식 설치기로 설치한다.

## 알아둘 것

- **실시간 보호를 켜면 크랙 패치된 EXE는 다시 삭제된다.** 진단상 `C:\Program Files\CHITUBOX Pro\CHITUBOX Pro.exe`가
  11:20:39과 16:33:11 두 번 위협으로 제거되었고, 그 EXE는 버전이 `0.0.0.0`으로 비어 있다. "완전 정상" 상태와
  크랙본 실행은 동시에 성립하지 않는다. 이 스크립트들은 백신을 끄거나 우회하지 않는다.
- `Downloads\seize V1.12-Parameter -HB3(fixed)_00.chitubox`의 SHA256이 `e3b0c442...b855`다. 이는 **빈 파일**의 해시다.
  그 파라미터 파일은 0바이트이므로 불러와도 아무 값도 들어오지 않는다. 다시 받아야 한다.
- 변조 방지(Tamper Protection)가 켜져 있으면 스크립트가 실시간 보호를 켤 수 없다. 그 경우 로그가 알려주며,
  Windows 보안 → 바이러스 및 위협 방지 → 설정 관리에서 직접 켜야 한다.
- Chrome 확장은 자동으로 지우지 않고 경로만 보고한다. `chrome://extensions`에서 직접 판단해 제거한다.
