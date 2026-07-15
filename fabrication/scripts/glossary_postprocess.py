# -*- coding: utf-8 -*-
"""모든 docx에 '용어 설명' 섹션을 원어(한국어:설명) / 原文(中文:说明) 형식으로 일괄 추가."""
import glob, os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUTD="/tmp/claude-0/-home-user-maestro/89feb1d7-5414-58cf-b499-d60f30aed29c/scratchpad/out"

# term : (ko_name, ko_desc, cn_name, cn_desc)
G = {
 "SUS201":("에스유에스201","저니켈 오스테나이트계 스테인리스강, 304 대비 저가","SUS201","低镍奥氏体不锈钢,较304廉价"),
 "SUS304":("에스유에스304","표준 오스테나이트계 스테인리스강","SUS304","标准奥氏体不锈钢"),
 "STK400":("에스티케이400","KS 일반구조용 탄소강 강관(각파이프)","STK400","KS一般结构用碳钢管(方管)"),
 "SM45C":("에스엠45씨","기계구조용 중탄소강(각봉)","SM45C","机械结构用中碳钢(方钢)"),
 "SPHC":("에스피에이치씨","열간압연 연강판","SPHC","热轧软钢板"),
 "PEEK":("피크","폴리에터에터케톤, 고성능 엔지니어링 플라스틱","PEEK","聚醚醚酮,高性能工程塑料"),
 "PETG":("펫지","글리콜변성 폴리에스터, 3D프린팅용","PETG","乙二醇改性聚酯,3D打印用"),
 "PLA":("피엘에이","폴리락타이드, 3D프린팅용","PLA","聚乳酸,3D打印用"),
 "PP":("피피","폴리프로필렌(버킷 재질)","PP","聚丙烯(铲斗材质)"),
 "NBR":("엔비알","니트릴 고무(가이드볼)","NBR","丁腈橡胶(导向球)"),
 "SHCS":("에스에이치씨에스","육각렌치볼트, 소켓헤드캡스크류","SHCS","内六角圆柱头螺栓"),
 "DIN912":("딘912","육각렌치볼트(SHCS) 규격","DIN912","内六角螺栓标准"),
 "KS D3568":("케이에스 D3568","일반구조용 각형강관 규격","KS D3568","一般结构用方形钢管标准"),
 "ISO 2768":("아이에스오2768","도면 미지정 부위 일반공차 규격","ISO 2768","未注公差通用标准"),
 "RAL7016":("랄7016","무광 앤트러사이트 그레이 도장 색상표준","RAL7016","哑光炭灰色涂装色号"),
 "A2-70":("에이투-70","오스테나이트 스테인리스 볼트 강도등급(≈STS304)","A2-70","奥氏体不锈钢螺栓强度等级(≈STS304)"),
 "TIG":("티그","텅스텐 불활성가스 아크용접","TIG","钨极惰性气体保护焊"),
 "GMAW":("지엠에이더블유","가스메탈 아크(CO2) 용접","GMAW","熔化极气体(CO2)保护焊"),
 "Sa2.5":("에스에이2.5","쇼트블라스트 표면청정도 등급","Sa2.5","喷砂表面清洁度等级"),
 "분체도장":("분체도장","분말도료 정전 도장(파우더코팅)","粉末涂装","静电粉末喷涂"),
 "어닐링":("어닐링","응력완화·강도향상 열처리(annealing)","退火","消除应力·增强热处理"),
 "마이터":("마이터","45° 경사 절단 접합(miter)","斜接","45°斜切拼接"),
 "디버링":("디버링","절단부 버(거스러미) 제거(deburring)","去毛刺","切口毛刺去除"),
 "SHS":("에스에이치에스","정사각 중공 형강, 각파이프(Square Hollow Section)","SHS","方形空心型钢,方管"),
 "BLDC":("비엘디씨","브러시리스 직류모터","BLDC","无刷直流电机"),
 "인버터":("인버터","모터 구동 드라이버(inverter)","变频器","电机驱动器"),
 "엔코더":("엔코더","회전각 검출 센서(encoder)","编码器","旋转角检测传感器"),
 "NEMA23":("네마23","표준 스테퍼모터 마운트 규격","NEMA23","标准步进电机安装规格"),
 "캐스터":("캐스터","이동식 바퀴(caster)","脚轮","移动轮"),
 "텐셔너":("텐셔너","벨트/체인 장력조절 장치(tensioner)","张紧器","皮带/链条张力调节装置"),
 "RFQ":("알에프큐","견적요청서(Request For Quotation)","RFQ","询价书"),
 "FOB":("에프오비","본선인도조건(무역)","FOB","船上交货"),
 "CIF":("씨아이에프","운임·보험료포함 인도조건","CIF","成本加保险费加运费"),
 "인코텀즈":("인코텀즈","국제무역 거래조건 규칙(Incoterms)","国际贸易术语","国际贸易术语规则"),
 "전개도":("전개도","판금을 평면으로 펼친 절단 도면","展开图","钣金平面展开下料图"),
 "throat":("스로트","호퍼 하단 배출 개구부","throat","料斗下部排出口"),
 "BOM":("비오엠","자재명세서(Bill of Materials)","BOM","物料清单"),
 "bbox":("바운딩박스","부품 외형 최대치수 상자","bbox","外形最大尺寸盒"),
 "STL":("에스티엘","3D프린팅 표준 삼각메쉬 파일","STL","3D打印三角网格文件"),
}
# 순서 고정
ORDER=list(G.keys())

def doc_text(doc):
    parts=[p.text for p in doc.paragraphs]
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells: parts.append(c.text)
    return "\n".join(parts)

def add_glossary(path):
    lang = "cn" if path.endswith("_CN.docx") else "kr"
    CJK = "Microsoft YaHei" if lang=="cn" else "Malgun Gothic"
    doc=Document(path)
    txt=doc_text(doc)
    if ("용어 설명" in txt) or ("术语说明" in txt): return "skip(exists)"
    used=[t for t in ORDER if t in txt]
    if not used: return "none"
    def cjk(run,size=10,bold=False,color=None):
        run.font.name="Calibri"; run.font.size=Pt(size); run.font.bold=bold
        if color: run.font.color.rgb=RGBColor(*color)
        rpr=run._element.get_or_add_rPr(); rf=rpr.find(qn("w:rFonts"))
        if rf is None: rf=OxmlElement("w:rFonts"); rpr.append(rf)
        rf.set(qn("w:eastAsia"),CJK)
    doc.add_page_break()
    # heading
    hp=doc.add_paragraph(); hp.paragraph_format.space_after=Pt(5)
    cjk(hp.add_run("■ "+("术语说明" if lang=="cn" else "용어 설명")+"  ("+("原文(中文: 说明)" if lang=="cn" else "원어(한국어: 설명)")+")"),13.5,True,(0x11,0x33,0x55))
    pr=hp._p.get_or_add_pPr(); pb=OxmlElement("w:pBdr"); bt=OxmlElement("w:bottom")
    for k,v in (("w:val","single"),("w:sz","12"),("w:space","2"),("w:color","2B6CB0")): bt.set(qn(k),v)
    pb.append(bt); pr.append(pb)
    # entries: 원어(한국어: 설명)
    for t in used:
        ko_n,ko_d,cn_n,cn_d=G[t]
        p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(2)
        cjk(p.add_run(t),9.5,True,(0x1a,0x1a,0x1a))
        if lang=="cn": cjk(p.add_run(f"（{cn_n}: {cn_d}）"),9.5)
        else:          cjk(p.add_run(f"({ko_n}: {ko_d})"),9.5)
    doc.save(path)
    return f"added {len(used)}"

res={}
for f in sorted(glob.glob(f"{OUTD}/*.docx")):
    res[os.path.basename(f)]=add_glossary(f)
for k,v in res.items(): print(f"{k:28s} {v}")
