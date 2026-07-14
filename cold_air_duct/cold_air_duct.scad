// ============================================================================
//  신일 창문형 에어컨 냉기 유도 덕트 — 측면도 기준 상향 벤드 (모서리 R)
//  ------------------------------------------------------------------------
//  사각(모서리 라운드) 140x80 흡입면을 에어컨 토출면(수직)에 밀착 →
//  큰 반경으로 냉기를 90° 옆(수평)으로 꺾어 → 보어 Ø142 원통(외부 수나사) 토출.
//  토출 원통 바깥면 나선 수나사에 Ø150 유연 호스/커넥터가 돌려 끼워짐.
//
//  좌표계: 흡입면 = x=0 (YZ). 냉기 +X 유입 → 벤드(X-Y 평면) → +Y(수평 옆) 토출.
//  OpenSCAD 에서 F6 렌더 후 File > Export > STL.
//
//  ※ 정밀/양산용 수밀 STL 은 generate_stl.py(둥근사각 SDF 정확) 산출물을 권장.
//    본 SCAD 는 슈퍼타원 근사로 모서리 R 을 표현한 파라메트릭 편집본.
// ============================================================================

/* [ 흡입구 (둥근 사각) ] */
inlet_w   = 140;   // 가로 (Y)
inlet_d   = 80;    // 세로 (Z, 벤드 평면 내)
corner_n  = 4.0;   // 모서리 라운드 정도 (2=타원, 클수록 각짐; 3.5~5 권장)
lip_in    = 8;     // 흡입 직선 스냅(+X) — 최소화

/* [ 벤드 / 토출 ] */
bend_deg  = 90;    // 벤드 각 (90=옆으로 수평, 180=반대편)
bend_r    = 80;    // 벤드 중심선 반경(꺾임 거리 최소화)
outlet_d  = 142;   // 원통 토출 보어(내경) — Ø150 호스 안에 들어가도록
lip_out   = 223;   // 토출 직선 원통 길이(연장). 전체 ~390mm

/* [ 토출 외부 수나사 (Ø150 호스/커넥터 체결) ] */
thread_on    = true;
pitch        = 15;   // 나사 피치(호스 주름 간격 실측·조정)
thr_round    = 2.0;  // 나사산 단면 반경(마루 = 칼라외경 + 이 값)
starts       = 2;    // 나사 줄 수
thr_len      = 42;   // 나사부 길이(원통 끝단에만)
thr_margin   = 3;    // 끝단 여유

/* [ 벽 / 플랜지 ] */
wall      = 2.6;   // 벽 두께
flange    = 14;    // 수직 플랜지 폭 (0=없음)
flange_th = 3;     // 플랜지 두께(X)
flange_r  = 10;    // 플랜지 외곽 라운드
screw_d   = 4.5;   // 플랜지 나사 구멍 (0=없음)
bead      = 0;     // 호스 이탈방지 비드(나사산으로 대체, 0=없음)
mount_r    = 250;  // 접촉면 수직(세로) 곡률 반경 (0=평면)
mount_start= 1/3;  // 세로 아래에서 이 비율 지점부터 곡면(그 아래 평면)

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
// 벤드 평면 = X-Y(수평). 토출은 옆(+Y) 방향.
module place(seg, u) {   // u: 0..1 구간 파라미터
    if (seg == "in") {
        translate([lip_in*u, 0, 0]) rotate([0,90,0]) children();
    } else if (seg == "arc") {
        a = bend_deg*u;
        translate([lip_in + bend_r*sin(a), bend_r*(1-cos(a)), 0])
            rotate([0,0,a]) rotate([0,90,0]) children();
    } else { // out
        a = bend_deg;
        translate([lip_in + bend_r*sin(a) + lip_out*u*cos(a),
                   bend_r*(1-cos(a)) + lip_out*u*sin(a),
                   0])
            rotate([0,0,a]) rotate([0,90,0]) children();
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

// 플랜지 외곽 2D (둥근 사각). extrude 평면 XY: x→세로(Z), y→가로(Y)
module flange_outline() {
    oy = b0+wall+flange; oz = a0+wall+flange;
    offset(r=flange_r) offset(delta=-flange_r) square([2*oz, 2*oy], center=true);
}

module flange_plate() {
    if (flange > 0) {
        oy = b0+wall+flange; oz = a0+wall+flange;
        z_start = -oz + 2*oz*mount_start;          // 아래에서 1/3 지점
        dtop    = oz - z_start;
        maxsag  = (mount_r>0) ? mount_r - sqrt(max(0, mount_r*mount_r - dtop*dtop)) : 0;
        difference() {
            union() {
                // 평판 (뒷면 x=-flange_th)
                translate([-flange_th,0,0]) rotate([0,90,0])
                    linear_extrude(flange_th) flange_outline();
                // 수직 접촉 곡면 쐐기: z_start 위쪽 뒷면을 곡면까지 채움
                if (mount_r > 0)
                    difference() {
                        intersection() {
                            translate([-flange_th-maxsag,0,0]) rotate([0,90,0])
                                linear_extrude(maxsag) flange_outline();
                            translate([-500,-500,z_start]) cube([1000,1000,1000]); // Z>z_start
                        }
                        // 카빙 실린더(축=Y, z_start에서 평면에 접함, 반경 mount_r)
                        translate([-flange_th-mount_r, 0, z_start])
                            rotate([90,0,0]) cylinder(h=1000, r=mount_r, center=true, $fn=180);
                    }
            }
            // 구멍 = 흡입 외벽
            translate([-flange_th-maxsag-1,0,0]) rotate([0,90,0])
                linear_extrude(flange_th+maxsag+2) section(0, wall);
            // 나사 구멍 4개
            if (screw_d > 0)
                for (sy=[-1,1], sz=[-1,1])
                    translate([-flange_th-maxsag-1, sy*(oy-flange/2), sz*(oz-flange/2)])
                        rotate([0,90,0]) cylinder(h=flange_th+maxsag+2, d=screw_d, $fn=24);
        }
    }
}

module bead_ring() {
    if (bead > 0) {
        a = bend_deg;
        translate([lip_in + bend_r*sin(a) + (lip_out-4)*cos(a),
                   bend_r*(1-cos(a)) + (lip_out-4)*sin(a),
                   0])
            rotate([0,0,a]) rotate([0,90,0])
                rotate_extrude($fn=N)
                    translate([rC+wall, 0]) polygon([[0,-2],[bead,-1],[bead,1],[0,2]]);
    }
}

// 토출 외부 수나사: 월드좌표 나선 위에 구를 hull 로 이어 코일 형성
module thread_coil() {
    if (thread_on) {
        Te  = [cos(bend_deg), sin(bend_deg), 0];      // 토출 진행방향(단위)
        Uax = [-sin(bend_deg), cos(bend_deg), 0];     // 면내 반경축
        Vax = [0, 0, 1];                              // 면밖(세로)축
        aC  = [lip_in + bend_r*sin(bend_deg), bend_r*(1-cos(bend_deg)), 0]; // 칼라 시작
        rr  = outlet_d/2 + wall;                      // 칼라 외경(나사 골 표면)
        s1 = lip_out - thr_margin; s0 = max(thr_margin, s1 - thr_len);
        steps = ceil((s1-s0)/pitch*24);
        for (k=[0:starts-1])
            for (i=[0:steps-1]) {
                sa = s0 + (s1-s0)*i/steps;    sb = s0 + (s1-s0)*(i+1)/steps;
                pa = 360*sa/pitch + 360*k/starts;
                pb = 360*sb/pitch + 360*k/starts;
                Ha = aC + sa*Te + rr*(cos(pa)*Uax + sin(pa)*Vax);
                Hb = aC + sb*Te + rr*(cos(pb)*Uax + sin(pb)*Vax);
                hull() {
                    translate(Ha) sphere(r=thr_round, $fn=14);
                    translate(Hb) sphere(r=thr_round, $fn=14);
                }
            }
    }
}

union() {
    duct_shell();
    flange_plate();
    bead_ring();
    thread_coil();
}
