# -*- coding: utf-8 -*-
# 호퍼 철판 전개도 + 프레임 도면 SVG 생성 → PNG
import math, os
import cairosvg

OUT = "/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/dwg"
os.makedirs(OUT, exist_ok=True)

t30 = math.tan(math.radians(30))
faceBotZ=-259.25; topW=1400; topD=1300; Hf=580; H=1148; inletD=138.56; opnHW=94
frontTopZ=faceBotZ-Hf*t30; backTopZ=frontTopZ+topD
frontTopZ_H=faceBotZ-H*t30; backThroatZ=faceBotZ+inletD

# vertices (x,y,z)
B_FL=(-94,0,faceBotZ);      B_FR=(94,0,faceBotZ)
B_BR=(94,0,backThroatZ);    B_BL=(-94,0,backThroatZ)
F_FL=(-topW/2,Hf,frontTopZ);F_FR=(topW/2,Hf,frontTopZ)
F_BR=(topW/2,Hf,backTopZ);  F_BL=(-topW/2,Hf,backTopZ)
F_oL=(-opnHW,Hf,frontTopZ); F_oR=(opnHW,Hf,frontTopZ)
T_BL=(-topW/2,H,backTopZ);  T_BR=(topW/2,H,backTopZ)
T_FLn=(-topW/2,H,frontTopZ_H); T_FRn=(topW/2,H,frontTopZ_H)
T_oLn=(-opnHW,H,frontTopZ_H);  T_oRn=(opnHW,H,frontTopZ_H)

def dist(a,b): return math.dist(a,b)

def flatten(pts):
    """Triangulated development of planar/warped polygon to 2D. Returns list of (x,y)."""
    n=len(pts)
    P=[None]*n
    P[0]=(0.0,0.0)
    P[1]=(dist(pts[0],pts[1]),0.0)
    # triangle fan from v0
    for i in range(2,n):
        r0=dist(pts[0],pts[i]); rp=dist(pts[i-1],pts[i])
        x0,y0=P[0]; x1,y1=P[i-1]
        d=math.dist(P[0],P[i-1])
        # circle intersection: |Q-P0|=r0, |Q-P_{i-1}|=rp
        a=(r0*r0-rp*rp+d*d)/(2*d)
        h2=r0*r0-a*a
        h=math.sqrt(max(h2,0))
        ux,uy=((x1-x0)/d,(y1-y0)/d)
        mx,my=(x0+a*ux, y0+a*uy)
        # normal (perp), choose +side (y>previous) to keep convex unfolding
        px,py=(-uy,ux)
        cand1=(mx+h*px, my+h*py); cand2=(mx-h*px, my-h*py)
        # pick the one with larger y (above the fan base) for consistent layout
        P[i]= cand1 if cand1[1]>=cand2[1] else cand2
    return P

PANELS = [
 ("P1","Front-Upper-L",[T_FLn,T_oLn,F_oL,F_FL]),
 ("P2","Front-Upper-R",[T_oRn,T_FRn,F_FR,F_oR]),
 ("P3","Front-Lower-L",[F_FL,F_oL,B_FL]),
 ("P4","Front-Lower-R",[F_oR,F_FR,B_FR]),
 ("P5","Left-Vertical",[T_BL,T_FLn,F_FL,F_BL]),
 ("P6","Left-Funnel",[F_BL,F_FL,B_FL,B_BL]),
 ("P7","Right-Vertical",[T_FRn,T_BR,F_BR,F_FR]),
 ("P8","Right-Funnel",[F_FR,F_BR,B_BR,B_FR]),
 ("P9","Rear-Vertical",[T_BR,T_BL,F_BL,F_BR]),
 ("P10","Rear-Funnel",[F_BR,F_BL,B_BL,B_BR]),
]

def newell_area(pts):
    nx=ny=nz=0
    for i in range(len(pts)):
        a=pts[i]; b=pts[(i+1)%len(pts)]
        nx+=(a[1]-b[1])*(a[2]+b[2]); ny+=(a[2]-b[2])*(a[0]+b[0]); nz+=(a[0]-b[0])*(a[1]+b[1])
    return 0.5*math.hypot(nx,ny,nz)

# ---- summary print ----
print("PANEL FLAT-PATTERN DATA (mm)")
tot=0
data=[]
for code,name,pts in PANELS:
    fp=flatten(pts)
    edges=[dist(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts))]
    diags=[]
    if len(pts)==4:
        diags=[dist(pts[0],pts[2]), dist(pts[1],pts[3])]
    area=newell_area(pts)/1e6; tot+=area
    data.append((code,name,fp,edges,diags,area))
    es="/".join(f"{e:.1f}" for e in edges)
    ds="/".join(f"{d:.1f}" for d in diags) if diags else "-"
    print(f"{code:4s} edges {es:34s} diag {ds:20s} area {area:.4f}")
print(f"TOTAL plate area (10 panels) = {tot:.3f} m2")

# ============================ SVG DRAWING ENGINE ============================
def _poly_bounds(P):
    xs=[p[0] for p in P]; ys=[p[1] for p in P]
    return min(xs),min(ys),max(xs),max(ys)

def draw_panel_svg(fp, edges, diags, code, box=380, pad=64):
    """Return (svg_inner, w, h) for one flat panel, dimensioned, scaled to box."""
    minx,miny,maxx,maxy=_poly_bounds(fp)
    w_mm=maxx-minx; h_mm=maxy-miny
    scale=(box-2*pad)/max(w_mm,h_mm)
    W=w_mm*scale+2*pad; Hh=h_mm*scale+2*pad
    def tx(x): return (x-minx)*scale+pad
    def ty(y): return Hh-((y-miny)*scale+pad)   # flip y
    s=[]
    # polygon
    pth=" ".join(f"{'M' if i==0 else 'L'}{tx(x):.1f},{ty(y):.1f}" for i,(x,y) in enumerate(fp))+" Z"
    s.append(f'<path d="{pth}" fill="#eaf2fb" stroke="#123" stroke-width="2.2"/>')
    # diagonals dashed
    n=len(fp)
    if n==4:
        for (i,j) in [(0,2),(1,3)]:
            s.append(f'<line x1="{tx(fp[i][0]):.1f}" y1="{ty(fp[i][1]):.1f}" x2="{tx(fp[j][0]):.1f}" y2="{ty(fp[j][1]):.1f}" stroke="#c0392b" stroke-width="1" stroke-dasharray="6 4"/>')
    # vertices
    labs="ABCD"
    for i,(x,y) in enumerate(fp):
        s.append(f'<circle cx="{tx(x):.1f}" cy="{ty(y):.1f}" r="3.4" fill="#123"/>')
        s.append(f'<text x="{tx(x)+7:.1f}" y="{ty(y)-6:.1f}" font-size="15" font-weight="700" fill="#123">{labs[i]}</text>')
    # edge dims
    for i in range(n):
        a=fp[i]; b=fp[(i+1)%n]
        mx=(tx(a[0])+tx(b[0]))/2; my=(ty(a[1])+ty(b[1]))/2
        # offset outward from centroid
        cx=sum(tx(p[0]) for p in fp)/n; cy=sum(ty(p[1]) for p in fp)/n
        ox=mx-cx; oy=my-cy; L=math.hypot(ox,oy) or 1
        lx=mx+ox/L*20; ly=my+oy/L*20
        s.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="16" font-weight="700" fill="#c0392b" text-anchor="middle">{edges[i]:.1f}</text>')
    # diagonal dims (offset along diagonal to avoid overlap)
    if n==4 and diags:
        fracs=[0.30,0.70]
        for k,(i,j) in enumerate([(0,2),(1,3)]):
            f=fracs[k]
            mx=tx(fp[i][0])*(1-f)+tx(fp[j][0])*f; my=ty(fp[i][1])*(1-f)+ty(fp[j][1])*f
            s.append(f'<rect x="{mx-42:.1f}" y="{my-13:.1f}" width="84" height="16" fill="white" opacity="0.75"/>')
            s.append(f'<text x="{mx:.1f}" y="{my:.1f}" font-size="12.5" fill="#7a1f16" text-anchor="middle">D{k+1}={diags[k]:.1f}</text>')
    return "".join(s), W, Hh

def sheet(panels_subset, title, fname, cols=2, cell=400):
    rows=math.ceil(len(panels_subset)/cols)
    cw=cell; ch=cell+40
    W=cols*cw+40; Hh=rows*ch+90
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>')
    parts.append(f'<text x="20" y="34" font-size="22" font-weight="800" fill="#123">{title}</text>')
    parts.append(f'<text x="20" y="56" font-size="13" fill="#555">Material: SUS201 t4.0  |  Dim in mm  |  A/B/C/D = vertices, red=edge len, D1/D2=diagonals</text>')
    for idx,(code,name,fp,edges,diags,area) in enumerate(panels_subset):
        r=idx//cols; c=idx%cols
        ox=20+c*cw; oy=76+r*ch
        inner,pw,ph=draw_panel_svg(fp,edges,diags,code,box=cell-30)
        # center in cell
        dx=ox+(cw-pw)/2; dy=oy+(ch-40-ph)/2
        parts.append(f'<g transform="translate({dx:.1f},{dy:.1f})">{inner}</g>')
        parts.append(f'<text x="{ox+cw/2:.1f}" y="{oy+ch-14}" font-size="16" font-weight="700" fill="#123" text-anchor="middle">{code}  {name}    Area {area:.3f} m2</text>')
        parts.append(f'<rect x="{ox}" y="{oy}" width="{cw-8}" height="{ch-8}" fill="none" stroke="#ccd" stroke-width="1"/>')
    parts.append('</svg>')
    svg="".join(parts)
    with open(f"{OUT}/{fname}.svg","w") as f: f.write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/{fname}.png", output_width=int(W*1.6))
    print(f"wrote {fname}.png ({W}x{Hh})")

# build panel data list matching PANELS order
PD=[]
for code,name,pts in PANELS:
    fp=flatten(pts)
    edges=[dist(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts))]
    diags=[dist(pts[0],pts[2]),dist(pts[1],pts[3])] if len(pts)==4 else []
    area=newell_area(pts)/1e6
    PD.append((code,name,fp,edges,diags,area))

sheet(PD[0:4], "HOPPER PLATE DEVELOPMENT - Sheet 1/3 (Front Panels)", "dev_front", cols=2, cell=400)
sheet(PD[4:8], "HOPPER PLATE DEVELOPMENT - Sheet 2/3 (Side Panels)", "dev_side", cols=2, cell=430)
sheet(PD[8:10],"HOPPER PLATE DEVELOPMENT - Sheet 3/3 (Rear Panels)", "dev_rear", cols=2, cell=430)

# ============================ FRAME DRAWINGS ============================
frameOuterX=732; iz_front=890.05; iz_rear=737.89; SEC=60  # spec 60x60 (model nominal 64)
casters=[("C1",-732,-890.05),("C2",732,-890.05),("C3",0,-890.05),
         ("C4",-732,737.89),("C5",732,737.89),("C8",0,737.89),
         ("C6",-732,0),("C7",732,0)]
# caster mount plate & hole pattern
PLATE=150; HOLE_DX=40; HOLE_DZ=30  # 80x60 pattern (M12)

def svg_header(W,H,title,sub=""):
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="white"/>',
       f'<text x="20" y="34" font-size="22" font-weight="800" fill="#123">{title}</text>']
    if sub: p.append(f'<text x="20" y="56" font-size="13" fill="#555">{sub}</text>')
    return p

def frame_plan():
    # plan: X horizontal, Z vertical (front -890 at bottom)
    minX,maxX=-800,900; minZ,maxZ=-980,830
    W=1220; H=1140; pad=90
    sx=(W-2*pad)/(maxX-minX); sz=(H-160-pad)/(maxZ-minZ)
    sc=min(sx,sz)
    def X(x): return pad+(x-minX)*sc
    def Z(z): return (H-pad)-(z-minZ)*sc   # front(-890) near bottom
    p=svg_header(W,H,"FRAME PLAN (Top View)","Square tube 60x60x2.3t STK400 | Caster mount plate 150x150x10 | Dim in mm (frame-local coord)")
    # perimeter beams (draw as tube width)
    def beam(x1,z1,x2,z2):
        # thick line
        p.append(f'<line x1="{X(x1):.1f}" y1="{Z(z1):.1f}" x2="{X(x2):.1f}" y2="{Z(z2):.1f}" stroke="#5a6472" stroke-width="{SEC*sc:.1f}" stroke-linecap="butt" opacity="0.55"/>')
        p.append(f'<line x1="{X(x1):.1f}" y1="{Z(z1):.1f}" x2="{X(x2):.1f}" y2="{Z(z2):.1f}" stroke="#233" stroke-width="1.2"/>')
    beam(-732,-890.05,732,-890.05)  # front
    beam(-732,737.89,732,737.89)    # rear
    beam(-732,-890.05,-732,737.89)  # left
    beam(732,-890.05,732,737.89)    # right
    beam(-732,-120.69,732,-120.69)  # cross bar (hopper support)
    # throat opening (X +-94, Z -259.25..-120.69)
    p.append(f'<rect x="{X(-94):.1f}" y="{Z(-120.69):.1f}" width="{(188)*sc:.1f}" height="{(138.56)*sc:.1f}" fill="#d9ecff" stroke="#2b6cb0" stroke-width="1.5" stroke-dasharray="5 3"/>')
    p.append(f'<text x="{X(0):.1f}" y="{Z(-190):.1f}" font-size="12" fill="#2b6cb0" text-anchor="middle">THROAT 188x138.6</text>')
    # casters + mount plates + holes
    for cid,cx,cz in casters:
        p.append(f'<rect x="{X(cx)-PLATE*sc/2:.1f}" y="{Z(cz)-PLATE*sc/2:.1f}" width="{PLATE*sc:.1f}" height="{PLATE*sc:.1f}" fill="none" stroke="#c0392b" stroke-width="1.6"/>')
        for hx in (-HOLE_DX,HOLE_DX):
            for hz in (-HOLE_DZ,HOLE_DZ):
                p.append(f'<circle cx="{X(cx+hx):.1f}" cy="{Z(cz+hz):.1f}" r="3.2" fill="none" stroke="#c0392b" stroke-width="1.4"/>')
        p.append(f'<circle cx="{X(cx):.1f}" cy="{Z(cz):.1f}" r="2" fill="#123"/>')
        p.append(f'<text x="{X(cx):.1f}" y="{Z(cz)-PLATE*sc/2-6:.1f}" font-size="14" font-weight="700" fill="#c0392b" text-anchor="middle">{cid}</text>')
    # dims: overall width between post centers 1464, front-back
    def dimH(x1,x2,z,txt,off=40):
        y=Z(z)+off
        p.append(f'<line x1="{X(x1):.1f}" y1="{y}" x2="{X(x2):.1f}" y2="{y}" stroke="#123" stroke-width="1"/>')
        for xx in (x1,x2): p.append(f'<line x1="{X(xx):.1f}" y1="{y-5}" x2="{X(xx):.1f}" y2="{y+5}" stroke="#123" stroke-width="1"/>')
        p.append(f'<text x="{(X(x1)+X(x2))/2:.1f}" y="{y-6}" font-size="14" fill="#123" text-anchor="middle">{txt}</text>')
    def dimV(z1,z2,x,txt,off=40):
        xx=X(x)+off
        p.append(f'<line x1="{xx}" y1="{Z(z1):.1f}" x2="{xx}" y2="{Z(z2):.1f}" stroke="#123" stroke-width="1"/>')
        for zz in (z1,z2): p.append(f'<line x1="{xx-5}" y1="{Z(zz):.1f}" x2="{xx+5}" y2="{Z(zz):.1f}" stroke="#123" stroke-width="1"/>')
        p.append(f'<text x="{xx+6}" y="{(Z(z1)+Z(z2))/2:.1f}" font-size="14" fill="#123">{txt}</text>')
    dimH(-732,732,-890.05,"1464 (post c/c)",off=150)
    dimV(-890.05,737.89,732,"1627.9 (front-rear c/c)",off=55)
    dimV(-890.05,-120.69,-732,"769.4",off=-70)
    dimV(-120.69,737.89,-732,"858.6",off=-70)
    p.append('</svg>')
    svg="".join(p)
    open(f"{OUT}/frame_plan.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/frame_plan.png", output_width=int(W*1.6))
    print("wrote frame_plan.png")

def frame_elev():
    W=980;H=760;pad=80
    # front elevation: X horizontal, Y vertical
    minX,maxX=-820,820; minY,maxY=0,1360
    sc=min((W-2*pad)/(maxX-minX),(H-140-pad)/(maxY-minY))
    def X(x): return pad+(x-minX)*sc
    def Y(y): return (H-pad)-(y-minY)*sc
    p=svg_header(W,H,"FRAME ELEVATION (Front View)","Heights in mm (frame-local Y, floor=0). Hopper body shown ghosted.")
    def hbeam(x1,x2,y):
        p.append(f'<line x1="{X(x1):.1f}" y1="{Y(y):.1f}" x2="{X(x2):.1f}" y2="{Y(y):.1f}" stroke="#5a6472" stroke-width="{SEC*sc:.1f}" opacity="0.55"/>')
    def vpost(x,y1,y2):
        p.append(f'<line x1="{X(x):.1f}" y1="{Y(y1):.1f}" x2="{X(x):.1f}" y2="{Y(y2):.1f}" stroke="#5a6472" stroke-width="{SEC*sc:.1f}" opacity="0.55"/>')
    # base beam Y173, top ring Y494
    hbeam(-732,732,173); hbeam(-732,732,494)
    vpost(-732,173,494); vpost(732,173,494); vpost(0,173,494)
    # legs to casters (Y0..173)
    for x in (-732,0,732): p.append(f'<line x1="{X(x):.1f}" y1="{Y(173):.1f}" x2="{X(x):.1f}" y2="{Y(30):.1f}" stroke="#5a6472" stroke-width="{SEC*sc:.1f}" opacity="0.55"/>')
    # casters
    for x in (-732,0,732):
        p.append(f'<circle cx="{X(x):.1f}" cy="{Y(60):.1f}" r="{60*sc:.1f}" fill="none" stroke="#c0392b" stroke-width="2"/>')
    # hopper ghost (throat Y170ish up to 1318 world -> local ~1148+170) draw trapezoid
    p.append(f'<path d="M{X(-94):.1f},{Y(170):.1f} L{X(-700):.1f},{Y(760):.1f} L{X(-700):.1f},{Y(1318):.1f} L{X(700):.1f},{Y(1318):.1f} L{X(700):.1f},{Y(760):.1f} L{X(94):.1f},{Y(170):.1f}" fill="#eaf7f8" stroke="#4a8" stroke-width="1.3" opacity="0.5"/>')
    # dims
    def dimV(y1,y2,x,txt,off=0):
        xx=X(x)+off
        p.append(f'<line x1="{xx}" y1="{Y(y1):.1f}" x2="{xx}" y2="{Y(y2):.1f}" stroke="#123" stroke-width="1"/>')
        for yy in (y1,y2): p.append(f'<line x1="{xx-5}" y1="{Y(yy):.1f}" x2="{xx+5}" y2="{Y(yy):.1f}" stroke="#123" stroke-width="1"/>')
        p.append(f'<text x="{xx+7}" y="{(Y(y1)+Y(y2))/2:.1f}" font-size="13" fill="#123">{txt}</text>')
    dimV(0,120,760,"120 wheel",off=40)
    dimV(120,173,760,"53",off=40)
    dimV(173,494,760,"321 leg",off=40)
    dimV(494,1318,760,"824",off=40)
    dimV(0,1318,-760,"1318 overall H",off=-70)
    p.append('</svg>')
    svg="".join(p); open(f"{OUT}/frame_elev.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/frame_elev.png", output_width=int(W*1.6))
    print("wrote frame_elev.png")

def caster_detail():
    W=560;H=560;pad=110; box=PLATE
    sc=(W-2*pad)/box
    cx0=W/2; cy0=H/2+10
    def X(x): return cx0+x*sc
    def Y(y): return cy0-y*sc
    p=svg_header(W,H,"CASTER MOUNT PLATE DETAIL","Plate 150x150x10 (welded to base beam) + top-plate caster D120, M12x4")
    p.append(f'<rect x="{X(-box/2):.1f}" y="{Y(box/2):.1f}" width="{box*sc:.1f}" height="{box*sc:.1f}" fill="#eef3f9" stroke="#123" stroke-width="2"/>')
    for hx in (-HOLE_DX,HOLE_DX):
        for hy in (-HOLE_DZ,HOLE_DZ):
            p.append(f'<circle cx="{X(hx):.1f}" cy="{Y(hy):.1f}" r="{6.5*sc:.1f}" fill="white" stroke="#c0392b" stroke-width="1.8"/>')
            p.append(f'<line x1="{X(hx)-9}" y1="{Y(hy):.1f}" x2="{X(hx)+9}" y2="{Y(hy):.1f}" stroke="#c0392b" stroke-width="0.8"/>')
            p.append(f'<line x1="{X(hx):.1f}" y1="{Y(hy)-9}" x2="{X(hx):.1f}" y2="{Y(hy)+9}" stroke="#c0392b" stroke-width="0.8"/>')
    # dims
    p.append(f'<text x="{X(0):.1f}" y="{Y(box/2)-14:.1f}" font-size="15" fill="#123" text-anchor="middle">150</text>')
    p.append(f'<text x="{X(-box/2)-40:.1f}" y="{Y(0):.1f}" font-size="15" fill="#123" text-anchor="middle">150</text>')
    p.append(f'<text x="{X(0):.1f}" y="{Y(HOLE_DZ)-8:.1f}" font-size="13" fill="#c0392b" text-anchor="middle">80</text>')
    p.append(f'<line x1="{X(-HOLE_DX):.1f}" y1="{Y(HOLE_DZ)+3:.1f}" x2="{X(HOLE_DX):.1f}" y2="{Y(HOLE_DZ)+3:.1f}" stroke="#c0392b" stroke-width="0.9"/>')
    p.append(f'<text x="{X(HOLE_DX)+22:.1f}" y="{Y(0):.1f}" font-size="13" fill="#c0392b" text-anchor="middle">60</text>')
    p.append(f'<line x1="{X(HOLE_DX)+3:.1f}" y1="{Y(-HOLE_DZ):.1f}" x2="{X(HOLE_DX)+3:.1f}" y2="{Y(HOLE_DZ):.1f}" stroke="#c0392b" stroke-width="0.9"/>')
    p.append(f'<text x="{X(0):.1f}" y="{Y(-box/2)-20:.1f}" font-size="13" fill="#c0392b" text-anchor="middle">4 x M10 (drill 11.0), pattern 80 x 60</text>')
    p.append('</svg>')
    svg="".join(p); open(f"{OUT}/caster_detail.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/caster_detail.png", output_width=int(W*1.7))
    print("wrote caster_detail.png")

frame_plan(); frame_elev(); caster_detail()
print("ALL DRAWINGS DONE")
