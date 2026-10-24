import math
def onCook(s):
 s.clear()
 for sign in (-1,1):
  rings=[]
  for j in range(10):
   t=j/9.;cx=sign*(.20+.12*math.sin(t*2.3));cy=1.21+.43*t;r=.09*(1-t)+.004;ring=[]
   for k in range(12):
    a=k*math.tau/12;p=s.appendPoint();p.P=(cx+math.cos(a)*r,cy,math.sin(a)*r*.72);ring.append(p)
   rings.append(ring)
  for j in range(9):
   for k in range(12):
    q=s.appendPoly(4,closed=True,addPoints=False)
    for v,p in zip(q,[rings[j][k],rings[j+1][k],rings[j+1][(k+1)%12],rings[j][(k+1)%12]]):v.point=p
