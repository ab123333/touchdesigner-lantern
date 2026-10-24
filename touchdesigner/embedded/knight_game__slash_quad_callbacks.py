def onCook(s):
    s.clear()
    q=s.appendPoly(4,closed=True,addPoints=True)
    for v,p in zip(q,((-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0))):v.point.P=p
