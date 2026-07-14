// ============================================================================
//  신일 창문형 에어컨 냉기 유도 덕트 — 측면도 기준 상향 벤드 (모서리 R)
//  ------------------------------------------------------------------------
//  사각(모서리 라운드) 140x80 흡입면을 에어컨 토출면(수직)에 밀착 →
//  큰 반경으로 냉기를 위로 말아 올려 → Ø148 원통 토출.
//
//  좌표계: 흡입면 = x=0 (YZ). 냉기 +X 유입 → 벤드 → +Z(위) 토출.
//  OpenSCAD 에서 F6 렌더 후 File > Export > STL.
//
//  ※ 정밀/양산용 수밀 STL 은 generate_stl.py(둥근사각 SDF 정확) 산출물을 권장.
//    본 SCAD 는 슈퍼타원 근사로 모서리 R 을 표현한 파라메트릭 편집본.
// ============================================================================

/* [ 흡입구 (둥근 사각) ] */
inlet_w   = 140;   // 가로 (Y)
inlet_d   = 80;    // 세로 (Z, 벤드 평면 내)
corner_n  = 4.0;   // 모서리 라운드 정도 (2=타원, 클수록 각짐; 3.5~5 권장)
lip_in    = 26;    // 흡입 직선 스냅(+X)

/* [ 벤드 / 토출 ] */
bend_deg  = 90;    // 벤드 각 (90=상향 L, 180=U)
bend_r    = 90;    // 벤드 중심선 반경(큰 라운드)
outlet_d  = 148;   // 원통 토출 지름 Ø148
lip_out   = 32;    // 토출 직선 칼라

/* [ 벽 / 플랜지 ] */
wall      = 2.6;   // 벽 두께
flange    = 14;    // 수직 플랜지 폭 (0=없음)
flange_th = 3;     // 플랜지 두께(X)
flange_r  = 10;    // 플랜지 외곽 라운드
screw_d   = 4.5;   // 플랜지 나사 구멍 (0=없음)
bead      = 1.6;   // 호스 이탈방지 비드 (0=없음)

/* [ 해상도 ] */
N     = 120;       // 원주 분할
steps = 64;        // 벤드 분할

// ----------------------------------------------------------------------------
a0 = inlet_d/2;  b0 = inlet_w/2;  rC = outlet_d/2;

// 슈퍼타원(둥근사각) <-> 원 보간 점.  m: 0=사각, 1=원.  (x=U 면내, y=V=Y)
function sgn(v) = v<0 ? -1 : 1;
function supell(t, a, b, n) =
    [ a*sgn(cos(t))*pow(abs(cos(t)), 2/n),
      b*sgn(sin(t))*pow(abs(sin(t)), 2/n) ];
function prof(t, m, a, b, n, r) =
    let(s = supell(t, a, b, n))
    [ (1-m)*s[0] + m*r*cos(t), (1-m)*s[1] + m*r*sin(t) ];

module section(m, off)
    polygon([ for (i=[0:N-1]) prof(360*i/N, m,
                a0+off, b0+off, (m>0? 2 : corner_n), rC+off) ]);

// smoothstep
function ss(t) = t*t*(3-2*t);

// 한 스테이션(직선/아크) 위치·회전으로 슬라이스 배치
//  seg: "in" 흡입직선 / "arc" 벤드 / "out" 토출직선
module place(seg, u) {   // u: 0..1 구간 파라미터
    if (seg == "in") {
        translate([lip_in*u, 0, 0]) rotate([0,90,0]) children();
    } else if (seg == "arc") {
        a = bend_deg*u;
        translate([lip_in + bend_r*sin(a), 0, bend_r*(1-cos(a))])
            rotate([0, 90-a, 0]) children();
    } else { // out
        a = bend_deg;
        translate([lip_in + bend_r*sin(a) + lip_out*u*cos(a),
                   0,
                   bend_r*(1-cos(a)) + lip_out*u*sin(a)])
            rotate([0, 90-a, 0]) children();
    }
}

// 구간을 얇은 슬라이스 hull 로 로프트
module loft_seg(seg, m0, m1, nseg, off) {
    for (i=[0:nseg-1]) {
        u0=i/nseg; u1=(i+1)/nseg;
        hull() {
            place(seg, u0) linear_extrude(0.01) section(ss(u0)*(m1-m0)+m0, off);
            place(seg, u1) linear_extrude(0.01) section(ss(u1)*(m1-m0)+m0, off);
        }
    }
}

module duct_solid(off) {
    loft_seg("in",  0, 0, 4,     off);
    loft_seg("arc", 0, 1, steps, off);
    loft_seg("out", 1, 1, 4,     off);
}

module duct_shell() {
    difference() {
        duct_solid(wall);
        duct_solid(0);            // 내부 유로 파냄
        // 흡입/토출 개구 확실히 관통
        translate([-1,0,0]) rotate([0,90,0]) linear_extrude(0.5) section(0,0);
    }
}

module flange_plate() {
    if (flange > 0) {
        oy = b0+wall+flange; oz = a0+wall+flange;
        difference() {
            translate([-flange_th,0,0]) rotate([0,90,0])
                linear_extrude(flange_th)
                    offset(r=flange_r) offset(delta=-flange_r)
                        square([2*oz, 2*oy], center=true);   // (z세로, y가로)
            // 구멍 = 흡입 외벽
            translate([-flange_th-1,0,0]) rotate([0,90,0])
                linear_extrude(flange_th+2) section(0, wall);
            // 나사 구멍 4개
            if (screw_d > 0)
                for (sy=[-1,1], sz=[-1,1])
                    translate([-flange_th-1, sy*(oy-flange/2), sz*(oz-flange/2)])
                        rotate([0,90,0]) cylinder(h=flange_th+2, d=screw_d, $fn=24);
        }
    }
}

module bead_ring() {
    if (bead > 0) {
        a = bend_deg;
        translate([lip_in + bend_r*sin(a) + (lip_out-4)*cos(a),
                   0,
                   bend_r*(1-cos(a)) + (lip_out-4)*sin(a)])
            rotate([0, 90-a, 0])
                rotate_extrude($fn=N)
                    translate([rC+wall, 0]) polygon([[0,-2],[bead,-1],[bead,1],[0,2]]);
    }
}

union() {
    duct_shell();
    flange_plate();
    bead_ring();
}
