# CLAUDE.md — 프로젝트 작업 규칙

이 저장소는 3D 형상(Three.js/절차적 모델링, STL 산출물)을 다룬다.

## STL 관련 필수 규칙  (자세히: `STL_RULES.md`)

STL 을 생성·수정·커밋할 때는 **반드시** 다음을 지킨다:

1. **단일 솔리드 원칙**: 배포/커밋되는 STL 은 항상
   **single body · watertight · manifold** 여야 한다.
2. **Export 전 boolean union**: 여러 바디(면·원통·플랜지 등)는 export 전에
   반드시 union 으로 하나로 fuse 한다. 접합부는 0.5~1mm 겹치고, 얇은/직각
   접합엔 필렛(살붙임)을 넣는다.
3. **검증 게이트 통과**: 산출/수정한 STL 은 커밋 전
   `python3 tools/check_stl.py [--expect-genus G] file.stl` 로 검증한다.
   `bodies=1 / non-manifold=0 / watertight=True` 가 아니면 커밋하지 않는다.
4. **복구 레퍼런스**: fuse 누락 STL 은
   `cold_air_duct_repair/fuse_reinforce_duct.py` 방식(union → 살붙임 필렛 →
   sliver 제거)으로 보강한다.

## 도구
- `tools/check_stl.py` — STL 건전성 검증기 (CI/pre-commit 공용)
- `.github/workflows/stl-check.yml` — PR/push STL 자동 검사
- `.pre-commit-config.yaml`, `tools/install-git-hooks.sh` — 로컬 커밋 훅
