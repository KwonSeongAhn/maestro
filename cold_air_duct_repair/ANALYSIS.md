# Cold-air-duct STL — 면·원통 FUSE 보강 분석 보고서

**대상**: `cold_air_duct` (신일 AC 라운드 엘보 140x80 → D148)
**증상**: "면과 원통이 FUSING 되어 있지 않다" — 사각 플랜지 면 / D148 출구 원통이
덕트 본체와 하나의 솔리드로 붙지 않고 떠 있음/틈이 보임.

---

## 1. 원인 진단 (원본 STL 계측)

원본 STL 을 삼각망으로 계측한 결과, **하나의 솔리드가 아니라 서로 닿아만 있는
4개의 독립 솔리드**였다.

| 성분 | 부위 | 삼각형 | watertight |
|------|------|-------:|:----------:|
| comp0 | 메인 엘보 본체 | 58,240 | ✅ |
| comp1 | D148 출구 링/원통 A | 1,896 | ✅ |
| comp2 | D148 출구 링/원통 B | 1,896 | ✅ |
| comp3 | 사각(140x80) 플랜지 **면** | 1,280 | ✅ |

전체 위상(topology):

```
watertight        : False
naked(경계) edge  : 0        ← 열린 "구멍"은 하나도 없음
non-manifold edge : 160      ← 면·원통이 본체에 겹쳐/맞닿아만 있음 (FUSE 안 됨)
bodies            : 4
```

### 핵심 포인트 — `fill_holes()` 로는 안 고쳐진다
- 경계(naked) edge = **0** 이므로 채울 "구멍"이 없다. `trimesh.repair.fill_holes()`
  는 아무 것도 하지 않는다.
- 진짜 문제는 **4개 솔리드가 boolean 으로 합쳐(FUSE)지지 않은 것**이다.
  겹쳐만 있어 공유 모서리가 3개 이상 면에 물리는 `non-manifold edge` 160개가 생겼다.
- 플랜지 접합부(X=0)의 덕트 벽 두께는 **2.6 mm** (외벽 Y±72.6 / 보어 Y±70) 로
  매우 얇은 "칼날 접합"이라, 단순 boolean weld 만으로는 구조가 약하다.

---

## 2. 보강 방법 (`fuse_reinforce_duct.py`)

`manifold3d` 엔진 기반 3단계.

1. **FUSE (boolean UNION)** — 4개 솔리드를 하나로 합집합.
   → `watertight, single body, genus-1(양단 개방 파이프)` 솔리드로 융합.
   면·원통이 본체와 실제로 붙는다.

2. **살붙임 필렛 (thick fillet)** — 플랜지 면 ↔ 덕트 본체 접합부(X=0 사각 둘레,
   둘레 421.9 mm)를 따라 **삼각형 거싯 단면을 스윕**하여 두꺼운 보강 살을 추가.
   - 단면: 축방향 14 mm, 반경방향 12 mm 상승, 벽/플랜지 안쪽으로 2 mm 파고듦.
   - 벽·플랜지 솔리드 안으로 깊게 겹치게 잡아 boolean 이 강건하게 처리됨.
   - **보어(유로)는 침범하지 않음** — 유효 단면적 유지.

3. **정리 + 검증** — 필렛 UNION 후 boolean 부산물(0-부피 sliver 1개)을 제거하고
   최대 연결성분만 남긴다.

---

## 3. 결과 (보강 후, round-trip 재검증)

```
triangles      : 68,218
watertight     : True      ✅
boundary edges : 0         ✅
non-manifold   : 0         ✅   (원본 160 → 0)
bodies         : 1         ✅   (원본 4 → 1)
genus          : 1         ✅   (정상 관통 덕트)
manifold3d     : NoError   ✅
winding OK     : True      ✅
volume (mm^3)  : 503,181.9
bbox (mm)      : 178.1 x 389.6 x 150.8  (원본과 동일)
```

**→ 면·원통·본체가 하나의 watertight/manifold 솔리드로 FUSE 되었고,
플랜지 접합부에 두꺼운 살붙임 필렛으로 보강 완료.**

---

## 4. 파일

| 파일 | 설명 |
|------|------|
| `fuse_reinforce_duct.py` | 보수 스크립트 (진단 로그 + 3단계 보강 + 검증) |
| `cold_air_duct_fused.stl` | 보강 완료된 STL (최종 산출물) |
| `verify_section_full.png` | Z=0 길이방향 단면 — 원본(4바디) vs 보강(1솔리드) |
| `verify_flange_zoom.png` | 플랜지 접합부 확대 — 틈/이음선 → 융합+필렛 |
| `verify_flange_3d.png` | 플랜지부 3D 셰이딩 — before/after |

### 재실행
```bash
pip install numpy trimesh manifold3d scipy
python3 fuse_reinforce_duct.py \
    --in  40b210d7-cold_air_duct.stl \
    --out cold_air_duct_fused.stl
# 필렛 크기 조정: --sec-axis 14 --sec-rise 12 --sec-bite 2 --back 4
```
