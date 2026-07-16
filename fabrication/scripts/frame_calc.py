# Frame square-pipe cut list (64x64 STK400) from code geometry
frameOuterX=732; iz_front=890.05; iz_rear=737.89
baseBeamR=32; fRingR=32; framePipeR=32
baseY=170; frameH=240; frameLegH=baseY+frameH+120  # 530
baseBeamY=baseY+3  # 173
fRingY=frameLegH-framePipeR-4  # 494
sec=64

def P(name,n,length,note=""):
    print(f"{name:24s} x{n}  L={length:8.1f}mm  {note}")

print("=== 베이스 프레임 (하부, Y=173, 64x64) ===")
lenFB = frameOuterX*2+baseBeamR*2   # 1528
lenSide = iz_front+iz_rear+baseBeamR*2  # 1691.94
P("베이스 전면빔",1,lenFB,"Z=-890.05")
P("베이스 후면빔",1,lenFB,"Z=+737.89")
P("베이스 사이드빔",2,lenSide,"X=+-732, centerZ=-76.08")
P("호퍼받침 가로바",1,lenFB,"Y=138, Z=-120.69 (용접)")

print("\n=== 상단 링 (Y=494, 64x64) ===")
lenRingFB = frameOuterX*2+fRingR*2  # 1528
lenRingSide = iz_front+iz_rear+fRingR*2 # 1691.94
P("링 전면빔",1,lenRingFB,"Z=-890.05")
P("링 후면빔",1,lenRingFB,"Z=+737.89")
P("링 사이드빔",2,lenRingSide,"X=+-732")

print("\n=== 수직 다리 (64x64) ===")
legH=(frameLegH-framePipeR*2-4)-(baseY+3+framePipeR) # 257
legs=[(-732,-890.05),(732,-890.05),(-732,737.89),(732,737.89),(-732,0),(732,0),(0,737.89)]
P("수직 다리",len(legs),legH,f"{len(legs)}개소 (전면중앙 제외)")
for x,z in legs: print(f"     leg @ X={x:6.1f} Z={z:8.2f}")

print("\n=== 캐스터 위치 (8개, D120) ===")
casters=[(-732,-890.05),(732,-890.05),(0,-890.05),(-732,737.89),(732,737.89),(-732,0),(732,0),(0,737.89)]
for i,(x,z) in enumerate(casters,1): print(f"  C{i}: X={x:7.1f}  Z={z:8.2f}  (world Z {z-158:8.2f})")

print("\n=== 호퍼 자체 보강 각파이프 (hopperGroup, 64x64) ===")
# corner posts
P("코너 포스트",4,1148-356,"FL/FR/BL/BR, Y=356~1148")
# rim
P("림 전면(좌/우)",2,700+32-94,"")
P("림 후면",1,1400+64,"")
P("림 사이드",2,(705.89-(-922.05))+64,"")

# total length
tot = lenFB*2+lenSide*2+lenFB + lenRingFB*2+lenRingSide*2 + legH*len(legs) + (1148-356)*4 + (638)*2 + 1528 + 1691.94*2
print(f"\n각파이프 총 절단길이(호퍼 보강 포함): {tot/1000:.2f} m")
