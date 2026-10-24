"""Asset-independent turn and hand articulation. No TouchDesigner dependency."""
import math
FINGERS=('Thumb','Index','Middle','Ring','Pinky')

def attack_weapon_pose(phase,face,aim,x,y):
    """Clockwise sweep matched to the slash atlas, then mirror/aim as one unit."""
    phase=max(0.,min(1.,phase));face=1. if face>=0 else -1.
    if phase<.16:theta=85.-20.*(phase/.16)
    elif phase<.78:
        t=(phase-.16)/.62;t=t*t*(3.-2.*t);theta=65.-130.*t
    else:theta=-65.-20.*((phase-.78)/.22)
    a=math.radians(aim*90.)
    return {'weapon_angle':face*(theta-90.+aim*90.),
            'weapon_x':x+face*.30*math.cos(a),'weapon_y':y+.65+.30*math.sin(a)}
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(v):
    length=math.sqrt(dot(v,v));return tuple(x/max(length,1e-8) for x in v)
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,dot(unit(a),unit(b))))))
class TurnAnimator:
    def __init__(self):self.yaw=65.;self.turn=0.
    def update(self,facing,dt):
        target=65 if facing>=0 else -65
        delta=(target-self.yaw)*(1-math.exp(-18*max(0,dt)))
        self.yaw+=max(-720*dt,min(720*dt,delta))
        self.turn=min(1,abs(target-self.yaw)/90)
        return self.yaw
def hand_angles(points):
    if not points or len(points)!=21:return None
    if not all(len(p)==3 and all(math.isfinite(x) for x in p) for p in points):return None
    across=unit(sub(points[17],points[5]));forward=unit(sub(points[9],points[0]));normal=unit(cross(across,forward))
    if dot(normal,normal)<.5:return None
    result={}
    for name,start in zip(FINGERS,(1,5,9,13,17)):
        a,b,c,d=points[start:start+4];base=unit(sub(a,points[0]));seg=unit(sub(b,a))
        curl=math.degrees(math.atan2(abs(dot(seg,normal)),max(.001,dot(seg,base))))
        spread=math.degrees(math.atan2(dot(seg,across),max(.01,dot(seg,forward))))
        result[name]=[min(75,curl),min(100,angle(sub(b,a),sub(c,b))),min(80,angle(sub(c,b),sub(d,c))),max(-22,min(22,spread))]
    return result
class HandFilter:
    def __init__(self):
        self.angles={n:[0.,0.,0.,0.] for n in FINGERS};self.age=999.
    def update(self,target,dt):
        dt=max(0,min(.1,dt));self.age=0 if target is not None else self.age+dt
        if target is None:
            if self.age<.20:return self.angles
            target={n:[0.,0.,0.,0.] for n in FINGERS}
        alpha=1-math.exp(-(16 if self.age==0 else 4)*dt)
        for n in FINGERS:
            for j in range(4):
                delta=(target[n][j]-self.angles[n][j])*alpha
                self.angles[n][j]+=max(-420*dt,min(420*dt,delta))
                # Avoid subnormal doubles in the TD float32 channel conversion.
                if abs(self.angles[n][j])<1e-5:self.angles[n][j]=0.
        return self.angles
