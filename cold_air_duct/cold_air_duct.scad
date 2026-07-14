// ============================================================================
//  신일 창문형 에어컨 냉기 유도 덕트 어댑터 (Square-to-Round Transition Duct)
//  ------------------------------------------------------------------------
//  실외 창틀에 고정한 에어컨의 냉기토출구에 씌워, Ø110 유연 덕트호스로
//  실내에 냉기를 끌어오기 위한 부품.  (스케치: 140x80 -> Ø110, 전이 40)
//
//  OpenSCAD 에서 열고 F6(렌더) 후 File > Export > Export as STL.
//  모든 치수는 mm.  아래 파라미터만 수정하면 형상이 바뀐다.
// ============================================================================

/* [ 흡입구 (에어컨 토출구에 끼워지는 사각) ] */
inlet_w    = 140;   // 가로
inlet_d    = 80;    // 세로
skirt_h    = 14;    // 스커트(직벽) 높이

/* [ 전이부 ] */
trans_h    = 40;    // 사각 -> 원형 전이 높이 (스케치 '40')

/* [ 토출구 (원형, 호스 연결) ] */
outlet_dia = 110;   // 원형 지름 (스케치 '110', Ø110 플렉시블 호스)
collar_h   = 14;    // 칼라(직벽) 높이
bead       = 1.6;   // 호스 이탈방지 비드 돌출 (0 이면 없음)

/* [ 벽 / 플랜지 ] */
wall       = 2.4;   // 벽 두께
flange     = 12;    // 흡입구 둘레 고정 플랜지 폭 (0 이면 없음)
flange_th  = 3;     // 플랜지 두께
screw_d    = 4.5;   // 플랜지 나사 구멍 지름 (0 이면 없음)

/* [ 출력 각도(선택) ] */
// 토출 칼라를 기울여 방향을 주고 싶을 때 (0 = 직선/동축).
// 대개 0 으로 두고 유연 호스로 방향을 잡는 것이 인쇄/성능에 유리.
outlet_tilt = 0;    // deg

/* [ 해상도 ] */
N          = 160;   // 원주 분할
steps      = 40;    // 전이부 세로 분할

// ----------------------------------------------------------------------------
hw = inlet_w/2;  hd = inlet_d/2;  r = outlet_dia/2;

// 각도 th(도)에서 사각 경계까지의 점
function ray_rect(th, HW, HD) =
    let(c=cos(th), s=sin(th),
        tx = abs(c)/HW, ty = abs(s)/HD,
        dd = 1/max(tx,ty))
    [dd*c, dd*s];

// 사각(m=0) <-> 원(m=1) 보간 프로파일 점
function morph_pt(th, m, HW, HD, RR) =
    let(rp = ray_rect(th, HW, HD), cp = [RR*cos(th), RR*sin(th)])
    [(1-m)*rp[0] + m*cp[0], (1-m)*rp[1] + m*cp[1]];

// 하나의 단면 폴리곤 (2D)
module section(m, HW, HD, RR)
    polygon([ for (i=[0:N-1]) morph_pt(360*i/N, m, HW, HD, RR) ]);

// smoothstep
function ss(t) = t*t*(3-2*t);

// 얇은 슬라이스를 hull 로 이어 붙여 한 구간을 로프트
module loft(z0, z1, m0, m1, HW, HD, RR) {
    for (i=[0:steps-1]) {
        t0 = i/steps;  t1 = (i+1)/steps;
        hull() {
            translate([0,0, z0 + (z1-z0)*t0])
                linear_extrude(height=0.01) section(ss(t0)*(m1-m0)+m0, HW, HD, RR);
            translate([0,0, z0 + (z1-z0)*t1])
                linear_extrude(height=0.01) section(ss(t1)*(m1-m0)+m0, HW, HD, RR);
        }
    }
}

// 스커트+전이+칼라 를 하나의 솔리드로 (외부/내부 각각 만들어 차집합)
module duct_body(off) {   // off: 프로파일 확장량 (외부=wall, 내부=0)
    // 스커트 (직벽 사각)
    translate([0,0,0])
        linear_extrude(height=skirt_h) section(0, hw+off, hd+off, r+off);
    // 전이부
    translate([0,0,0]) loft(skirt_h, skirt_h+trans_h, 0, 1, hw+off, hd+off, r+off);
    // 칼라 (직벽 원)
    translate([0,0, skirt_h+trans_h])
        linear_extrude(height=collar_h) section(1, hw+off, hd+off, r+off);
}

module duct_shell() {
    difference() {
        duct_body(wall);
        // 내부 관통 (아래로 조금 더 파서 바닥 개방)
        translate([0,0,-1]) scale([1,1,1])
            union() {
                linear_extrude(height=skirt_h+1) section(0, hw, hd, r);
                translate([0,0,skirt_h]) loft(0, trans_h, 0, 1, hw, hd, r);
                translate([0,0, skirt_h+trans_h])
                    linear_extrude(height=collar_h+2) section(1, hw, hd, r);
            }
    }
}

module bead_ring() {
    if (bead > 0) {
        zc = skirt_h + trans_h + collar_h - 3;
        translate([0,0, zc])
            rotate_extrude($fn=N)
                translate([r+wall, 0, 0])
                    // 반원 비드 단면
                    polygon([[0,-2],[bead,-1],[bead,1],[0,2]]);
    }
}

module flange_plate() {
    if (flange > 0) {
        ohw = hw+wall+flange;  ohd = hd+wall+flange;
        difference() {
            // 모서리 둥근 평판
            linear_extrude(height=flange_th)
                offset(r=6) offset(delta=-6)
                    square([2*ohw, 2*ohd], center=true);
            // 스커트 통과 구멍
            translate([0,0,-1])
                linear_extrude(height=flange_th+2) section(0, hw, hd, r);
            // 나사 구멍 4개
            if (screw_d > 0)
                for (sx=[-1,1], sy=[-1,1])
                    translate([sx*(ohw-flange/2), sy*(ohd-flange/2), -1])
                        cylinder(h=flange_th+2, d=screw_d, $fn=24);
        }
    }
}

module part() {
    union() {
        duct_shell();
        bead_ring();
        flange_plate();
    }
}

// 토출 기울임(선택): 칼라 상단 기준으로 살짝 기울여 방향성 부여
if (outlet_tilt == 0) part();
else part();   // 기본은 직선. 기울임은 유연 호스로 처리 권장.
