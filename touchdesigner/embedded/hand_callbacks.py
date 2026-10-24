"""Asset-independent turn and hand articulation. No TouchDesigner dependency."""
import math
FINGERS=('Thumb','Index','Middle','Ring','Pinky')
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

# Prepended with art_animation.py, followed by JSON bind-pose data on install.
import json,time
_filters={side:HandFilter() for side in ('Left','Right')}
_last=None
_eulers={}
_bindings=None
_geometry=None
_thumb_quats={}
def onCook(s):
    global _last,_bindings,_geometry
    now=time.monotonic();dt=1/60 if _last is None else max(0,min(.1,now-_last));_last=now
    root=op('/project1');source=root.op('MediaPipe')
    if _bindings is None:_bindings=json.loads(root.op('hand_bindings').text)
    if _geometry is None:
        data=root.op('hand_geometry')
        _geometry=json.loads(data.text) if data is not None else {}
    mathlib=root.op('script1_callbacks').module
    thumb_targets={}
    detected={};quality={'Left':0.,'Right':0.}
    arrived=source.fetch('hand_pose_arrived',None)
    fresh=arrived is not None and 0<=now-arrived<.35
    if fresh:
        try:
            packet=json.loads(source.op('hand_results').text)
            data=packet.get('handResults',packet.get('gestureResults',{}))
            images=data.get('landmarks',[]);worlds=data.get('worldLandmarks',[])
            labels=data.get('handednesses',data.get('handedness',[]))
            pose=json.loads(source.op('pose_results').text).get('poseResults',{}).get('landmarks',[])
            sides=root.op('script1_callbacks').module.assign_hand_sides(images,pose[0] if pose else [],labels)
            candidates=[]
            for i,pts in enumerate(images):
                if len(pts)!=21:continue
                label=labels[i][0] if i<len(labels) and labels[i] else {}
                score=float(label.get('score',1))
                if score<.55:continue
                side=sides.get(i)
                if side not in _filters:continue
                points=worlds[i] if i<len(worlds) and len(worlds[i])==21 else pts
                points=[(float(p['x']),-float(p['y']),-float(p['z'])) for p in points]
                angles=hand_angles(points)
                if angles is not None:candidates.append((score,side,angles,points))
            for score,side,angles,points in sorted(candidates,key=lambda row:row[0],reverse=True):
                if side not in detected:
                    detected[side]=angles;quality[side]=score
                    name='mixamorig_'+side+'Hand'
                    if name in _geometry.get('palm_frames',{}):
                        rests=[_bindings[name+'Thumb'+str(j)]['rest'] for j in (1,2,3)]
                        thumb_targets[side]=mathlib.solve_thumb(points,_geometry['palm_frames'][name],rests)
        except (ValueError,KeyError,TypeError,IndexError):pass
    smoothed={side:_filters[side].update(detected.get(side),dt) for side in _filters}
    mathlib=root.op('script1_callbacks').module
    s.clear();s.numSamples=1
    for bone,binding in _bindings.items():
        side=binding['side'];finger=binding['finger'];j=binding['joint'];rest=binding['rest']
        values=smoothed[side][finger]
        curl=values[j]*binding.get('curl_sign',1)
        spread=values[3]*binding.get('spread_sign',1) if j==0 else 0.
        # Local bind rotation composed with constrained flexion/splay; not Euler addition.
        matrix=mathlib.mat_mul(mathlib.euler_xyz_to_matrix(rest),mathlib.euler_xyz_to_matrix((curl,0,spread)))
        if finger=='Thumb' and _geometry:
            restq=mathlib.matrix_to_quat(mathlib.euler_xyz_to_matrix(rest))
            previousq=_thumb_quats.get(bone,restq)
            target=thumb_targets.get(side)
            goal=target[j] if target else (previousq if _filters[side].age<.20 else restq)
            distance=mathlib.quat_angle(previousq,goal)
            if distance>1e-8:goal=mathlib.quat_slerp(previousq,goal,min(1.,math.radians(360)*dt/distance))
            current=mathlib.quat_slerp(previousq,goal,1-math.exp(-(18 if target else 4)*dt))
            _thumb_quats[bone]=current;matrix=mathlib.quat_to_matrix(current)
        euler=mathlib.matrix_to_euler_xyz(matrix)
        previous=_eulers.get(bone,rest)
        euler=mathlib.YBotRetargeter._unwrap(euler,previous);_eulers[bone]=euler
        for axis,value in zip('xyz',euler):s.appendChan(bone+'_r'+axis)[0]=value
    for side in _filters:
        s.appendChan(side.lower()+'_tracked')[0]=float(side in detected)
        s.appendChan(side.lower()+'_confidence')[0]=quality[side]
        s.appendChan(side.lower()+'_curl')[0]=sum(smoothed[side][n][1] for n in FINGERS)/5
