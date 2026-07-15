# LOSTBALL 부품 제작·발주 문서 패키지 (LBH)

로스트볼 선별설비의 전 부품을 **3D프린트 / 외주가공**으로 분류하고, 발주·제작에
바로 쓰는 문서(한국어·중국어)와 STL을 생성한다. 데이터 원천은
`lostball_simulation.html`(Three.js 시뮬)의 실계측 지오메트리다.

## 발주 정책
- **호퍼**는 엘레베이터(핵심 침수버킷 승강 기구)와 **분리하여 중국 제작업체**에 발주한다(보안).
- 호퍼 발주에는 엘레베이터를 제외하되, 호퍼에 볼팅된 철판·보강·전장함 등 연결 금속은 모두 포함(인버터만 제외).
- 각파이프는 시스템 전체를 통합해 호퍼 제작업체에 턴키 발주.
- 재질: 호퍼 철판 **SUS201**(가성비, 304 오버스펙 회피), 프레임 STK400.

## 산출물 (`package/LBH_PACKAGE_ALL.zip`)
| 문서 | 내용 |
|---|---|
| LBH-COVER-001 | 발주 패키지 표지 |
| LBH-FAB-001 | 호퍼 철판·캐스터·보강 사양서 + BOM(xlsx) |
| LBH-PIPE-001 | 호퍼 각파이프 발주서 + 절단표 |
| LBH-PIPE-SYS-001 | 시스템 전체 각파이프 통합 + 절단표 |
| LBH-RFQ-001 | 견적요청서(RFQ) + 견적서 |
| LBH-ELEV-001 | 엘레베이터 금속장치 명세 + BOM (3D프린트 제외) |
| LBH-3DP-001 | 3D프린트 부품 명세 (62부품, 전량 수밀) |
| LBH-3DP-PARTS-FINAL.zip | STL 62종 + manifest + hole_schedule + 살덧붙임 규칙 |

모든 문서는 KR/CN 2판. 부품번호 규칙 `LBH-[P철판/F각파이프/C캐스터/R보강/B체결/E부속]-NN`.

## 3D프린트 파이프라인 (`scripts/`)
1. `extract_parts.js` / `extract_stl.js` — 시뮬 씬에서 메시별 STL·메타 추출(Playwright).
2. `dedupe_parts.py` — 회전·미러·이동 불변 시그니처로 중복 통합(1 STL + 수량).
3. `extract_fasteners.js` / `extract_thumbsockets.js` — 211개 체결·33개 섬스크류 실계측 위치.
4. `threadlib.py` — 프린트용 굵은 나사(M5×P2.0) 엔진(섬스크류·너트·소켓 통일).
5. `build_final.py` / `cut_holes.py` — 기능별 홀 절삭(THROUGH=clearHole 관통 / TAP=tapDrill 블라인드).
6. `build_p01_p15.py` — 솔리드화 불가 부품 파라메트릭 재구성.
7. `reinforce2.py` — **살덧붙임 규칙**(아래).
8. `build_3dp_final.py` — 최종 명세서(docx) 생성.

## 살덧붙임(Wall Reinforcement) 규칙
`RULE_3DP_WALL_REINFORCE.md` 참조. 기준 품질: `cold_air_duct_fused.stl`
(수밀 1바디·균일벽·필렛). 62부품 스캔 결과 실제 얇은엣지 부품은 **P32 1종**뿐이며,
복셀 팽창 0.8mm(벽+1.6, 엣지 필렛) + M5 통공 4 재절삭으로 보강 완료
(p1 0.43→1.40mm, <1.5mm 2.9%→1.3%). P30 얇은점은 나사산 크레스트(정상, 제외), P23은 챔퍼(합격).

## 재현
스크립트는 세션 스크래치패드 절대경로를 사용한다(`SP=...`). 재실행 시 경로를 로컬로 수정하고,
`trimesh manifold3d rtree scipy scikit-image fast-simplification python-docx openpyxl` 설치가 필요하다.
