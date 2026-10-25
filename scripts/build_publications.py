"""Build printable research PDFs from the committed synthetic experiment summary.
Not the original editorial report; a reproducible GitHub publication edition.
"""
from pathlib import Path
import csv
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs"
OUT.mkdir(exist_ok=True)
summary={}
with (ROOT/"results"/"summary_600.csv").open(encoding="utf8",newline="") as f:
    for r in csv.DictReader(f):
        summary[r["scenario"],r["policy"]]=float(r["completed_mean"])
navy=colors.HexColor("#102F3E")
teal=colors.HexColor("#0A8F80")
dark=colors.HexColor("#0A2130")
pale=colors.HexColor("#EEF7F5")
slate=colors.HexColor("#526D79")
light=colors.HexColor("#DDE9EB")
orange=colors.HexColor("#C39965")
font_path=Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
font_bold=Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
if not font_path.exists():
    alternatives=[Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    font_path=next((x for x in alternatives if x.exists()),font_path)
    font_bold=font_path
pdfmetrics.registerFont(TTFont("FAB",str(font_path)))
pdfmetrics.registerFont(TTFont("FABBold",str(font_bold)))

def para(c,text,x,top,width,size=13,leading=1.56,color=navy,bold=False):
    st=ParagraphStyle("p",fontName="FABBold" if bold else "FAB",fontSize=size,
                      leading=size*leading,textColor=color,wordWrap="CJK")
    p=Paragraph(text,st)
    _,height=p.wrap(width,1200)
    p.drawOn(c,x,top-height)
    return top-height

def rounded(c,x,y,w,h,fill,r=12):
    c.setFillColor(fill);c.roundRect(x,y,w,h,r,stroke=0,fill=1)

def title(c,s,x,y,size=23,color=navy):
    c.setFillColor(color);c.setFont("FABBold",size);c.drawString(x,y,s)

def chart(c,x,y,w,h,condition):
    pol=[
      ("Full-route","full_atomic_dynamic",colors.HexColor("#8198A5")),
      ("Partial shortest","partial_shortest",orange),
      ("Partial dynamic","partial_dynamic",teal),
      ("Untrained Q","partial_rl_untrained",colors.HexColor("#719CB0")),
      ("Trained Q","partial_rl_trained",colors.HexColor("#124A63"))
    ]
    mx=max(summary[condition,name] for _,name,_ in pol)
    for i,(name,key,col) in enumerate(pol):
        yy=y+h-38-i*(h-45)/5
        c.setFillColor(navy);c.setFont("FAB",11);c.drawString(x,yy,name)
        c.setFillColor(colors.HexColor("#E5EEEF"));c.roundRect(x+143,yy-4,w-205,14,4,fill=1,stroke=0)
        c.setFillColor(col);c.roundRect(x+143,yy-4,(w-205)*summary[condition,key]/max(44,mx),14,4,fill=1,stroke=0)
        c.setFont("FABBold",12);c.setFillColor(navy)
        c.drawRightString(x+w-5,yy,f"{summary[condition,key]:.2f}")

# Landscape A2 conference poster
W,H=594*mm,420*mm
poster=canvas.Canvas(str(OUT/"FABFLOW_Conference_Poster_A2.pdf"),pagesize=(W,H))
poster.setFillColor(colors.HexColor("#F5FAFA"));poster.rect(0,0,W,H,fill=1,stroke=0)
poster.setFillColor(dark);poster.rect(0,H-198,W,198,fill=1,stroke=0)
title(poster,"FAB FLOW  /  SEMICONDUCTOR MATERIAL HANDLING RESEARCH",66,H-56,25,colors.HexColor("#6AD9C0"))
title(poster,"Deadlock-Aware OHT Routing and Partial Rail Reservation",66,H-106,35,colors.white)
para(poster,"반도체 FAB의 OHT 경로·교차로 예약·강화학습을 통합한 합성 시뮬레이션 연구",68,H-124,W-135,22,color=colors.HexColor("#C9DFE2"))
title(poster,"Learners × YPICS Joint Logistics Seminar  |  Presentation Preparation · 31 Oct 2026",68,H-181,15,colors.HexColor("#AAC8D2"))
margin=62;gap=20;col=(W-2*margin-2*gap)/3
top=H-228
for i,heading in enumerate(["01  RESEARCH QUESTION","02  SIMULATION MODEL","03  STATISTICAL EVIDENCE"]):
    x=margin+i*(col+gap)
    rounded(poster,x,110,col,top-110,colors.white,14)
    rounded(poster,x,top-56,col,56,pale,10)
    title(poster,heading,x+22,top-38,18,teal)
x=margin
t=top-83
t=para(poster,"<b>최단경로와 전체 처리량은 다르다.</b> 차량 한 대가 가장 빠른 길을 찾더라도, 여러 차량이 같은 교차로를 공유하면 시스템 전체의 물류는 지연될 수 있다.",x+22,t,col-44,17)
t-=30
t=para(poster,"Full-route reservation",x+22,t,col-44,16,bold=True)
t=para(poster,"출발 시 전체 경로의 레일 자원을 잠가 교착을 보수적으로 회피하지만, 미사용 레일까지 선점한다.",x+22,t-12,col-44,14)
t-=35
t=para(poster,"Partial next-segment reservation",x+22,t,col-44,16,bold=True)
t=para(poster,"다음 진입 구간만 검사·예약하고 통과한 구간은 해제해 레일 활용률을 높인다.",x+22,t-12,col-44,14)
t-=35
t=para(poster,"Wait-for Graph",x+22,t,col-44,16,bold=True)
t=para(poster,"차량 A가 B를 기다리는 관계를 추적해 순환대기 위험이 커지는 진입을 사전에 거부한다.",x+22,t-12,col-44,14)
t-=35
para(poster,"<b>Question</b> — Does learning itself improve throughput once the same safety constraints and routing structure are held constant?",x+22,t,col-44,14)
x=margin+col+gap
t=top-83
t=para(poster,"<b>Virtual FAB topology</b> · 48 nodes, 82 directed rail links, 9 OHT vehicles.",x+22,t,col-44,16)
t=para(poster,"3 scenarios × 5 policies × 40 paired seeds = 600 evaluation runs; 360 safety/fleet sensitivity runs.",x+22,t-22,col-44,15)
t-=30
for k,v in [("Arrival model","Synthetic Poisson transport requests"),("Normal demand","68 requests / hour"),("Demand surge","1.5× normal arrivals"),("Observation","1,500 s (25 minutes)"),("Learning","Tabular Q-learning"),("Statistics","Bootstrap CIs / Holm-corrected sign test")]:
    title(poster,k,x+22,t,13,teal)
    t=para(poster,v,x+190,t+13,col-217,13)
    t-=29
x=margin+2*(col+gap)
t=top-83
title(poster,"DEMAND SURGE  /  COMPLETED JOBS",x+20,t,16,navy)
chart(poster,x+20,t-300,col-40,270,"surge")
t-=338
t=para(poster,"<b>Partial dynamic vs full-route:</b> +13.425 completed jobs (95% paired CI [+11.650, +15.125]).",x+22,t,col-44,14)
t=para(poster,"<b>Trained Q vs untrained Q:</b> +0.575 jobs (95% CI [+0.200, +1.000]); Holm-adjusted p = 0.0369.",x+22,t-14,col-44,14)
t=para(poster,"The learned effect was not consistently significant under normal and rail-closure scenarios.",x+22,t-14,col-44,14)
poster.setStrokeColor(light);poster.line(margin,80,W-margin,80)
para(poster,"<b>Main finding:</b> Resource reservation strategy mattered more than additional Q-learning in this synthetic test. Not a real factory digital twin or industrial safety-certified controller.",margin,72,W-2*margin,14)
poster.showPage();poster.save()

# Print-friendly research brief
styles={
"title":ParagraphStyle("title",fontName="FABBold",fontSize=20,leading=31,textColor=navy,spaceAfter=13),
"h":ParagraphStyle("h",fontName="FABBold",fontSize=13,leading=22,textColor=navy,spaceBefore=15,spaceAfter=8),
"p":ParagraphStyle("p",fontName="FAB",fontSize=9.8,leading=17,textColor=navy,spaceAfter=10,wordWrap="CJK"),
"note":ParagraphStyle("note",fontName="FAB",fontSize=8.5,leading=15,textColor=slate,spaceAfter=10,wordWrap="CJK")
}
def P(s,k="p"):return Paragraph(s,styles[k])
story=[
 P("FAB FLOW | Semiconductor OHT Routing Optimization","title"),
 P("Synthetic FAB Experiment · Conference Portfolio / Learners × YPICS Seminar Preparation","note"),
 P("Executive Summary / 연구 요약","h"),
 P("반도체 FAB에서 여러 OHT가 같은 레일과 교차로를 공유하면 최단경로만으로는 전체 운송 효율을 설명하기 어렵다. 48개 노드와 82개 단방향 링크를 가진 가상 FAB 모델을 구성하고, 전체 경로 예약과 다음 구간만 예약하는 제어기를 비교하였다."),
 P("Main study: 600 runs (3 scenarios × 5 policies × 40 matched seeds). Safety sensitivity: 360 additional runs. Synthetic requests and synthetic topology; no factory MES or real sensor linkage."),
 P("Problem & Model","h"),
 P("A full-route lock preclaims every node and edge along a route. A partial reservation grants only the next section when destination occupancy and prospective wait-cycle constraints permit. Wait-for graph edges describe a blocked vehicle waiting for another; a cycle flag is a warning rather than physical deadlock certification."),
 P("Reinforcement Learning / 강화학습","h"),
 P("Q-learning records action values for reduced representations of location, destination, demand condition and activity. Q(s,a) is updated with a learning rate of 0.22 and a discount factor of 0.87. The trained policy is compared with an otherwise similar untrained policy to isolate learning effects. A safe-action shield limits path detours and disallows reserved intersections."),
 P("Evaluation & Statistics","h"),
 P("All policies in a scenario receive the same generated job requests for 40 paired evaluation seeds. Paired mean differences, 95% bootstrap confidence intervals and Holm-adjusted exact sign tests support the comparisons. Completed-only transport lead times may be biased because unfinished jobs are excluded."),
 P("Key means / 평균 완료 운송 (25분)","h")
]
table=[["Scenario","Full-route","Partial dynamic","Trained Q"]]
for scene in ("normal","surge","closure"):
 table.append([scene,*[f"{summary[scene,key]:.3f}" for key in ("full_atomic_dynamic","partial_dynamic","partial_rl_trained")]])
T=Table(table,colWidths=[95,96,105,96]);T.setStyle(TableStyle([
 ("BACKGROUND",(0,0),(-1,0),pale),("GRID",(0,0),(-1,-1),.6,light),
 ("FONTNAME",(0,0),(-1,-1),"FAB"),("FONTSIZE",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
story.extend([T,Spacer(1,14),P("Interpretation and limitations","h"),
P("Partial dynamic routing improved completion counts over conservative full-route reservation across all three tested conditions: +5.525 (normal), +13.425 (surge), and +5.875 (rail closure) mean jobs. Learning contributed +0.575 mean jobs only in surge (95% CI [+0.200,+1.000], Holm-adjusted p=0.0369); other conditions did not establish a significant learning effect."),
P("모형에 정의한 노드 중복 점유 위반 0건과 보호장치의 순환대기 신호 감소는 실제 장비에 대한 충돌 방지 인증이 아니다. FAB 동역학, 레일 블록, 장비 지연, 실시간 센서 동기화, 생산 스케줄링, 다중 네트워크 일반화는 아직 추가 검증이 필요하다."),
P("Full source, readme, paired inference CSV and interactive schematic: github.com/doyunsin883-debug/semiconductor-oht-routing-optimization / fabflow-oht-phase3-deadlock.vercel.app","note")])
report=str(OUT/"FABFLOW_GitHub_Research_Brief_KO_EN.pdf")
doc=SimpleDocTemplate(report,pagesize=(210*mm,297*mm),rightMargin=22*mm,leftMargin=22*mm,topMargin=20*mm,bottomMargin=20*mm)
doc.build(story)
print("Built",OUT/"FABFLOW_Conference_Poster_A2.pdf",report)
