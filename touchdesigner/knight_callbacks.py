# Appended after the self-contained game core in the embedded DAT.
import time
_game=Game()
_game.enemy_hp[1]=0
_last_time=None
def onCook(scriptOp):
    global _last_time
    now=time.monotonic()
    dt=1/60 if _last_time is None else max(0,min(.1,now-_last_time))
    _last_time=now
    parent=scriptOp.parent()
    pad=parent.op('dualsense_raw');keys=parent.op('keyboard')
    def value(node,name):
        ch=node[name]
        return float(ch[0]) if ch is not None and len(ch) else 0.
    connected=value(pad,'connected')>.5
    def button(parname):return connected and value(pad,getattr(parent.par,parname).eval())>.5
    def key(name):return bool(parent.par.Keyboard) and value(keys,'k'+name)>.5
    move=deadzone(value(pad,'lx'),float(parent.par.Deadzone)) if connected else 0.
    aim=deadzone(value(pad,'ly'),float(parent.par.Deadzone)) if connected else 0.
    if bool(getattr(parent.par,'Invertattacky',False)):aim=-aim
    if key('a') or key('d'):move=float(key('d'))-float(key('a'))
    if key('w') or key('s'):aim=float(key('w'))-float(key('s'))
    controls=Input(move,aim,button('Jumpbutton') or key('z'),button('Dashbutton') or (connected and value(pad,'b6')>.5) or key('x'),button('Attackbutton') or key('c'),key('r') or (connected and value(pad,'b10')>.5))
    if hasattr(parent.par,'Contactdamage'):
        _game.boss_contact_enabled=bool(parent.par.Contactdamage)
        _game.contact_push=max(1.,min(8.,float(parent.par.Contactpush)))
        _game.impact_scale=max(.25,min(1.5,float(parent.par.Impactscale)))
    if hasattr(parent.par,'Limbdamage'):_game.boss_limb_enabled=bool(parent.par.Limbdamage)
    _game.advance(dt,controls if bool(parent.par.Active) else Input())
    source=op('/project1/MediaPipe');rig=op('/project1/Y_Bot');solver=op('/project1/script1')
    tracked=False;hands=[(0.,0.),(0.,0.)]
    if source is not None and rig is not None and solver is not None:
        arrived=source.fetch('retarget_pose_arrived',None)
        tracked=arrived is not None and 0<=time.monotonic()-arrived<.5 and value(solver,'quality')>.3
        if tracked:
            for i,side in enumerate(('Left','Right')):
                bone=rig.op('mixamorig_'+side+'Hand')
                m=bone.worldTransform;hands[i]=(float(m[0,3])*.02,float(m[1,3])*.02)
    camera_tracking=tracked
    if tracked:
        landmarks=solver.inputs[0] if solver.inputs else None
        tracked=landmarks is not None and min(value(landmarks,side+'_wrist:visibility') for side in ('left','right'))>.4
    if dt>0:_game.boss_step(dt,tracked,*hands)
    hitboxes=parent.op('boss_hitbox_map');segments={};visible=set()
    landmarks=solver.inputs[0] if solver is not None and solver.inputs else None
    if hitboxes is not None:
        for row in hitboxes.rows()[1:]:
            name,a_path,b_path,radius,va,vb=[cell.val for cell in row]
            a=parent.op(a_path);b=parent.op(b_path)
            if a is None or b is None:continue
            am=a.worldTransform;bm=b.worldTransform
            segments[name]=((float(am[0,3]),float(am[1,3])),(float(bm[0,3]),float(bm[1,3])),float(radius))
            if landmarks is not None and min(value(landmarks,va+':visibility'),value(landmarks,vb+':visibility'))>.4:visible.add(name)
    if dt>0:_game.boss_limb_step(dt,segments,camera_tracking,visible)
    channels=_game.channels()
    channels.update(boss_hp=_game.boss_hp,boss_phase=_game.boss_phase,boss_flash=_game.boss_flash,boss_tracking=float(_game.boss_tracking),camera_tracking=float(camera_tracking),boss_x=_game.boss_x)
    channels.update(connected=float(connected),input_move=move,input_jump=float(controls.jump),input_dash=float(controls.dash),input_attack=float(controls.attack))
    scriptOp.clear();scriptOp.numSamples=1
    for name,v in channels.items():scriptOp.appendChan(name)[0]=v
