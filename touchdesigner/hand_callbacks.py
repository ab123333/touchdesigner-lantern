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
