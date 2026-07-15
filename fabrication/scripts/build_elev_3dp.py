# -*- coding: utf-8 -*-
"""엘레베이터 금속장치 문서 + 3D프린트 부품(재료별) 문서 — 한/중."""
import os, json
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

SP="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad"
OUTD=f"{SP}/out"; DATE="2026-07-14"
MANIFEST=json.load(open(f"{SP}/stl/stl_manifest.json"))

class Doc:
    def __init__(self, lang):
        self.lang=lang; self.CJK="Malgun Gothic" if lang=="kr" else "Microsoft YaHei"
        d=Document(); self.d=d; s=d.sections[0]; s.page_width=Mm(210); s.page_height=Mm(297)
        for m in ("top_margin","bottom_margin","left_margin","right_margin"): setattr(s,m,Mm(16))
        nf=d.styles["Normal"].font; nf.name="Calibri"; nf.size=Pt(10)
        d.styles["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"),self.CJK)
    def T(self,kr,cn): return kr if self.lang=="kr" else cn
    def _c(self,run,size=10,bold=False,color=None):
        run.font.name="Calibri"; run.font.size=Pt(size); run.font.bold=bold
        if color: run.font.color.rgb=RGBColor(*color)
        rpr=run._element.get_or_add_rPr(); rf=rpr.find(qn("w:rFonts"))
        if rf is None: rf=OxmlElement("w:rFonts"); rpr.append(rf)
        rf.set(qn("w:eastAsia"),self.CJK)
    def para(self,t,s=10,b=False,c=None,after=4,al=None):
        p=self.d.add_paragraph(); p.paragraph_format.space_after=Pt(after)
        if al: p.alignment=al
        self._c(p.add_run(t),s,b,c); return p
    def h1(self,n,t):
        p=self.d.add_paragraph(); p.paragraph_format.space_before=Pt(9); p.paragraph_format.space_after=Pt(4)
        self._c(p.add_run(f"{n}. {t}"),13.5,True,(0x11,0x33,0x55))
        pr=p._p.get_or_add_pPr(); pb=OxmlElement("w:pBdr"); bt=OxmlElement("w:bottom")
        for k,v in (("w:val","single"),("w:sz","12"),("w:space","2"),("w:color","2B6CB0")): bt.set(qn(k),v)
        pb.append(bt); pr.append(pb)
    def h2(self,t): self.para(t,11,True,(0x2b,0x6c,0xb0),3)
    def title(self,t,sub=None):
        self.para(t,20,True,(0x11,0x33,0x55),2)
        if sub: self.para(sub,12,False,(0x55,0x55,0x55),8)
    def table(self,heads,rows,ctr=set(),fs=8.5):
        t=self.d.add_table(rows=1,cols=len(heads)); t.style="Table Grid"; t.alignment=WD_TABLE_ALIGNMENT.CENTER
        hc=t.rows[0].cells
        for i,h in enumerate(heads):
            hc[i].text=""; self._c(hc[i].paragraphs[0].add_run(h),fs,True,(0xff,0xff,0xff)); hc[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
            sh=OxmlElement("w:shd"); sh.set(qn("w:fill"),"1F2937"); hc[i]._tc.get_or_add_tcPr().append(sh)
        for row in rows:
            cells=t.add_row().cells
            for i,v in enumerate(row):
                cells[i].text=""; self._c(cells[i].paragraphs[0].add_run(str(v)),fs)
                cells[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER if i in ctr else WD_ALIGN_PARAGRAPH.LEFT
        return t
    def save(self,name): p=f"{OUTD}/{name}.docx"; self.d.save(p); print("DOCX:",p)

def xs():
    thin=Side(style="thin",color="9AA4B2")
    return dict(bd=Border(left=thin,right=thin,top=thin,bottom=thin),hf=PatternFill("solid",fgColor="1F2937"),
                tf=PatternFill("solid",fgColor="DFF0DF"),ctr=Alignment(horizontal="center",vertical="center",wrap_text=True),
                lft=Alignment(horizontal="left",vertical="center",wrap_text=True))

# ============ 엘레베이터 금속장치 ============
# (partno, kr, cn, spec, qty, proc_kr, proc_cn)
ELEV=[
 ("EV-01","엘레베이터 케이스/프레임","提升机壳体/框架","SUS304 판금, 280×1400×160, 침지형","1","외주가공-판금/용접","外协-钣金/焊接"),
 ("EV-02","버킷","料斗铲斗","PP 폴리프로필렌 60×55×60, 피치 71.78","46","구매/사출(비금속)","采购/注塑(非金属)"),
 ("EV-03","구동 풀리/스프로킷 (상)","驱动轮/链轮(上)","Ø40×W100 SUS, 베어링 내장","1","구매/외주","采购/外协"),
 ("EV-04","종동 풀리/스프로킷 (하)","从动轮/链轮(下)","Ø40×W100 SUS, 베어링 내장","1","구매/외주","采购/外协"),
 ("EV-05","구동 벨트/체인","驱动带/链条","무한궤도 루프 (구동부 도면 확정)","1 set","구매","采购"),
 ("EV-06","구동 모터 BLDC","驱动电机BLDC","80BLS130-310, 750W, 유성 50:1, 107N·m","1","구매","采购"),
 ("EV-07","드라이버/인버터","驱动器/变频器","BLD-AC750S, 단상 220VAC, 166×102×67","1","구매","采购"),
 ("EV-08","체인/벨트 텐셔너","张紧器","텐셔너 + 압축스프링 (장력 ≈142N)","1 set","외주/구매","外协/采购"),
 ("EV-09","구동/종동 샤프트","驱动/从动轴","SUS304/S45C, Ø 축 (풀리 정합)","2","외주가공","外协加工"),
 ("EV-10","샤프트 베어링","轴承","피로우블록/심구 (UCP·6004ZZ 등급)","4","구매-표준품","采购-标准件"),
 ("EV-11","모터 마운트·브라켓(금속)","电机安装·支架(金属)","STK400 브라켓 + M10 SHCS","1 set","외주가공","外协加工"),
]
def build_elev(lang):
    D=Doc(lang); T=D.T
    D.title(T("엘레베이터 금속장치 명세서","提升机金属装置清单"),
            T("버킷 엘레베이터 · 3D프린트 제외 · 프레임/구동/베어링/모터·인버터 (LBH-ELEV-001)",
              "斗式提升机·不含3D打印·框架/驱动/轴承/电机·变频器 (LBH-ELEV-001)"))
    D.table([T("항목","项目"),T("내용","内容")],
      [[T("문서번호","文件号"),"LBH-ELEV-001"],[T("일자","日期"),DATE],
       [T("범위","范围"),T("엘레베이터에 부착된 3D프린트 제외 전 부품(금속·구매품)","提升机上除3D打印外全部件(金属·采购)")],
       [T("경계","边界"),T("하부/상부 보강·30×60 결합관 = 호퍼 패키지(LBH-PIPE-001). 모터 PEEK 클램프 = 3D프린트(LBH-3DP-001)",
                          "下/上加强·30×60接合管=料斗包(LBH-PIPE-001)。电机PEEK夹=3D打印(LBH-3DP-001)")],
       [T("발주","订购"),T("호퍼와 별도 발주(보안). 구동부 구매품+케이스 외주 혼합","与料斗分开订购(保密)。驱动采购件+壳体外协")]],ctr={0})
    D.h1(1,T("부품 명세","部件清单"))
    D.table([T("품번","品番"),T("품명","品名"),T("사양","规格"),T("수량","数量"),T("제작구분","加工")],
      [[c,T(kr,cn),sp,q,T(pk,pc)] for c,kr,cn,sp,q,pk,pc in ELEV],ctr={0,3},fs=8.5)
    D.h1(2,T("확인 필요 (구동부)","需确认(驱动)"))
    D.para(T("· 구동 방식(벨트/체인)·텐셔너 사양: BOM=벨트+풀리, 설계계산서=체인 장력 병기 → 구동부 상세도면 기준 확정.\n"
             "· 모터 BLDC 750W(310V) vs 드라이버 BLD-AC750S(220VAC 입력) 전원계 정합 확인.\n"
             "· 샤프트 베어링 등급(피로우블록 UCP/삽입형)은 축경 확정 후 선정.",
             "· 驱动方式(带/链)·张紧器: BOM=带+轮, 计算书=链张力 → 按驱动详图确定。\n"
             "· 电机BLDC 750W(310V)与驱动器BLD-AC750S(220VAC输入)电源匹配确认。\n"
             "· 轴承等级(UCP/嵌入式)按轴径确定后选型。"),9.5)
    D.h1(3,T("주기","备注"))
    D.para(T("본 명세는 엘레베이터 구성의 3D프린트 제외 부품 일체이며, 호퍼와 분리 발주 대상(보안). 3D프린트 부품은 LBH-3DP-001 참조.",
             "本清单为提升机除3D打印外全部件,与料斗分开订购(保密)。3D打印件见LBH-3DP-001。"),9)
    D.save(f"LBH-ELEV-001_{'KR' if lang=='kr' else 'CN'}")

def xlsx_elev():
    S=xs(); wb=openpyxl.Workbook(); ws=wb.active; ws.title="ELEV BOM"
    ws.merge_cells("A1:G1"); ws["A1"]="엘레베이터 금속장치 BOM / 提升机金属装置BOM (LBH-ELEV-001)"; ws["A1"].font=Font(bold=True,size=12); ws["A1"].alignment=S["ctr"]
    for c,h in enumerate(["No","품번","품명(한)","品名(中)","사양 规格","수량","제작구분 加工"],1):
        cell=ws.cell(3,c,h); cell.font=Font(bold=True,color="FFFFFF"); cell.fill=S["hf"]; cell.alignment=S["ctr"]; cell.border=S["bd"]
    r=4
    for i,(c_,kr,cn,sp,q,pk,pc) in enumerate(ELEV,1):
        for cc,v in enumerate([i,c_,kr,cn,sp,q,f"{pk}\n{pc}"],1):
            cell=ws.cell(r,cc,v); cell.border=S["bd"]; cell.font=Font(size=9); cell.alignment=S["ctr"] if cc in(1,2,6) else S["lft"]
        r+=1
    for i,w in enumerate([4,10,20,16,34,7,20],1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width=w
    ws.row_dimensions[3].height=24
    p=f"{OUTD}/LBH-ELEV-001_BOM.xlsx"; wb.save(p); print("XLSX:",p)

# ============ 3D 프린트 부품 (재료별) ============
MAT_SPEC={
 "PEEK":[("재료 材料","PEEK (CF-PEEK 권장) / 어닐링 후처리 金属级"),("노즐 喷嘴","390~410°C"),("베드/챔버 床/腔","130°C / 60~90°C"),
         ("인필/벽 填充/壁","60~100% / 4벽"),("레이어 层高","0.15~0.20mm"),("후처리 后处理","어닐링(150°C 서냉) 退火, 압입/치면 마감")],
 "PETG":[("재료 材料","PETG"),("노즐 喷嘴","235~245°C"),("베드 床","80°C"),("인필/벽","30~40% / 3벽"),("레이어 层高","0.20mm"),("후처리","서포트 제거")],
 "RIG":[("재료 材料","PETG 또는 PLA+ (카메라 거치대)"),("노즐 喷嘴","240 / 210°C"),("베드 床","80 / 60°C"),("인필/벽","25~35% / 3벽"),("레이어 层高","0.24~0.30mm"),("후처리","서포트 제거")],
}
MAT_KR={"PEEK":"PEEK (분배 구동부·마운트·플랜지·엘보·니플·링·노브·모터클램프)","PETG":"PETG (인버터 고정박스)","RIG":"카메라 천장 거치대"}
MAT_CN={"PEEK":"PEEK (分配驱动·安装·法兰·弯头·接头·环·旋钮·电机夹)","PETG":"PETG (变频器固定盒)","RIG":"相机吊装支架"}
def build_3dp(lang):
    D=Doc(lang); T=D.T
    D.title(T("3D 프린트 부품 명세 (재료별) + STL 패키지","3D打印件清单(按材料)+STL包"),
            T("전 시스템 3D프린트 부품 · 재료별 STL 일체 (LBH-3DP-001)","全系统3D打印件·按材料STL整套 (LBH-3DP-001)"))
    tq={};
    for m in MANIFEST: tq[m["mat"]]=tq.get(m["mat"],0)+m["qty"]
    D.table([T("항목","项目"),T("내용","内容")],
      [[T("문서번호","文件号"),"LBH-3DP-001"],[T("일자","日期"),DATE],
       [T("범위","范围"),T("호퍼·엘레·분배·차광 전 시스템 3D프린트 부품","料斗·提升·分配·遮光 全系统3D打印件")],
       [T("STL 패키지","STL包"),f"LBH-3DP-STL.zip — PEEK/ PETG/ RIG/ ("+T("고유","唯一")+f" {len(MANIFEST)}, "+T("총","共")+f" {sum(tq.values())} ea)"],
       [T("좌표","坐标"),T("STL은 시뮬 월드좌표 실측 지오메트리 (mm)","STL为仿真世界坐标实测几何(mm)")]],ctr={0})
    D.h1(1,T("재료별 요약","按材料汇总"))
    D.table([T("재료","材料"),T("구성","构成"),T("고유부품","唯一件"),T("총수량","总数量")],
      [[m,T(MAT_KR[m],MAT_CN[m]),len([x for x in MANIFEST if x["mat"]==m]),tq.get(m,0)] for m in ["PEEK","PETG","RIG"]],ctr={0,2,3})
    for m in ["PEEK","PETG","RIG"]:
        D.h1(f"§{m}",T(f"{m} 프린트 사양 + 부품","{} 打印规格+件".format(m)))
        D.h2(T("프린트 설정","打印设置"))
        D.table([T("항목","项目"),T("값","值")],[[T(a,a),b] for a,b in MAT_SPEC[m]],ctr=set())
        D.h2(T("STL 부품 목록","STL件目录"))
        rows=[[x["file"].split("/")[-1],x["qty"],x["dims"]+" mm",x["ntri"]] for x in MANIFEST if x["mat"]==m]
        D.table([T("STL 파일","STL文件"),T("수량","数量"),T("외형(bbox)","外形"),T("삼각형","三角面")],rows,ctr={1,2,3},fs=7.5)
    D.h1(2,T("적용·주기","应用·备注"))
    D.para(T("· STL은 설계 모델(시뮬)에서 직접 추출한 실측 지오메트리 — 슬라이서에서 배치 후 프린트.\n"
             "· 일부 얇은 셸/개방면 부재는 프린트 전 솔리드화(두께 부여)·메쉬 리페어 필요(설계모델 특성).\n"
             "· PEEK 대형 조립체(PEEK_01)는 논리부품 다수 병합 — 슬라이서에서 분리 배치 권장.\n"
             "· 동일 STL은 수량(qtyN)만큼 복제 프린트. 재료별 폴더(PEEK/PETG/RIG)로 구분.\n"
             "· 엘레·호퍼의 금속·구매부품은 LBH-ELEV-001 / LBH-FAB-001·PIPE-001 참조.",
             "· STL为从设计模型(仿真)直接提取的实测几何 — 切片软件排版后打印。\n"
             "· 部分薄壳/开放面件打印前需实体化(赋厚)·网格修复(设计模型特性)。\n"
             "· PEEK大型组合体(PEEK_01)含多逻辑件合并 — 建议切片时分离排版。\n"
             "· 相同STL按数量(qtyN)复制打印。按材料文件夹(PEEK/PETG/RIG)区分。\n"
             "· 提升机·料斗金属·采购件见LBH-ELEV-001 / LBH-FAB-001·PIPE-001。"),9)
    D.save(f"LBH-3DP-001_{'KR' if lang=='kr' else 'CN'}")

build_elev("kr"); build_elev("cn"); xlsx_elev()
build_3dp("kr"); build_3dp("cn")
print("DONE. 3DP mats:", {m:len([x for x in MANIFEST if x['mat']==m]) for m in ['PEEK','PETG','RIG']})
