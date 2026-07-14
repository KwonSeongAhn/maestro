#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_stl.py — STL 건전성(FUSE/manifold) 검증 게이트.

이번처럼 "면·원통이 fuse 안 된(= 분리된 여러 바디, non-manifold seam)" STL 이
배포/커밋되는 것을 사전에 막기 위한 재사용 검사기.

사용:
    python3 check_stl.py part.stl [part2.stl ...]
    python3 check_stl.py --expect-genus 1 duct.stl   # 관통 덕트는 genus 1 기대

제외 목록:
    저장소 루트(또는 상위)의 `.stlcheckignore` (gitignore 스타일 glob)에 적힌
    파일은 검사에서 SKIP 한다. "수리 전" 원본/레퍼런스 등 의도적으로 보관하는
    입력 아티팩트를 제외하는 용도. --no-ignore 로 무시 가능.

종료코드: 0 = 모든 파일 PASS, 1 = 하나라도 FAIL  (CI/pre-commit 에서 그대로 사용)
"""
import argparse
import fnmatch
import os
import sys
import numpy as np
import trimesh


def load_ignore(start="."):
    """cwd 에서 위로 올라가며 첫 .stlcheckignore 를 찾아 glob 패턴 목록 반환."""
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".stlcheckignore")
        if os.path.isfile(p):
            pats = []
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pats.append(line.replace("\\", "/"))
            return pats, p
        nd = os.path.dirname(d)
        if nd == d:
            return [], None
        d = nd


def is_ignored(path, patterns):
    rp = os.path.normpath(path).replace("\\", "/")
    base = os.path.basename(rp)
    for pat in patterns:
        if (fnmatch.fnmatch(rp, pat) or fnmatch.fnmatch(base, pat)
                or fnmatch.fnmatch(rp, "*/" + pat.lstrip("/"))):
            return True
    return False


def check(path, expect_genus=None, expect_bodies=1):
    m = trimesh.load(path, process=True)
    m.merge_vertices()
    e = m.edges_sorted
    _, counts = np.unique(e, axis=0, return_counts=True)
    boundary = int((counts == 1).sum())
    nonmanifold = int((counts > 2).sum())
    bodies = m.body_count
    genus = None
    mstatus = "n/a"
    try:
        import manifold3d
        mm = manifold3d.Manifold(
            manifold3d.Mesh(m.vertices.astype("float32"), m.faces.astype("uint32")))
        mstatus = str(mm.status())
        genus = mm.genus()
    except Exception as ex:
        mstatus = "manifold3d 없음(%s)" % type(ex).__name__

    checks = [
        ("watertight",           m.is_watertight,               "열린 메쉬 — 구멍/틈 존재"),
        ("boundary edges = 0",   boundary == 0,                 "경계 edge %d 개" % boundary),
        ("non-manifold = 0",     nonmanifold == 0,              "non-manifold edge %d 개 (FUSE 안 됨 의심)" % nonmanifold),
        ("single body (=%d)" % expect_bodies, bodies == expect_bodies,
                                                                 "바디 %d 개 (분리된 솔리드 = FUSE 안 됨)" % bodies),
        ("winding consistent",   m.is_winding_consistent,       "면 방향 불일치"),
        ("positive volume",      m.volume > 0,                  "부피 %.1f (법선 반전 의심)" % m.volume),
    ]
    if expect_genus is not None and genus is not None:
        checks.append(("genus = %d" % expect_genus, genus == expect_genus,
                       "genus %s (예상 %d)" % (genus, expect_genus)))

    ok = all(passed for _, passed, _ in checks)
    print("\n=== %s ===" % path)
    print("  tri=%d  bodies=%d  boundary=%d  non-manifold=%d  genus=%s  manifold3d=%s"
          % (len(m.faces), bodies, boundary, nonmanifold, genus, mstatus))
    for name, passed, why in checks:
        print("  [%s] %-22s %s" % ("PASS" if passed else "FAIL", name, "" if passed else "-> " + why))
    print("  ==> %s" % ("PASS ✅" if ok else "FAIL ❌"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stl", nargs="+")
    ap.add_argument("--expect-genus", type=int, default=None,
                    help="기대 genus (관통 덕트=1, 막힌 솔리드=0)")
    ap.add_argument("--expect-bodies", type=int, default=1)
    ap.add_argument("--no-ignore", action="store_true",
                    help=".stlcheckignore 무시하고 모든 파일 검사")
    args = ap.parse_args()

    patterns, ig_path = ([], None) if args.no_ignore else load_ignore()
    if patterns:
        print("[.stlcheckignore] %s  (%d 패턴)" % (ig_path, len(patterns)))

    results = []
    for p in args.stl:
        if not args.no_ignore and is_ignored(p, patterns):
            print("\n=== %s ===\n  [SKIP] .stlcheckignore 제외 (레퍼런스/입력 아티팩트)" % p)
            continue
        results.append(check(p, args.expect_genus, args.expect_bodies))
    print("\n검사 %d개 중 %d개 PASS (제외 %d개)"
          % (len(results), sum(results), len(args.stl) - len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
