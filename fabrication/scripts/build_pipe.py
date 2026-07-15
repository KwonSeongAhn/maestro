# -*- coding: utf-8 -*-
"""호퍼 각파이프 종합 외주 발주서 (docx 한/중 + 절단표 xlsx)."""
import os, math
DWG="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/dwg"
OUTD="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/out"
os.makedirs(OUTD,exist_ok=True)
DOCNO="LBH-PIPE-001"; REV="A"; DATE="2026-07-14"

# 각파이프 전량: (품번, kr, cn, 단면, 재질, 길이mm, 수량, 부위kr, 부위cn, 단부kr, 단부cn)
PIPES=[
 ("LP-01","베이스 전/후빔","底架 前/后梁","□60×60×2.3t","STK400",1528,2,"대차 프레임","台车框架","양단 맞대기","两端对接"),
 ("LP-02","베이스 사이드빔","底架 侧梁","□60×60×2.3t","STK400",1692,2,"대차 프레임","台车框架","양단 맞대기","两端对接"),
 ("LP-03","호퍼받침 가로바","料斗承托横杆","□60×60×2.3t","STK400",1528,1,"대차 프레임","台车框架","양단 필렛","两端角焊"),
 ("LP-04","상단링 전/후빔","上环 前/后梁","□60×60×2.3t","STK400",1528,2,"대차 프레임","台车框架","양단 맞대기","两端对接"),
 ("LP-05","상단링 사이드빔","上环 侧梁","□60×60×2.3t","STK400",1692,2,"대차 프레임","台车框架","양단 맞대기","两端对接"),
 ("LP-06","수직 다리","立柱腿","□60×60×2.3t","STK400",257,7,"대차 프레임","台车框架","상하 맞대기","上下对接"),
 ("LP-07","하부보강 수직기둥","下部加强立柱","□50×50×2.3t","STK400",610,2,"결합부 보강","接合加强","상하 맞대기/용접","上下对接/焊接"),
 ("LP-08","상부보강 각봉(중실)","上部加强方钢(实心)","■50×50 SOLID","STK400",242,2,"결합부 보강","接合加强","양단 면직각 절단","两端垂直切"),
 ("LP-09","결합부 직사각 강관","接合部 矩形钢管","□30×60×2.3t","STK400",1252,2,"결합부 보강","接合加强","angX -30° 경사부착","angX-30°斜装"),
 ("LP-10","코너 포스트","角立柱","□60×60×2.3t","SUS201",792,4,"호퍼 본체","料斗本体","호퍼측 용접","料斗侧焊接"),
 ("LP-11","상단 림 전면","上缘 前","□60×60×2.3t","SUS201",638,2,"호퍼 본체","料斗本体","코너 45° 마이터","角部45°斜接"),
 ("LP-12","상단 림 후면","上缘 后","□60×60×2.3t","SUS201",1464,1,"호퍼 본체","料斗本体","코너 45° 마이터","角部45°斜接"),
 ("LP-13","상단 림 사이드","上缘 侧","□60×60×2.3t","SUS201",1692,2,"호퍼 본체","料斗本体","코너 45° 마이터","角部45°斜接"),
]
def total_len_m(items): return sum(l*q for *_,l,q,_,_,_,_ in [ (p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9],p[10]) for p in items])  # placeholder

# 조달 요약: 단면×재질 그룹
from collections import OrderedDict
groups=OrderedDict()
for p in PIPES:
    key=(p[3],p[4])  # section, material
    groups.setdefault(key,0)
    groups[key]+=p[5]*p[6]
STOCK={ "□60×60×2.3t":6000, "□50×50×2.3t":6000, "■50×50 SOLID":1000, "□30×60×2.3t":6000 }
PROC=[]
for (sec,mat),tot in groups.items():
    stock=STOCK[sec]
    need=tot*1.10  # 10% 절단손실
    bars=max(1,math.ceil(need/stock))
    PROC.append((sec,mat,round(tot/1000,2),stock/1000,bars,round(bars*stock/1000,1)))
GRAND=round(sum(p[5]*p[6] for p in PIPES)/1000,2)

# ============ XLSX (절단표 + 조달요약) ============
import openpyxl
from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
def xlsx():
    wb=openpyxl.Workbook()
    thin=Side(style="thin",color="9AA4B2"); bd=Border(left=thin,right=thin,top=thin,bottom=thin)
    hf=PatternFill("solid",fgColor="1F2937"); gf=PatternFill("solid",fgColor="E8EEF5"); tf=PatternFill("solid",fgColor="DFF0DF")
    ctr=Alignment(horizontal="center",vertical="center",wrap_text=True); lft=Alignment(horizontal="left",vertical="center",wrap_text=True)
    # sheet1 조달요약
    ws=wb.active; ws.title="조달요약 采购汇总"
    ws.merge_cells("A1:F1"); ws["A1"]=f"각파이프 종합 조달 요약 / 方管综合采购汇总  ({DOCNO} Rev.{REV})"; ws["A1"].font=Font(bold=True,size=12); ws["A1"].alignment=ctr
    heads=["단면 截面","재질 材质","총소요(m) 需求","정척(m) 定尺","소요본수 根数","발주총량(m) 订购"]
    for c,h in enumerate(heads,1):
        cell=ws.cell(3,c,h); cell.font=Font(bold=True,color="FFFFFF"); cell.fill=hf; cell.alignment=ctr; cell.border=bd
    r=4
    for sec,mat,tot,stock,bars,order in PROC:
        for c,v in enumerate([sec,mat,tot,stock,bars,order],1):
            cell=ws.cell(r,c,v); cell.border=bd; cell.alignment=ctr; cell.font=Font(size=10)
        r+=1
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=2); ws.cell(r,1,"합계 合计").font=Font(bold=True); ws.cell(r,1).fill=tf; ws.cell(r,1).alignment=ctr
    ws.cell(r,3,GRAND).font=Font(bold=True); ws.cell(r,3).fill=tf; ws.cell(r,3).alignment=ctr
    for c in (4,5,6): ws.cell(r,c,"").fill=tf
    for c in range(1,7): ws.cell(r,c).border=bd
    for i,w in enumerate([16,12,12,10,12,14],1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width=w
    ws.row_dimensions[3].height=28
    # sheet2 절단표
    ws2=wb.create_sheet("절단표 下料表")
    ws2.merge_cells("A1:I1"); ws2["A1"]=f"각파이프 절단표 / 方管下料表  ({DOCNO})  ※길이 mm, 일반공차 절단 ±1.0mm"; ws2["A1"].font=Font(bold=True,size=12); ws2["A1"].alignment=ctr
    h2=["No","품번 品番","부위 部位","품명 品名","단면 截面","재질 材质","길이 长度","수량 数量","단부·비고 端部·备注"]
    for c,h in enumerate(h2,1):
        cell=ws2.cell(3,c,h); cell.font=Font(bold=True,color="FFFFFF"); cell.fill=hf; cell.alignment=ctr; cell.border=bd
    r=4
    for i,p in enumerate(PIPES,1):
        vals=[i,p[0],f"{p[7]}\n{p[8]}",f"{p[1]}\n{p[2]}",p[3],p[4],p[5],p[6],f"{p[9]}\n{p[10]}"]
        for c,v in enumerate(vals,1):
            cell=ws2.cell(r,c,v); cell.border=bd; cell.font=Font(size=9)
            cell.alignment=ctr if c in(1,2,5,6,7,8) else lft
        r+=1
    ws2.merge_cells(start_row=r,start_column=1,end_row=r,end_column=6); ws2.cell(r,1,"총 연장 总延长 (m)").font=Font(bold=True); ws2.cell(r,1).fill=tf; ws2.cell(r,1).alignment=ctr
    ws2.cell(r,7,GRAND).font=Font(bold=True); ws2.cell(r,7).fill=tf; ws2.cell(r,7).alignment=ctr
    for c in (8,9): ws2.cell(r,c,"").fill=tf
    for c in range(1,10): ws2.cell(r,c).border=bd
    for i,w in enumerate([4,10,14,20,15,10,9,7,22],1): ws2.column_dimensions[openpyxl.utils.get_column_letter(i)].width=w
    ws2.row_dimensions[3].height=26; ws2.freeze_panes="A4"
    path=f"{OUTD}/{DOCNO}_CUTLIST.xlsx"; wb.save(path); print("XLSX:",path)
xlsx()

# ============ DOCX (한/중) ============
from docx import Document
from docx.shared import Pt,Mm,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
def build(lang):
    CJK="Malgun Gothic" if lang=="kr" else "Microsoft YaHei"
    def T(kr,cn): return kr if lang=="kr" else cn
    doc=Document(); sec=doc.sections[0]
    sec.page_width=Mm(210); sec.page_height=Mm(297)
    for m in ("top_margin","bottom_margin","left_margin","right_margin"): setattr(sec,m,Mm(16))
    nf=doc.styles["Normal"].font; nf.name="Calibri"; nf.size=Pt(10)
    doc.styles["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"),CJK)
    def cjk(run,size=10,bold=False,color=None):
        run.font.name="Calibri"; run.font.size=Pt(size); run.font.bold=bold
        if color: run.font.color.rgb=RGBColor(*color)
        rpr=run._element.get_or_add_rPr(); rf=rpr.find(qn("w:rFonts"))
        if rf is None: rf=OxmlElement("w:rFonts"); rpr.append(rf)
        rf.set(qn("w:eastAsia"),CJK)
    def para(t,s=10,b=False,c=None,after=4,al=None):
        p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(after)
        if al: p.alignment=al
        r=p.add_run(t); cjk(r,s,b,c); return p
    def h1(n,t):
        p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(10); p.paragraph_format.space_after=Pt(5)
        r=p.add_run(f"{n}. {t}"); cjk(r,14,True,(0x11,0x33,0x55))
        pr=p._p.get_or_add_pPr(); pb=OxmlElement("w:pBdr"); bt=OxmlElement("w:bottom")
        bt.set(qn("w:val"),"single"); bt.set(qn("w:sz"),"12"); bt.set(qn("w:space"),"2"); bt.set(qn("w:color"),"2B6CB0"); pb.append(bt); pr.append(pb)
    def table(heads,rows,ctr=set(),fs=8.5):
        t=doc.add_table(rows=1,cols=len(heads)); t.style="Table Grid"; t.alignment=WD_TABLE_ALIGNMENT.CENTER
        hc=t.rows[0].cells
        for i,h in enumerate(heads):
            hc[i].text=""; rr=hc[i].paragraphs[0].add_run(h); cjk(rr,fs,True,(0xff,0xff,0xff)); hc[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
            sh=OxmlElement("w:shd"); sh.set(qn("w:fill"),"1F2937"); hc[i]._tc.get_or_add_tcPr().append(sh)
        for row in rows:
            cells=t.add_row().cells
            for i,v in enumerate(row):
                cells[i].text=""; rr=cells[i].paragraphs[0].add_run(str(v)); cjk(rr,fs)
                cells[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER if i in ctr else WD_ALIGN_PARAGRAPH.LEFT
        return t
    def img(path,w=168,cap=None):
        doc.add_picture(path,width=Mm(w)); doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
        if cap: para(cap,8.5,False,(0x66,0x66,0x66),6,WD_ALIGN_PARAGRAPH.CENTER)

    para(T("호퍼 각파이프 종합 외주 발주서","料斗方管综合外协订购书"),20,True,(0x11,0x33,0x55),2)
    para(T("料斗方管综合外协订购书" if lang=="kr" else "호퍼 각파이프 종합 외주 발주서",
           "호퍼 각파이프 종합 외주 발주서" if lang=="kr" else "料斗方管综合外协订购书"),12,False,(0x55,0x55,0x55),8)
    table([T("항목","项目"),T("내용","内容")],
      [[T("문서번호","文件号"),DOCNO],[T("개정","版本"),REV],[T("일자","日期"),DATE],
       [T("적용","适用"),T("호퍼 구성 금속 각파이프 전량 (대차프레임+본체보강+결합부보강)","料斗构成金属方管全量(台车框架+本体加强+接合加强)")],
       [T("총 연장","总延长"),f"{GRAND} m"],[T("정척","定尺"),T("SHS 6m 기준 / 각봉 1m","SHS 6m / 方钢 1m")],
       [T("발주처","订购方"),T("호퍼 제작업체 (철판 사양서 LBH-FAB-001과 일괄 의뢰) — 각관 사입·절단·용접·도장 턴키",
                             "料斗制作商(与钢板规格书LBH-FAB-001一并委托)— 方管自购·下料·焊接·涂装 交钥匙")],
       [T("자재 공급","材料供应"),T("각파이프 원자재는 제작업체 사입(발주자 지급 아님). 본 절단표는 소요·검증용 명세",
                                 "方管原材由制作商自购(非甲供)。本下料表为用量·核对清单")]],
      ctr={0})

    h1(1,T("자재 규격·재질·마감","材料规格·材质·表面"))
    table([T("구분","分类"),T("사양","规格")],
      [[T("각파이프(구조)","方管(结构)"),"KS D3568 STK400 / □60×60×2.3t, □50×50×2.3t, □30×60×2.3t"],
       [T("각봉(중실)","方钢(实心)"),"KS D3752 SM45C 상당 / ■50×50 SOLID"],
       [T("스테인리스 각관","不锈钢方管"),T("SUS201 □60×60×2.3t (호퍼 본체측, 철판과 동재)","SUS201 □60×60×2.3t (料斗本体侧,与钢板同材)")],
       [T("STK400 마감","STK400 表面"),T("쇼트 Sa2.5 + 분체도장 RAL7016 80㎛","喷砂Sa2.5+粉末涂装RAL7016 80㎛")],
       [T("SUS201 마감","SUS201 表面"),T("무처리(부동태) / 절단부 디버링","不处理(钝化)/切口去毛刺")],
       [T("절단 공차","下料公差"),"±1.0 mm (KS B ISO 2768-c)"],
       [T("직각도","垂直度"),T("단면 절단 ⟂ ±0.5°","端面切割⟂±0.5°")]], ctr={0})

    h1(2,T("종합 조달 요약 (정척 발주)","综合采购汇总 (定尺订购)"))
    para(T("총소요 = 순 연장, 발주본수 = (총소요×1.10 절단손실)÷정척 올림.",
           "需求=净延长,根数=(需求×1.10下料损耗)÷定尺 向上取整。"),9)
    table([T("단면","截面"),T("재질","材质"),T("총소요(m)","需求(m)"),T("정척(m)","定尺(m)"),T("소요본수","根数"),T("발주총량(m)","订购(m)")],
      [[sec,mat,f"{tot:.2f}",f"{stock:.0f}",bars,f"{order:.1f}"] for sec,mat,tot,stock,bars,order in PROC]
      +[[T("합계 合计","合计"),"",f"{GRAND:.2f}","","",""]], ctr={0,1,2,3,4,5}, fs=9.5)

    doc.add_page_break()
    h1(3,T("절단표 (전 부재)","下料表 (全部件)"))
    rows=[]
    for i,p in enumerate(PIPES,1):
        rows.append([i,p[0],T(p[7],p[8]),T(p[1],p[2]),p[3],p[4],p[5],p[6],T(p[9],p[10])])
    rows.append([T("계","合计"),"","","","","",f"{GRAND}m","",""])
    table([T("No","No"),T("품번","品番"),T("부위","部位"),T("품명","品名"),T("단면","截面"),T("재질","材质"),T("길이","长度"),T("수량","数量"),T("단부·비고","端部·备注")],
          rows, ctr={0,1,4,5,6,7}, fs=8)

    h1(4,T("절단·단부 가공 지침","下料·端部加工要求"))
    para(T("· 전 부재 직각 절단(⟂), 마이터 표기부(림 LP-11~13)는 코너 45° 접합용.\n"
           "· LP-09(30×60)는 절곡판에 angX-30° 경사 부착 — 부착면 기준 직각 절단, 경사는 용접조립에서 형성.\n"
           "· 절단 후 버 제거(디버링), STK400은 도장 전 쇼트블라스트.\n"
           "· 60각 부재 다수 동일 치수 → 정척 6m에서 네스팅 절단으로 손실 최소화(요약표 본수 반영).",
           "· 全部件垂直切割,标注斜接的上缘(LP-11~13)用于角部45°拼接。\n"
           "· LP-09(30×60)以angX-30°斜装于折弯板 — 按贴合面垂直切割,斜度在焊接装配中形成。\n"
           "· 切割后去毛刺,STK400涂装前喷砂。\n"
           "· 60方多件同尺寸 → 6m定尺套裁,损耗最小(汇总表根数已含)。"),9)

    h1(5,T("참조 도면 (프레임 배치)","参考图 (框架布置)"))
    img(f"{DWG}/frame_plan.png",168,T("대차 프레임 평면 — 각파이프 배치·다리·캐스터 위치","台车框架平面—方管布置·腿·脚轮位置"))
    img(f"{DWG}/frame_elev.png",158,T("프레임 입면 — 각파이프 높이","框架立面—方管高度"))

    h1(6,T("표면처리·포장·납품","表面处理·包装·交付"))
    para(T("· 본 각파이프는 호퍼 제작업체가 사입·절단·용접·도장까지 일괄(턴키) 수행 — 철판 사양서 LBH-FAB-001과 동일 업체.\n"
           "· STK400: 절단·용접 후 쇼트 Sa2.5 → 분체도장 RAL7016 80㎛ (제작업체 도장).\n"
           "· SUS201: 무도장(부동태), 유막 방지 포장. 호퍼 본체(철판) 용접에 사용.\n"
           "· 본 절단표·조달요약은 발주자 검증 및 제작업체 자재 산출용 명세이며, 최종 자재는 제작업체 책임 조달.",
           "· 本方管由料斗制作商自购·下料·焊接·涂装一并(交钥匙)完成 — 与钢板规格书LBH-FAB-001同一制作商。\n"
           "· STK400: 切割焊接后喷砂Sa2.5→粉末涂装RAL7016 80㎛(制作商涂装)。\n"
           "· SUS201: 不涂装(钝化),防油膜包装。用于料斗本体(钢板)焊接。\n"
           "· 本下料表·采购汇总为甲方核对及制作商用量核算清单,最终材料由制作商负责采购。"),9)

    path=f"{OUTD}/{DOCNO}_{'KR' if lang=='kr' else 'CN'}.docx"; doc.save(path); print("DOCX:",path)
build("kr"); build("cn")
print("GRAND total pipe length (m):",GRAND)
for row in PROC: print(row)
