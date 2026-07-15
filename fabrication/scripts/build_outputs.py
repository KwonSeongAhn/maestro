# -*- coding: utf-8 -*-
import os
from hopper_data import *

DWG="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/dwg"
OUTD="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/out"
os.makedirs(OUTD, exist_ok=True)

# ---------------- Build unified BOM (single source) ----------------
# columns: no, partno, kr, cn, material, spec, qty, unit, unitkg, process_kr, process_cn, remark
BOM=[]
def add(partno,kr,cn,mat,spec,qty,unit,unitkg,pk,pc,rem=""):
    BOM.append(dict(partno=partno,kr=kr,cn=cn,mat=mat,spec=spec,qty=qty,unit=unit,
                    unitkg=round(unitkg,2),totkg=round(unitkg*qty,2),pk=pk,pc=pc,rem=rem))

# 1) 철판 패널
for code,kr,cn,pc,edges,diags,area in PANELS:
    add(code,kr,cn,"SUS201 t4.0","전개도 참조 / 见展开图",1,"EA",plate_kg(area,4.0),
        "외주가공-판금/절곡/용접","外协-钣金/折弯/焊接",f"{pc}, {area:.3f}m²")
add("LBH-P11","피드슈트판","进料溜槽板","SUS201 t3.0","188×138.6",1,"EA",plate_kg(FEED_CHUTE_AREA,3.0),
    "외주가공-판금","外协-钣金","15° 경사")
add("LBH-P12","결합부 절곡판","接合部 折弯板","SUS201 t2.0","1251.7×85 절곡",2,"EA",plate_kg(FLANGE_AREA,2.0),
    "외주가공-판금/절곡","外协-钣金/折弯","M6 볼트홀 8")
# 2) 각파이프
for code,kr,cn,sec,ln,qty,mat,end in FRAME:
    if "×2.3t" in sec: ukg=pipe_kg_per_m(60,2.3)*ln/1000.0
    else: ukg=pipe_kg_per_m(60,2.3)*ln/1000.0
    add(code,kr,cn,f"{mat} {sec}",f"L{ln}",qty,"EA",ukg,
        "외주가공-절단/용접","外协-下料/焊接",end)
# 3) 캐스터
add("LBH-C01","중하중 캐스터","重载脚轮","PU/주철","Ø125×W50 200kg 선회+제동",8,"EA",3.2,
    "구매-표준품","采购-标准件","상판 105×85, 홀Ø11@80×60")
add("LBH-C02","캐스터 마운트판","脚轮安装板","STK400 t10","150×150",8,"EA",0.15*0.15*0.01*DENS_STK,
    "외주가공-절단/용접","外协-下料/焊接","4×Ø11 @80×60, 빔에 용접")
# 4) 보강재
rmat_kg={"□50×50×2.3t, L610":pipe_kg_per_m(50,2.3)*0.610,
         "t8, 100×84":0.10*0.084*0.008*DENS_STK,
         "t8, 70×72":0.07*0.072*0.008*DENS_STK,
         "t8, 70×80":0.07*0.080*0.008*DENS_STK,
         "t8, 100×72":0.10*0.072*0.008*DENS_STK,
         "■50×50, L242":solidbar_kg_per_m(50)*0.242,
         "t6, 520×100 (홀4/판)":0.52*0.10*0.006*DENS_STK}
for code,kr,cn,spec,qty,mat in REINF:
    add(code,kr,cn,mat,spec,qty,"EA",rmat_kg.get(spec,0),
        "외주가공-절단/용접","外协-下料/焊接","")
# 5) 체결부품
for code,kr,cn,spec,qty,rem in FASTENERS:
    add(code,kr,cn,"A2-70 (STS304)",spec,qty,"EA",0.02,"구매-표준품","采购-标准件",rem)
# 6) 부속
add("LBH-E01","제어 전장함(함체)","控制箱(箱体)","강판 t1.6 분체도장","400×220×150",1,"EA",6.0,
    "외주가공-판금(전장 별도)","外协-钣金(电装另计)","전장조립 별도, 인버터 제외")

TOTAL_KG=round(sum(b['totkg'] for b in BOM),1)

# ==================================================================
# XLSX  (표준 BOM 기본문서)
# ==================================================================
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
def build_xlsx():
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="BOM"
    thin=Side(style="thin",color="9AA4B2"); bd=Border(left=thin,right=thin,top=thin,bottom=thin)
    hdr_fill=PatternFill("solid",fgColor="1F2937"); cat_fill=PatternFill("solid",fgColor="E8EEF5")
    tot_fill=PatternFill("solid",fgColor="DFF0DF")
    center=Alignment(horizontal="center",vertical="center",wrap_text=True)
    left=Alignment(horizontal="left",vertical="center",wrap_text=True)
    # title
    ws.merge_cells("A1:L1")
    ws["A1"]=f"{META['title_kr']}  /  {META['title_cn']}  —  BOM (기본문서/基础文件)"
    ws["A1"].font=Font(bold=True,size=13); ws["A1"].alignment=center
    ws.merge_cells("A2:L2")
    ws["A2"]=f"문서번호 文件号 {META['docno']}   Rev.{META['rev']}   일자 日期 {META['date']}   품번규칙 编码规则: LBH-[P철판/F각파이프/C캐스터/R보강/B체결/E부속]-NN"
    ws["A2"].font=Font(size=9,color="555555"); ws["A2"].alignment=left
    heads=["No","품번\nPart No","품명(한)","品名(中)","재질\nMaterial","규격·사양\nSpec",
           "수량\nQty","단위\nUnit","단중(kg)","총중(kg)","제작구분\nProcess","비고 Remark"]
    r=3
    for c,h in enumerate(heads,1):
        cell=ws.cell(r,c,h); cell.font=Font(bold=True,color="FFFFFF",size=9)
        cell.fill=hdr_fill; cell.alignment=center; cell.border=bd
    r=4
    cat_of=lambda p:p.split("-")[1][0]
    cat_names={"P":"1. 호퍼 철판 / 料斗钢板","F":"2. 각파이프 프레임 / 方管框架","C":"3. 캐스터 / 脚轮",
               "R":"4. 보강재 / 加强件","B":"5. 체결부품 / 紧固件","E":"6. 부속 / 附件"}
    last_cat=None; no=0
    for b in BOM:
        cat=cat_of(b['partno'])
        if cat!=last_cat:
            ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=12)
            cc=ws.cell(r,1,cat_names[cat]); cc.font=Font(bold=True,size=10,color="8a4b00")
            cc.fill=cat_fill; cc.alignment=left; cc.border=bd
            r+=1; last_cat=cat
        no+=1
        vals=[no,b['partno'],b['kr'],b['cn'],b['mat'],b['spec'],b['qty'],b['unit'],
              b['unitkg'],b['totkg'],f"{b['pk']}\n{b['pc']}",b['rem']]
        for c,v in enumerate(vals,1):
            cell=ws.cell(r,c,v); cell.border=bd; cell.font=Font(size=9)
            cell.alignment=center if c in(1,2,5,7,8,9,10) else left
        r+=1
    # total
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=9)
    ws.cell(r,1,"합계 / 合计 (구조 강재 순중량, 캐스터·볼트 포함)").font=Font(bold=True)
    ws.cell(r,1).fill=tot_fill; ws.cell(r,1).alignment=left
    ws.cell(r,10,TOTAL_KG).font=Font(bold=True); ws.cell(r,10).fill=tot_fill; ws.cell(r,10).alignment=center
    for c in (11,12): ws.cell(r,c,"").fill=tot_fill
    for cc in range(1,13): ws.cell(r,cc).border=bd
    widths=[4,12,20,18,16,22,6,6,9,9,20,22]
    for i,w in enumerate(widths,1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width=w
    ws.row_dimensions[3].height=30
    ws.freeze_panes="A4"
    path=f"{OUTD}/{META['docno']}_BOM.xlsx"; wb.save(path); print("XLSX:",path,"items",no,"total",TOTAL_KG,"kg")
    return path

xlsx_path=build_xlsx()

# ==================================================================
# DOCX  (사양서 — 한/중)
# ==================================================================
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def build_docx(lang):
    CJK = "Malgun Gothic" if lang=="kr" else "Microsoft YaHei"
    def T(kr,cn): return kr if lang=="kr" else cn
    doc=Document()
    # page
    sec=doc.sections[0]
    sec.page_width=Mm(210); sec.page_height=Mm(297)
    for m in ("top_margin","bottom_margin"): setattr(sec,m,Mm(16))
    for m in ("left_margin","right_margin"): setattr(sec,m,Mm(16))
    # default font
    nf=doc.styles["Normal"].font; nf.name="Calibri"; nf.size=Pt(10)
    doc.styles["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"),CJK)

    def cjk(run,size=10,bold=False,color=None):
        run.font.name="Calibri"; run.font.size=Pt(size); run.font.bold=bold
        if color: run.font.color.rgb=RGBColor(*color)
        rpr=run._element.get_or_add_rPr(); rf=rpr.find(qn("w:rFonts"))
        if rf is None:
            rf=OxmlElement("w:rFonts"); rpr.append(rf)
        rf.set(qn("w:eastAsia"),CJK)
    def para(text,size=10,bold=False,color=None,after=4,align=None):
        p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(after)
        if align: p.alignment=align
        r=p.add_run(text); cjk(r,size,bold,color); return p
    def h1(n,text):
        p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(10); p.paragraph_format.space_after=Pt(5)
        r=p.add_run(f"{n}. {text}"); cjk(r,14,True,(0x11,0x33,0x55))
        pr=p._p.get_or_add_pPr(); pb=OxmlElement("w:pBdr"); bt=OxmlElement("w:bottom")
        bt.set(qn("w:val"),"single"); bt.set(qn("w:sz"),"12"); bt.set(qn("w:space"),"2"); bt.set(qn("w:color"),"2B6CB0")
        pb.append(bt); pr.append(pb)
    def h2(text):
        p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(6); p.paragraph_format.space_after=Pt(3)
        r=p.add_run(text); cjk(r,11,True,(0x2b,0x6c,0xb0))
    def table(headers, rows, widths=None, fs=8.5):
        t=doc.add_table(rows=1,cols=len(headers)); t.style="Table Grid"; t.alignment=WD_TABLE_ALIGNMENT.CENTER
        hc=t.rows[0].cells
        for i,htext in enumerate(headers):
            hc[i].text=""; r=hc[i].paragraphs[0].add_run(htext); cjk(r,fs,True,(0xff,0xff,0xff))
            hc[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
            sh=OxmlElement("w:shd"); sh.set(qn("w:fill"),"1F2937"); hc[i]._tc.get_or_add_tcPr().append(sh)
        for row in rows:
            cells=t.add_row().cells
            for i,v in enumerate(row):
                cells[i].text=""; rr=cells[i].paragraphs[0].add_run(str(v)); cjk(rr,fs)
                cells[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER if (widths and i in widths) else WD_ALIGN_PARAGRAPH.LEFT
        return t
    def img(path,w=168,cap=None):
        doc.add_picture(path,width=Mm(w))
        doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
        if cap: para(cap,8.5,False,(0x66,0x66,0x66),after=6,align=WD_ALIGN_PARAGRAPH.CENTER)

    # ---------- COVER ----------
    para(META["title_kr"] if lang=="kr" else META["title_cn"],20,True,(0x11,0x33,0x55),after=2)
    para(T("料斗制作规格书" if lang=="kr" else "호퍼 제작 사양서",
           "호퍼 제작 사양서" if lang=="kr" else "料斗制作规格书"),12,False,(0x55,0x55,0x55),after=8)
    table([T("항목","项目"),T("내용","内容")],
          [[T("문서번호","文件号"),META["docno"]],[T("개정","版本"),META["rev"]],[T("일자","日期"),META["date"]],
           [T("적용범위","适用范围"),T("호퍼 철판·각파이프·캐스터·보강재 (엘레베이터 제외)","料斗钢板·方管·脚轮·加强件 (不含提升机)")],
           [T("발주 형태","订购方式"),T("엘레베이터와 분리 발주 (보안). 본 사양 단독 완결","与提升机分开订购(保密)。本规格独立完整")],
           [T("총 강재중량","钢材总重"),f"≈ {TOTAL_KG} kg"],[T("도면단위","图纸单位"),"mm"]],
          widths={0}, fs=9.5)
    img(f"{DWG}/ga_iso.png",150,T("[참고] 호퍼 조립 형상 (철판+각파이프+캐스터+보강재)","[参考] 料斗总装形态 (钢板+方管+脚轮+加强件)"))

    # ---------- §0 DECISIONS ----------
    h1(0,T("설계 확정 사항 (질의 불요 · 제작 기준)","设计确定事项 (无需询问·制作基准)"))
    table([T("항목","项目"),T("확정 사양","确定规格")],
          [[T(a,b),c] for a,b,c in DECISIONS], widths={0})

    # ---------- §1 MATERIALS ----------
    h1(1,T("재질·마감·공차","材质·表面·公差"))
    table([T("구분","分类"),T("사양","规格")],
      [[T("호퍼 철판","料斗钢板"),"SUS201 t4.0 (2B), TIG"],
       [T("호퍼측 각파이프/림","料斗侧方管/缘"),T("SUS201 □60×60×2.3t","SUS201 □60×60×2.3t")],
       [T("프레임 각파이프","框架方管"),"STK400 (KS D3568) □60×60×2.3t"],
       [T("보강재","加强件"),"STK400 t6~t8 / □50×50"],
       [T("프레임 마감","框架涂装"),T("쇼트 Sa2.5 + 분체도장 RAL7016 80㎛","喷砂Sa2.5+粉末涂装RAL7016 80㎛")],
       [T("체결부품","紧固件"),"A2-70 (STS304), SHCS DIN912 (M5/M6/M10)"],
       [T("일반공차","一般公差"),"KS B ISO 2768-mK / 절곡 ±0.5° / 대각 ±1.5mm"]], widths={0})

    # ---------- §2 BOM ----------
    doc.add_page_break()
    h1(2,T("BOM (자재 명세 · 기본문서)","BOM (物料清单·基础文件)"))
    para(T("품번 규칙: LBH-[P철판/F각파이프/C캐스터/R보강/B체결/E부속]-일련번호",
           "编码规则: LBH-[P钢板/F方管/C脚轮/R加强/B紧固/E附件]-序号"),8.5,False,(0x55,0x55,0x55))
    bom_head=[T("품번","品番"),T("품명","品名"),T("재질","材质"),T("규격","规格"),
              T("수량","数量"),T("단중","单重"),T("총중","总重"),T("제작구분","加工"),T("비고","备注")]
    bom_rows=[]
    for b in BOM:
        bom_rows.append([b["partno"], T(b["kr"],b["cn"]), b["mat"], b["spec"], b["qty"],
                         b["unitkg"], b["totkg"], T(b["pk"],b["pc"]), b["rem"]])
    bom_rows.append([T("합계 合计","合计"),"","","","","",TOTAL_KG,"",""])
    table(bom_head,bom_rows,widths={0,4,5,6},fs=7.5)

    # ---------- §3 PLATE DEVELOPMENT ----------
    doc.add_page_break()
    h1(3,T("호퍼 철판 전개도","料斗钢板展开图"))
    para(T("각 패널은 평판에서 절단(레이저/플라즈마) 후 절곡·용접. 치수=내면 기준, 단위 mm. 변길이(적색)+대각선 D1/D2로 완전 정의.",
           "各板从平板下料(激光/等离子)后折弯·焊接。尺寸=内表面基准,单位mm。边长(红)+对角线D1/D2完全定义。"),9)
    h2(T("패널 치수표","板尺寸表"))
    prows=[]
    for code,kr,cn,pc,edges,diags,area in PANELS:
        prows.append([code,T(kr,cn),"/".join(f"{e:.1f}" for e in edges),
                      "/".join(f"{d:.1f}" for d in diags) if diags else "-",f"{area:.3f}",1])
    table([T("품번","品番"),T("품명","品名"),T("변길이(mm)","边长"),T("대각선 D1/D2","对角线"),"m²",T("수량","数量")],
          prows,widths={0,4,5},fs=8)
    img(f"{DWG}/dev_front.png",168)
    img(f"{DWG}/dev_side.png",168)
    img(f"{DWG}/dev_rear.png",150)

    # ---------- §4 FRAME ----------
    doc.add_page_break()
    h1(4,T("각파이프 프레임 · 절단표","方管框架·下料表"))
    frows=[[c,T(kr,cn),f"{mat} {sec}",f"L{ln}",qty,T(end,end)] for c,kr,cn,sec,ln,qty,mat,end in FRAME]
    table([T("품번","品番"),T("품명","品名"),T("단면·재질","截面·材质"),T("길이","长度"),T("수량","数量"),T("단부","端部")],
          frows,widths={0,3,4},fs=8)
    img(f"{DWG}/frame_plan.png",168,T("프레임 평면도 (캐스터 C1~C8 위치 + 마운트 홀)","框架平面图 (脚轮C1~C8位置+安装孔)"))
    img(f"{DWG}/frame_elev.png",160,T("프레임 입면도 (높이)","框架立面图 (高度)"))

    # ---------- §5 HOLES ----------
    doc.add_page_break()
    h1(5,T("홀 위치 (캐스터 마운트)","孔位 (脚轮安装)"))
    para(T("각 캐스터 마운트판(150×150×10)에 M10 4홀(Ø11), 패턴 80×60. 좌표=프레임 로컬(X,Z), mm.",
           "每脚轮安装板(150×150×10)开M10 4孔(Ø11),阵列80×60。坐标=框架本地(X,Z),mm。"),9)
    img(f"{DWG}/caster_detail.png",95,T("캐스터 마운트판 홀 상세","脚轮安装板孔详图"))
    hrows=[[cid,f"{cx:+.0f}",f"{cz:+.1f}",T("(X±40, Z±30) 4홀 Ø11","(X±40,Z±30) 4孔Ø11")] for cid,cx,cz in CASTERS]
    table([T("캐스터","脚轮"),T("중심 X","中心X"),T("중심 Z","中心Z"),T("홀 패턴","孔阵列")],hrows,widths={0,1,2},fs=8.5)
    para(T("· 고정 절편(LBH-R07) 홀: 판 중심 대칭 4홀 (Z±227.45 × Y±25), M10 관통 Ø11.  · 결합부 절곡판(LBH-P12): M6 8홀.",
           "· 固定片(LBH-R07)孔: 板中心对称4孔 (Z±227.45×Y±25), M10通孔Ø11。 · 接合折弯板(LBH-P12): M6 8孔。"),8.5,False,(0x33,0x33,0x33))

    # ---------- §6 STANDARD PARTS ----------
    h1(6,T("표준품 사양 (구매)","标准件规格 (采购)"))
    h2(T(CASTER_SPEC["kr"]+" (LBH-C01)",CASTER_SPEC["cn"]+" (LBH-C01)"))
    table([T("항목","项目"),T("사양","规格")],[list(r) for r in CASTER_SPEC["rows"]],widths={0})
    h2(T("체결부품 (SUS201 A2-70, SHCS DIN912)","紧固件 (SUS201 A2-70, SHCS DIN912)"))
    table([T("품번","品番"),T("품명","品名"),T("규격","规格"),T("수량","数量"),T("용도","用途")],
          [[c,T(kr,cn),spec,qty,rem] for c,kr,cn,spec,qty,rem in FASTENERS],widths={0,3},fs=8)

    # ---------- §7 WELDING ----------
    h1(7,T("용접·표면처리 사양","焊接·表面处理规格"))
    table([T("부위","部位"),T("사양","规格")],[[T(a,b),c] for a,b,c in WELDS],widths=None)
    para(T("※ SUS201와 STK400 직접 용접 금지 — 계면은 M10 볼트 결합. 전 용접부 슬래그 제거·비드 연속.",
           "※ 禁止SUS201与STK400直接焊接 — 界面用M10螺栓连接。所有焊缝清渣·连续。"),8.5,False,(0xc0,0x39,0x2b))

    # ---------- §8 ----------
    h1(8,T("부속·발주범위 주기","附件·订购范围备注"))
    para(T("· LBH-E01 제어 전장함: 판금 함체만 본 발주 포함. 내부 전장(Arduino/드라이버) 조립은 별도 계통.\n"
           "· 인버터(BLD-AC750S)는 본 발주 제외.\n· 본 사양은 엘레베이터와 분리 발주(보안)이며 단독으로 제작 가능.",
           "· LBH-E01 控制箱: 仅钣金箱体列入本次订购。内部电装(Arduino/驱动器)另行装配。\n"
           "· 变频器(BLD-AC750S)不在本次订购范围。\n· 本规格与提升机分开订购(保密),可独立制作。"),9)

    path=f"{OUTD}/{META['docno']}_{'KR' if lang=='kr' else 'CN'}.docx"
    doc.save(path); print("DOCX:",path)
    return path

kr=build_docx("kr"); cn=build_docx("cn")
print("DONE")
