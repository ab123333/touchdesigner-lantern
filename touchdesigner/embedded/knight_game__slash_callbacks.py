import math
def onCook(s):
 s.clear()
 for i in range(25):
  a=-1.15+i*2.3/25;b=-1.15+(i+1)*2.3/25;q=s.appendPoly(4,closed=True,addPoints=True)
  for v,p in zip(q,[(math.cos(a)*.76,math.sin(a)*.76,0),(math.cos(a)*.90,math.sin(a)*.90,0),(math.cos(b)*.90,math.sin(b)*.90,0),(math.cos(b)*.76,math.sin(b)*.76,0)]):v.point.P=p
