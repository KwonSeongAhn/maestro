#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fuse_reinforce_duct.py
======================
Cold-air-duct (신일 AC 라운드 엘보 140x80 -> D148) STL 보수 스크립트.

[문제 진단]  (원본 STL 계측 결과)
  업로드된 STL 은 하나의 솔리드가 아니라 서로 "닿아만 있는" 4개의 독립 솔리드였다.
      comp0 : 메인 엘보 본체        (58240 tri, watertight)
      comp1 : D148 출구 링/원통 A   (1896 tri, watertight)
      comp2 : D148 출구 링/원통 B   (1896 tri, watertight)
      comp3 : 사각(140x80) 플랜지 면 (1280 tri, watertight)
  - naked(경계) edge = 0   ->  fill_holes() 로는 고칠 게 없음(열린 구멍 자체가 없음).
  - non-manifold edge = 160 ->  면/원통이 본체에 겹쳐/맞닿아만 있고 boolean UNION 으로
    FUSE 되지 않은 상태. 이것이 "FUSING 안 됨"의 실체.
  - 플랜지 접합부(X=0) 사각 둘레의 덕트 벽 두께 = 2.6mm 로 매우 얇음(칼날 접합).

[보수 방법]
  1) manifold3d 엔진으로 4개 솔리드를 boolean UNION -> 하나의 watertight 솔리드로 융합
     (면 + 원통 + 본체가 실제로 FUSE 됨).
  2) 플랜지 면 <-> 덕트 본체 접합부(X=0 사각 둘레)를 따라, 벽/플랜지 안쪽으로 깊게
     겹치는 삼각형 거싯 단면을 스윕하여 "두꺼운 살붙임" 필렛을 생성(보어는 침범 안 함).
  3) 필렛까지 UNION 하고, boolean 부산물(미세 sliver) 제거 -> 최종 단일
     watertight / manifold(genus-1 파이프) 솔리드로 출력.
"""
import argparse
import numpy as np
import trimesh

ENGINE = "manifold"


def topo(mesh):
    e = mesh.edges_sorted
    _, counts = np.unique(e, axis=0, return_counts=True)
    return int((counts == 1).sum()), int((counts > 2).sum())


def genus(mesh):
    try:
        import manifold3d
        mm = manifold3d.Manifold(
            manifold3d.Mesh(mesh.vertices.astype("float32"), mesh.faces.astype("uint32")))
        return mm.status(), mm.genus()
    except Exception as e:  # pragma: no cover
        return ("n/a:%s" % e), None


def load_components(path):
    m = trimesh.load(path, process=True)
    m.merge_vertices()
    comps = sorted(m.split(only_watertight=False), key=lambda c: -len(c.faces))
    return m, comps


def junction_loop(solid, x_plane=0.0, outer=True):
    """X=x_plane 단면의 접합 둘레(바깥/안쪽) 폴리라인 (closed, (n,3))."""
    sec = solid.section(plane_origin=[x_plane + 1e-3, 0, 0], plane_normal=[1, 0, 0])
    if sec is None:
        raise RuntimeError("section() 실패: X=%.3f 교차 없음" % x_plane)
    loops = [np.asarray(L) for L in sec.discrete]
    loops.sort(key=lambda L: (L[:, 1].max() - L[:, 1].min()) * (L[:, 2].max() - L[:, 2].min()))
    loop = loops[-1] if outer else loops[0]
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    return loop


def fillet_ring(loop, section2d):
    """
    평면(X≈0) 접합 둘레(loop)를 따라 국부 단면 section2d=[(dx,dr),...] 를 스윕한
    닫힌 프리즘 링 솔리드. dx=X방향(축), dr=외곽 반경방향(+바깥). 벽/플랜지 안으로
    깊게 겹치도록 단면을 잡아 boolean 이 강건하게 처리되게 한다.
    """
    P = loop.copy()
    N = len(P)
    ctr = P[:, 1:].mean(0)
    T = np.zeros((N, 3))
    for i in range(N):
        T[i] = P[(i + 1) % N] - P[(i - 1) % N]
    T[:, 0] = 0
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    e1 = np.array([1.0, 0.0, 0.0])                        # 축(X, 평면 밖)
    e2 = np.stack([np.zeros(N), -T[:, 2], T[:, 1]], 1)   # 평면 내 법선
    radial = np.concatenate([np.zeros((N, 1)), P[:, 1:] - ctr], 1)
    e2[np.sum(e2 * radial, 1) < 0] *= -1                 # 바깥 방향으로 정렬
    M = len(section2d)
    sec = np.asarray(section2d, float)
    verts = np.zeros((N * M, 3))
    for i in range(N):
        verts[i * M:(i + 1) * M] = P[i] + np.outer(sec[:, 0], e1) + np.outer(sec[:, 1], e2[i])
    faces = []
    for i in range(N):
        i2 = (i + 1) % N
        for k in range(M):
            k2 = (k + 1) % M
            a, b = i * M + k, i * M + k2
            c, d = i2 * M + k2, i2 * M + k
            faces.append([a, b, c])
            faces.append([a, c, d])
    t = trimesh.Trimesh(verts, np.array(faces), process=True)
    t.merge_vertices()
    if t.volume < 0:
        t.invert()
    return t


def keep_main_body(mesh, min_faces=64):
    """boolean 부산물(미세 sliver) 제거 -> 최대 연결성분만 반환."""
    comps = mesh.split(only_watertight=False)
    if len(comps) <= 1:
        return mesh
    comps = sorted(comps, key=lambda c: -len(c.faces))
    dropped = [(len(c.faces), round(float(c.volume), 3)) for c in comps[1:]]
    print("    sliver 제거: %d개 %s" % (len(dropped), dropped))
    return comps[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    # 삼각형 거싯 필렛 단면 (dx, dr) mm : 벽/플랜지로 2mm 파고들고, 축방향 14mm·반경 12mm 살붙임
    ap.add_argument("--sec-axis", type=float, default=14.0, help="필렛 축방향 길이(mm)")
    ap.add_argument("--sec-rise", type=float, default=12.0, help="필렛 반경방향 높이(mm)")
    ap.add_argument("--sec-bite", type=float, default=2.0, help="벽/플랜지 파고듦 깊이(mm)")
    ap.add_argument("--back", type=float, default=4.0, help="플랜지쪽(-X) 파고듦(mm)")
    args = ap.parse_args()

    print("[*] load:", args.inp)
    orig, comps = load_components(args.inp)
    nb, nm = topo(orig)
    print("    입력  : faces=%d watertight=%s boundary=%d nonmanifold=%d bodies=%d"
          % (len(orig.faces), orig.is_watertight, nb, nm, len(comps)))
    labels = ["메인 엘보 본체", "출구 링/원통 A", "출구 링/원통 B", "사각 플랜지 면"]
    for i, c in enumerate(comps):
        print("      comp[%d] %-14s faces=%-6d watertight=%s ext=%s"
              % (i, labels[i] if i < len(labels) else "", len(c.faces),
                 c.is_watertight, np.round(c.bounds[1] - c.bounds[0], 1)))

    # 1) 4개 솔리드 FUSE
    print("[*] step1: boolean UNION (manifold) — 4 solids -> 1  (면+원통+본체 융합)")
    fused = trimesh.boolean.union(comps, engine=ENGINE)
    nb, nm = topo(fused)
    st, g = genus(fused)
    print("    융합후: faces=%d watertight=%s boundary=%d nonmanifold=%d bodies=%d genus=%s vol=%.1f"
          % (len(fused.faces), fused.is_watertight, nb, nm, fused.body_count, g, fused.volume))

    # 2) 플랜지 접합부 두꺼운 살붙임 필렛
    print("[*] step2: 플랜지 접합부 살붙임 필렛 생성")
    loop = junction_loop(fused, x_plane=0.0, outer=True)
    perim = np.linalg.norm(np.diff(np.vstack([loop, loop[:1]]), axis=0), axis=1).sum()
    print("    접합 둘레: pts=%d perimeter=%.1fmm Y=%.1f..%.1f Z=%.1f..%.1f"
          % (len(loop), perim, loop[:, 1].min(), loop[:, 1].max(),
             loop[:, 2].min(), loop[:, 2].max()))
    b = args.sec_bite
    section2d = [(-args.back, -b), (args.sec_axis, -b), (-args.back, args.sec_rise)]
    ring = fillet_ring(loop, section2d)
    print("    필렛: faces=%d watertight=%s vol=%.1f 단면=%s"
          % (len(ring.faces), ring.is_watertight, ring.volume, section2d))

    # 3) 필렛 UNION + sliver 정리
    print("[*] step3: 필렛 UNION -> sliver 제거 -> 최종")
    final = trimesh.boolean.union([fused, ring], engine=ENGINE)
    final = keep_main_body(final)
    final.merge_vertices()
    final.remove_unreferenced_vertices()

    nb, nm = topo(final)
    st, g = genus(final)
    print("    최종  : faces=%d watertight=%s boundary=%d nonmanifold=%d bodies=%d genus=%s"
          % (len(final.faces), final.is_watertight, nb, nm, final.body_count, g))
    print("    volume=%.1f  euler=%d  winding_consistent=%s  manifold_status=%s"
          % (final.volume, final.euler_number, final.is_winding_consistent, st))

    final.export(args.out)
    print("[+] saved:", args.out)

    ok = final.is_watertight and nb == 0 and nm == 0 and final.body_count == 1 and g == 1
    print("[%s] 검증: %s" % ("PASS" if ok else "WARN",
          "단일 watertight/manifold(genus-1) 솔리드로 FUSE + 살붙임 보강 완료"
          if ok else "추가 확인 필요"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
