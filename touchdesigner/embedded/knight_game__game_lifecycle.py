import json,time
from pathlib import Path
_last=0.
_ranges={}
_hand_max={'left':0.,'right':0.}
_hand_seen={'left':False,'right':False}
_frames=0
_start=time.monotonic()
def onStart():
    Path(project.folder, '.runtime').mkdir(exist_ok=True)
    if op('/project1/MediaPipe') is not None:op('/project1/MediaPipe').unstore('hand_pose_arrived')
    run("args[0].op('PLAY').openViewer()",parent(),delayFrames=45)
def onFrameStart(frame):
    global _frames
    _frames+=1
    if op('/project1/hand_retarget') is not None:op('/project1/hand_retarget').cook(force=True)
    parent().op('game_state').cook(force=True)
    parent().op('dash_state').cook(force=True)
def onFrameEnd(frame):
    global _last
    g=parent();pad=g.op('dualsense_raw')
    # Boss visibility is assigned after cooking, never a dependency on its own collision query.
    g.op('boss_rig').par.render=bool(g.op('game_state')['boss_hp'][0]>0)
    for c in pad.chans():
        v=float(c[0]);lo,hi=_ranges.get(c.name,(v,v));_ranges[c.name]=(min(lo,v),max(hi,v))
    if time.monotonic()-_last<2:return
    _last=time.monotonic()
    try:
        r={'time':time.time(),'errors':g.errors(recurse=True),'warnings':g.warnings(recurse=True),'scriptErrors':g.scriptErrors(recurse=True),'input_ranges':_ranges,'observed_frames_per_second':_frames/max(.001,time.monotonic()-_start),'state':{c.name:float(c[0]) for c in g.op('game_state').chans()}}
        h=op('/project1/hand_retarget')
        for side in ('left','right'):
            _hand_max[side]=max(_hand_max[side],float(h[side+'_curl'][0]))
            _hand_seen[side]=_hand_seen[side] or bool(h[side+'_tracked'][0])
        r['root_errors']=op('/project1').errors(recurse=True)
        r['root_script_errors']=op('/project1').scriptErrors(recurse=True)
        r['project']=project.name
        r['weapon_vertices']=g.op('equipped_weapon/imported_blade').numPoints
        r['last_limb_hit']=g.op('game_callbacks').module._game.last_limb_hit
        r['wrist_mirror']=bool(op('/project1/script1').par.Wristmirror)
        r['arm_joint_constraints']={'twist_total_degrees':180,'hand_neutral_cone':90,'solver_present':hasattr(op('/project1/script1_callbacks').module,'constrain_arm_joint')}
        r['palm_mapping']={'version':2,'geometry':op('/project1/hand_geometry') is not None,'forearm_pronation':True,'duplicate_euler_filter_bypassed':bool(op('/project1/filter1').bypass)}
        r['slash_vfx']={'frames':12,'atlas_loaded':op('/project1/knight_game/slash_atlas').width>0,'material_errors':op('/project1/knight_game/slash_sprite_mat').errors(),'draw_priority':float(op('/project1/knight_game/slash').par.drawpriority)}
        r['dash_vfx']={'frames':12,'atlas_loaded':g.op('dash_atlas').width>0,'material_errors':g.op('dash_sprite_mat').errors(),'state':{c.name:float(c[0]) for c in g.op('dash_state').chans()},'weapon_visible':bool(g.op('equipped_weapon').par.render),'invert_attack_y':bool(g.par.Invertattacky)}
        r['hands']={'tracked':{side:float(h[side+'_tracked'][0]) for side in ('left','right')},'seen':_hand_seen,'max_curl':_hand_max,'packet_age':time.monotonic()-op('/project1/MediaPipe').fetch('hand_pose_arrived',0)}
        Path(project.folder,'.runtime','game_health.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    except (OSError,AttributeError,TypeError):pass

# Refresh live hand statistics after numeric guard.
