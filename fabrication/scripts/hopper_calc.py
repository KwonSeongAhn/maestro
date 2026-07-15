import math

t30 = math.tan(math.radians(30))
faceBotZ = -259.25
topW, topD = 1400, 1300
Hf, H = 580, 1148
inletD = 138.56
opnHW = 94

frontTopZ   = faceBotZ - Hf*t30      # -594.11
backTopZ    = frontTopZ + topD       # 705.89
frontTopZ_H = faceBotZ - H*t30       # -922.05
backThroatZ = faceBotZ + inletD      # -120.69

# vertices
B_FL=(-94,0,faceBotZ);      B_FR=(94,0,faceBotZ)
B_BR=(94,0,backThroatZ);    B_BL=(-94,0,backThroatZ)
F_FL=(-topW/2,Hf,frontTopZ);F_FR=(topW/2,Hf,frontTopZ)
F_BR=(topW/2,Hf,backTopZ);  F_BL=(-topW/2,Hf,backTopZ)
F_oL=(-opnHW,Hf,frontTopZ); F_oR=(opnHW,Hf,frontTopZ)
T_BL=(-topW/2,H,backTopZ);  T_BR=(topW/2,H,backTopZ)
T_FLn=(-topW/2,H,frontTopZ_H); T_FRn=(topW/2,H,frontTopZ_H)
T_oLn=(-opnHW,H,frontTopZ_H);  T_oRn=(opnHW,H,frontTopZ_H)

def d(a,b): return math.dist(a,b)
def area_poly(pts):
    # Newell area of planar polygon in 3D
    n=[0,0,0]
    for i in range(len(pts)):
        a=pts[i]; b=pts[(i+1)%len(pts)]
        n[0]+=(a[1]-b[1])*(a[2]+b[2])
        n[1]+=(a[2]-b[2])*(a[0]+b[0])
        n[2]+=(a[0]-b[0])*(a[1]+b[1])
    return 0.5*math.sqrt(n[0]**2+n[1]**2+n[2]**2)

panels = {
 "전면상부좌(4각)": [T_FLn,T_oLn,F_oL,F_FL],
 "전면상부우(4각)": [T_oRn,T_FRn,F_FR,F_oR],
 "전면하부좌(3각)": [F_FL,F_oL,B_FL],
 "전면하부우(3각)": [F_oR,F_FR,B_FR],
 "좌수직(4각)":    [T_BL,T_FLn,F_FL,F_BL],
 "좌깔대기(4각)":  [F_BL,F_FL,B_FL,B_BL],
 "우수직(4각)":    [T_FRn,T_BR,F_BR,F_FR],
 "우깔대기(4각)":  [F_FR,F_BR,B_BR,B_FR],
 "후수직(4각)":    [T_BR,T_BL,F_BL,F_BR],
 "후깔대기(4각)":  [F_BR,F_BL,B_BL,B_BR],
}
print(f"frontTopZ={frontTopZ:.2f} backTopZ={backTopZ:.2f} frontTopZ_H={frontTopZ_H:.2f} backThroatZ={backThroatZ:.2f}")
print(f"throat slot: X {2*94}mm  Z {inletD}mm")
print("="*78)
total=0
for name,pts in panels.items():
    edges=[d(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts))]
    a=area_poly(pts)/1e6
    total+=a
    es=" / ".join(f"{e:.1f}" for e in edges)
    print(f"{name:16s} 변길이(mm): {es:38s} 면적 {a:.4f} m2")
print("="*78)
print(f"철판 합계 면적(전면+측면+후면, 절곡판/슈트 제외): {total:.3f} m2")
# feed chute
scLen=abs(faceBotZ-backThroatZ)
print(f"15deg 피드슈트: 188 x {scLen:.1f} mm  면적 {188*scLen/1e6:.4f} m2")
