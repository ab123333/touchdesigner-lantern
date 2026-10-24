# Prepended with art_animation.py. Art-only outputs never change collision facing.
import time
_turn=TurnAnimator()
_last=None
_values={}
def onCook(s):
    global _last
    now=time.monotonic();dt=1/60 if _last is None else max(0,min(.1,now-_last));_last=now
    state=s.inputs[0]
    def c(name):return float(state[name][0])
    response=float(s.parent().par.Turnspeed) if hasattr(s.parent().par,'Turnspeed') else 18.
    yaw=_turn.update(c('face'),dt*max(4.,min(40.,response))/18.)
    run=min(1,abs(c('vx'))/3)
    targets={'yaw':yaw,'turn':_turn.turn,'lean':-c('vx')*2,'head':c('vx')*.6,
             'leg_l':math.sin(c('phase'))*32*run if c('grounded') else -18,
             'leg_r':-math.sin(c('phase'))*32*run if c('grounded') else 24,
             'cape':c('vx')*3+math.sin(c('time')*8)*run*3}
    # The FBX weapon points +Z in its own mesh. RX=-90 turns it upright.
    phase=c('attack_phase');attack=c('attack');face=c('face');aim=c('attack_dir')
    targets.update(attack_weapon_pose(phase,face,aim,c('x'),c('y')))
    s.clear();s.numSamples=1
    for name,value in targets.items():
        if name not in ('yaw','turn','weapon_angle','weapon_x','weapon_y'):
            previous=_values.get(name,value);value=previous+(value-previous)*(1-math.exp(-16*dt));_values[name]=value
        s.appendChan(name)[0]=value
