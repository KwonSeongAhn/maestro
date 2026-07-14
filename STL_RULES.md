# STL 설계·Export·검증 규칙 (STL Rules)

> 목적: "면과 원통이 FUSE 안 됨"(분리된 여러 바디 / non-manifold seam) 같은
> 불량 STL 이 다시 나오거나 저장소에 유입되는 것을 **원천 차단**한다.
> 근거 사례: `cold_air_duct_repair/ANALYSIS.md`

---

## 0. 한 줄 규칙
**모든 배포/커밋 STL 은 "단일(single) · watertight · manifold" 솔리드여야 한다.**

---

## 1. 설계 규칙 (모델링 단계 — 근본 차단)

| # | 규칙 | 이유 |
|---|------|------|
| 1.1 | Export 전 **모든 바디를 boolean union(합치기)** 한다 | STL 은 어셈블리 개념이 없어, 안 합치면 분리 바디로 저장됨 |
| 1.2 | 접합부는 맞닿게(coincident)가 아니라 **0.5~1mm 겹치게(interference)** | 정확히 맞닿으면 boolean 이 degenerate → seam 발생 |
| 1.3 | 얇은 벽·직각 접합엔 **필렛/거싯(살붙임)** 을 넣는다 | 칼날 접합(예: 2.6mm 벽)은 구조 취약 + 융합 불안정 |
| 1.4 | 벽 두께는 공정 최소치 이상으로 유지 | 프린트/제조성 |

- CAD(Fusion360/SolidWorks): `Combine(Join)` / `Boolean Union` 후 export.
- 절차적/Three.js: `manifold3d` 또는 `three-bvh-csg` 로 union 후 export.

## 2. Export 규칙 (검증 게이트)

Export 직후 **반드시** 아래를 통과해야 한다(자동):
```bash
python3 tools/check_stl.py --expect-genus <G> part.stl
#   G = 관통(양단 개방) 덕트/파이프 → 1,  막힌 솔리드 → 0
```
통과 기준(모두 PASS):
- `watertight = True`
- `boundary edges = 0`
- `non-manifold edges = 0`
- `bodies = 1` (단일 솔리드)
- `winding consistent = True`
- `volume > 0` (법선 정상)
- (선택) `genus = 기대값`

> 불량 신호: `watertight=False`, `non-manifold>0`, `bodies>1`, `genus<0`
> 중 하나라도 뜨면 **fuse 누락** 이다.

### 2.1 검사 제외 (레퍼런스/입력 아티팩트)
"수리 전" 원본이나 비교용 before 샘플처럼 **의도적으로 보관하는 불량 STL** 은
deliverable 이 아니므로 저장소 루트의 **`.stlcheckignore`** (gitignore 스타일
glob)에 등록해 검사에서 제외한다. 산출/배포 STL 은 제외 금지 — 반드시 통과해야 한다.

## 3. 자동화 규칙 (강제)

- **pre-commit (로컬)**: `bash tools/install-git-hooks.sh` 또는
  `pip install pre-commit && pre-commit install` → `*.stl` 커밋 시 자동 검증.
- **CI (원격)**: `.github/workflows/stl-check.yml` 가 push/PR 마다 모든 `*.stl` 검증.
- 검증 실패 STL 은 **커밋/머지 금지**. 부득이 우회 시 `git commit --no-verify`
  는 리뷰어 승인 하에서만.

## 4. 불량 발견 시 복구 절차

1. `tools/check_stl.py` 로 원인 확인 (bodies/non-manifold/genus).
2. `cold_air_duct_repair/fuse_reinforce_duct.py` 방식으로:
   - 모든 바디 boolean union → 단일 솔리드
   - 얇은/분리 접합부에 살붙임 필렛(벽·플랜지 안으로 깊게 겹침, 보어 비침범)
   - boolean 부산물(sliver) 제거 후 최대 연결성분만 유지
3. 다시 `check_stl.py` 통과 확인 → 커밋.

## 5. 리뷰 체크리스트

- [ ] Export 전 boolean union 했는가
- [ ] 접합부 0.5~1mm 겹침 + 필렛 있는가
- [ ] `tools/check_stl.py` 통과했는가 (bodies=1, non-manifold=0)
- [ ] genus 가 형상 의도와 맞는가 (관통=1 / 막힘=0)
- [ ] 벽 두께가 최소치 이상인가
