"""Deterministic 2.5D action-controller simulation, embedded in a TD Script CHOP."""
from dataclasses import dataclass
import math

STEP = 1.0 / 120.0
# Solid ledges: left, right, bottom, top. Feet are at player.y.
PLATFORMS = ((-14.,14.,-1.,0.),(-4.8,-2.5,0.95,1.25),
             (-0.8,1.2,1.95,2.25),(4.,6.3,1.0,1.3),(9.,10.,0.,3.8))

def approach(value, target, amount):
    return min(target,value+amount) if value<target else max(target,value-amount)

def deadzone(value, threshold=0.15):
    value=max(-1.,min(1.,float(value)))
    return 0. if abs(value)<=threshold else math.copysign((abs(value)-threshold)/(1-threshold),value)

def segment_distance(a,b,c,d):
    """2D closest segment distance, parameter on AB, and point on AB."""
    def sub(p,q):return (p[0]-q[0],p[1]-q[1])
    def cross(p,q):return p[0]*q[1]-p[1]*q[0]
    def dot(p,q):return p[0]*q[0]+p[1]*q[1]
    def project(p,x,y):
        v=sub(y,x);t=max(0.,min(1.,dot(sub(p,x),v)/max(1e-12,dot(v,v))))
        return t,(x[0]+t*v[0],x[1]+t*v[1])
    ab=sub(b,a);cd=sub(d,c);den=cross(ab,cd)
    if abs(den)>1e-10:
        ac=sub(c,a);t=cross(ac,cd)/den;u=cross(ac,ab)/den
        if 0<=t<=1 and 0<=u<=1:return 0.,t,(a[0]+t*ab[0],a[1]+t*ab[1])
    candidates=[]
    for t,p in ((0.,a),(1.,b)):
        _,q=project(p,c,d);candidates.append((math.hypot(*sub(p,q)),t,p))
    for p in (c,d):
        t,q=project(p,a,b);candidates.append((math.hypot(*sub(p,q)),t,q))
    return min(candidates,key=lambda item:item[0])

@dataclass
class Input:
    move: float = 0.
    aim: float = 0.
    jump: bool = False
    dash: bool = False
    attack: bool = False
    reset: bool = False

class Game:
    def __init__(self):
        self.x,self.y=-7.,0.
        self.vx=self.vy=0.
        self.face=1.
        self.grounded=True
        self.wall=0
        self.coyote=0.10
        self.jump_buffer=0.
        self.air_jumps=1
        self.air_dash=True
        self.dash_time=self.dash_cooldown=0.
        self.attack_time=self.attack_cooldown=0.
        self.attack_dir=0
        self.attack_serial=0
        self.combo=0
        self.enemy_hp=[4,4]
        self.enemy_respawn=[0.,0.]
        self.enemy_last_hit=[-1,-1]
        self.enemy_x=[2.5,7.2]
        self.hits=0
        self.hp=5
        self.invulnerable=0.
        self.hitstop=0.
        self.flash=0.
        self.time=self.phase=0.
        self.accumulator=0.
        self.previous={k:False for k in ('jump','dash','attack','reset')}
        self.pending=set()
        self.camera_x=-2.
        self.respawns=0
        self.speed=4.2
        self.gravity=23.
        self.jump_speed=8.4
        self.boss_x=7.
        self.boss_hp=30
        self.boss_phase=0
        self.boss_timer=0.
        self.boss_cooldown=0.
        self.boss_previous=None
        self.boss_hit_serial=-1
        self.boss_hit_player=False
        self.boss_tracking=False
        self.boss_flash=0.
        self.boss_swing_velocity=(0.,0.)
        self.boss_attack_velocity=(0.,0.)
        self.boss_contact_enabled=True
        self.contact_push=4.
        self.impact_scale=1.
        self.hurt_time=0.
        self.knockback_x=0.
        self.boss_limb_enabled=True
        self.limb_previous={}
        self.limb_tracking=False
        self.limb_tracked=set()
        self.limb_player=None
        self.limb_count=0
        self.last_limb_hit=''

    def take_hit(self,source_x,impulse=None):
        """One damage event; recoil is independent of movement input/friction."""
        if self.hp<=0 or self.invulnerable>0:return False
        away=-1. if self.x<source_x else 1.
        ix,iy=impulse if impulse is not None else (away*self.contact_push,3.2)
        if not math.isfinite(ix) or not math.isfinite(iy):return False
        self.hp=max(0,self.hp-1);self.invulnerable=1.;self.flash=.15
        self.hurt_time=.22;self.knockback_x=max(-8.,min(8.,ix))
        self.vx=0.;self.vy=max(-6.,min(6.,iy))
        self.dash_time=self.attack_time=self.jump_buffer=self.coyote=0.
        self.grounded=False
        return True

    def boss_limb_step(self,dt,segments,tracking,tracked_ids=None):
        """Rendered-bone capsules in XY; bounded swept contact and local inertia.

        segments maps a stable limb id to (start XY, end XY, radius). Z is
        deliberately ignored in this side-view game. Missing tracking preserves
        static contact but clears momentum and swept history.
        """
        if not math.isfinite(dt) or dt<=0:return
        valid={}
        for name,(a,b,radius) in segments.items():
            if all(math.isfinite(v) and abs(v)<1000 for p in (a,b) for v in p) and math.isfinite(radius):
                valid[name]=(tuple(a),tuple(b),max(.04,min(.3,radius)))
        self.limb_count=len(valid)
        moving=bool(tracking and self.limb_tracking and dt<=.1)
        tracked_ids=set(valid if tracked_ids is None else tracked_ids) if tracking else set()
        candidates=[]
        for name,(a,b,radius) in valid.items():
            old=self.limb_previous.get(name,(a,b,radius))
            travel=max(math.dist(a,old[0]),math.dist(b,old[1]))
            # A tracking jump is a new static pose, never a high-speed attack.
            continuous=moving and name in self.limb_previous and name in tracked_ids and name in self.limb_tracked and travel<=1.5
            oa,ob=(old[0],old[1]) if continuous else (a,b)
            player_old=self.limb_player if continuous and self.limb_player else (self.x,self.y)
            player_travel=math.dist(player_old,(self.x,self.y))
            steps=max(1,min(48,math.ceil(((travel if continuous else 0)+player_travel)/.08)))
            for i in range(steps+1):
                f=i/steps
                sa=tuple(x+(y-x)*f for x,y in zip(oa,a));sb=tuple(x+(y-x)*f for x,y in zip(ob,b))
                px,py=(x+(y-x)*f for x,y in zip(player_old,(self.x,self.y)))
                distance,t,point=segment_distance(sa,sb,(px,py+.23),(px,py+1.05))
                if distance>radius+.23:continue
                velocity=tuple(((a[j]-oa[j])*(1-t)+(b[j]-ob[j])*t)/dt for j in range(2))
                speed=math.hypot(*velocity)
                away=-1. if px<point[0] else 1.
                if continuous and speed>.6:
                    strength=max(2.5,min(8.,(3.5+.38*min(10.,speed))*self.impact_scale))
                    impulse=(velocity[0]/speed*strength,velocity[1]/speed*strength)
                    if abs(velocity[1])/speed<.15:impulse=(impulse[0],1.8)
                else:impulse=(away*self.contact_push,3.2)
                candidates.append((math.hypot(*impulse),name,point[0],impulse))
                break
        self.limb_previous=valid;self.limb_tracking=bool(tracking);self.limb_player=(self.x,self.y)
        self.limb_tracked=tracked_ids
        if self.boss_limb_enabled and self.boss_hp>0 and candidates:
            _,name,source_x,impulse=max(candidates,key=lambda item:item[0])
            if self.take_hit(source_x,impulse):self.last_limb_hit=name

    def boss_step(self,dt,tracking,left_hand,right_hand):
        if not math.isfinite(dt) or dt<=0:return
        dt=min(.1,dt)
        hands=(left_hand,right_hand)
        tracking=bool(tracking) and all(math.isfinite(v) for hand in hands for v in hand)
        self.boss_tracking=tracking
        self.boss_cooldown=max(0.,self.boss_cooldown-dt)
        self.boss_flash=max(0.,self.boss_flash-dt)
        if self.boss_hp<=0:self.boss_phase=0;return
        speed=0.
        if tracking and self.boss_previous is not None:
            velocities=[((a[0]-b[0])/dt,(a[1]-b[1])/dt) for a,b in zip(hands,self.boss_previous)]
            velocity=max(velocities,key=lambda v:math.hypot(*v))
            length=math.hypot(*velocity)
            velocity=tuple(v*min(1.,12./max(.001,length)) for v in velocity)
            alpha=1-math.exp(-24*dt)
            self.boss_swing_velocity=tuple(a+(b-a)*alpha for a,b in zip(self.boss_swing_velocity,velocity))
            speed=math.hypot(*self.boss_swing_velocity)
        self.boss_previous=hands if tracking else None
        # Tracking loss cancels dangerous actions, not the player simulation.
        if not tracking:
            self.boss_phase=0;self.boss_timer=0.
            self.boss_swing_velocity=self.boss_attack_velocity=(0.,0.)
        if tracking and self.boss_phase==0 and self.boss_cooldown<=0 and speed>2.6:
            self.boss_phase=1;self.boss_timer=.42;self.boss_hit_player=False
            self.boss_attack_velocity=self.boss_swing_velocity
        if self.boss_phase==1 and speed>math.hypot(*self.boss_attack_velocity):
            self.boss_attack_velocity=self.boss_swing_velocity
        if self.boss_phase:
            self.boss_timer-=dt
            if self.boss_timer<=0:
                if self.boss_phase==1:self.boss_phase=2;self.boss_timer=.24
                else:self.boss_phase=0;self.boss_cooldown=.95
        if self.boss_phase==2 and not self.boss_hit_player and abs(self.x-self.boss_x)<2.4 and -1.28<self.y<1.3:
            vx,vy=self.boss_attack_velocity
            speed=min(10.,math.hypot(vx,vy))
            direction=math.copysign(1.,vx) if abs(vx)>.5 else (-1. if self.x<self.boss_x else 1.)
            strength=max(2.5,min(8.,(3.5+.38*speed)*self.impact_scale))
            if self.take_hit(self.boss_x,(direction*strength,4.+max(-1.5,min(2.,vy*.2)))):
                self.boss_hit_player=True
        if .0672<self.attack_time<.145 and self.boss_hit_serial!=self.attack_serial:
            dx=self.boss_x-self.x
            valid=(0<dx*self.face<1.55 and self.y<3.5) if self.attack_dir==0 else (abs(dx)<.9 and self.y<4.2)
            if valid:
                self.boss_hp-=1;self.boss_hit_serial=self.attack_serial;self.hits+=1;self.boss_flash=.15;self.hitstop=.045
                if self.attack_dir==-1:self.vy=7.2;self.air_dash=True

    def respawn(self):
        self.x,self.y=-7.,0.
        self.vx=self.vy=0.
        self.hp=5
        self.invulnerable=1.
        self.dash_time=self.attack_time=0.
        self.hurt_time=self.knockback_x=0.
        self.limb_previous={};self.limb_tracking=False;self.limb_tracked=set();self.limb_player=None;self.last_limb_hit=''
        self.grounded=True
        self.air_dash=True
        self.air_jumps=1
        self.respawns+=1

    def advance(self,dt,controls):
        for key in self.previous:
            down=bool(getattr(controls,key))
            if down and not self.previous[key]: self.pending.add(key)
            self.previous[key]=down
        self.accumulator+=max(0.,min(float(dt),0.10))
        while self.accumulator+1e-12>=STEP:
            edges=self.pending
            self.pending=set()
            self._step(controls,edges)
            self.accumulator-=STEP
        return self.channels()

    def _step(self,c,edges):
        dt=STEP
        self.time+=dt
        if 'reset' in edges:
            self.respawn()
            self.boss_hp=30;self.boss_phase=0
            self.boss_previous=None;self.boss_timer=self.boss_cooldown=0.
            self.boss_swing_velocity=self.boss_attack_velocity=(0.,0.)
            self.boss_hit_player=False;self.boss_hit_serial=-1;self.boss_flash=0.
        for name in ('dash_cooldown','attack_cooldown','invulnerable','flash'):
            setattr(self,name,max(0.,getattr(self,name)-dt))
        for i in range(2):
            if self.enemy_respawn[i]>0:
                self.enemy_respawn[i]-=dt
                if self.enemy_respawn[i]<=0: self.enemy_hp[i]=4
        if self.hitstop>0:
            self.hitstop=max(0.,self.hitstop-dt)
            self.pending.update(edges-{'reset'})
            return
        hurting=self.hurt_time>0
        self.hurt_time=max(0.,self.hurt_time-dt)
        self.knockback_x*=math.exp(-5*dt)
        if abs(self.knockback_x)<.025:self.knockback_x=0.
        if hurting:
            c=Input(reset=c.reset)
            edges=edges-{'jump','dash','attack'}
        if 'jump' in edges:self.jump_buffer=0.12
        else:self.jump_buffer=max(0.,self.jump_buffer-dt)
        self.coyote=0.10 if self.grounded else max(0.,self.coyote-dt)
        if abs(c.move)>0.05 and self.dash_time<=0:self.face=1. if c.move>0 else -1.
        if self.jump_buffer>0:
            if self.grounded or self.coyote>0:
                self.vy=self.jump_speed
                self.grounded=False; self.coyote=0.; self.jump_buffer=0.
            elif self.wall:
                self.vy=self.jump_speed
                self.vx=-self.wall*self.speed*1.1
                self.face=float(-self.wall)
                self.jump_buffer=0.
            elif self.air_jumps>0:
                self.vy=self.jump_speed*0.95
                self.air_jumps-=1; self.jump_buffer=0.
        if not hurting and not c.jump and self.vy>3.5:self.vy=3.5
        if 'dash' in edges and self.dash_cooldown<=0 and (self.grounded or self.air_dash):
            self.dash_time=0.16
            self.dash_cooldown=0.48
            self.air_dash=False
            self.invulnerable=max(self.invulnerable,0.16)
        if 'attack' in edges and self.attack_cooldown<=0:
            self.attack_time=0.24
            self.attack_cooldown=0.29
            self.attack_serial+=1
            self.combo=(self.combo+1)%3
            self.attack_dir=1 if c.aim>0.5 else (-1 if c.aim<-.5 and not self.grounded else 0)
        self.attack_time=max(0.,self.attack_time-dt)
        if self.dash_time>0:
            self.dash_time=max(0.,self.dash_time-dt)
            self.vx=self.face*12.
            self.vy=0.
        else:
            acceleration=36. if self.grounded else 22.
            self.vx=approach(self.vx,c.move*self.speed,acceleration*dt)
            self.vy=max(-13.,self.vy-self.gravity*dt)
            if self.wall and c.move*self.wall>0 and self.vy<0:self.vy=max(self.vy,-2.5)
        half=0.23; height=1.28
        oldx,oldy=self.x,self.y
        self.x+=(self.vx+self.knockback_x)*dt
        self.wall=0
        for left,right,bottom,top in PLATFORMS:
            if self.y+height>bottom+0.02 and self.y<top-0.02:
                if self.x+half>left and self.x-half<right:
                    if oldx+half<=left+0.005:self.x=left-half;self.wall=1;self.vx=self.knockback_x=0.
                    elif oldx-half>=right-0.005:self.x=right+half;self.wall=-1;self.vx=self.knockback_x=0.
        self.x=max(-13.7,min(13.7,self.x))
        if abs(self.x)>=13.7 and self.x*self.knockback_x>0:self.knockback_x=0.
        self.y+=self.vy*dt
        self.grounded=False
        for left,right,bottom,top in PLATFORMS:
            if self.x+half>left and self.x-half<right:
                if self.vy<=0 and oldy>=top-0.005 and self.y<=top:
                    self.y=top;self.vy=0.;self.grounded=True
                    self.air_jumps=1;self.air_dash=True
                elif self.vy>0 and oldy+height<=bottom+0.005 and self.y+height>=bottom:
                    self.y=bottom-height;self.vy=0.
        if self.attack_time>0.0672 and self.attack_time<0.145:
            for i,ex in enumerate(self.enemy_x):
                if self.enemy_hp[i]<=0 or self.enemy_last_hit[i]==self.attack_serial:continue
                dx,dy=ex-self.x,0.48-(self.y+0.60)
                valid=(0<dx*self.face<1.35 and abs(dy)<0.8) if self.attack_dir==0 else (abs(dx)<0.65 and 0<dy*self.attack_dir<1.4)
                if valid:
                    self.enemy_last_hit[i]=self.attack_serial
                    self.enemy_hp[i]-=1;self.hits+=1
                    self.hitstop=0.045;self.flash=0.12
                    if self.attack_dir==-1:self.vy=7.2;self.air_dash=True
                    if self.enemy_hp[i]<=0:self.enemy_respawn[i]=3.
        for i,ex in enumerate(self.enemy_x):
            if self.enemy_hp[i]>0 and abs(ex-self.x)<0.50 and self.y<0.8 and self.invulnerable<=0:
                self.take_hit(ex)
        # Core body collider only: the extended arms retain their telegraphed attack.
        # The visible Boss remains a contact hazard even without camera tracking.
        if self.boss_contact_enabled and self.boss_hp>0 and abs(self.x-self.boss_x)<.55+half and self.y<3.3 and self.y+height>0:
            self.take_hit(self.boss_x)
        if self.hp<=0 or self.y<-6:self.respawn()
        self.phase+=abs(self.vx)*dt*3.4
        self.camera_x+=(max(-5.,min(5.,self.x))-self.camera_x)*(1-math.exp(-4*dt))

    def channels(self):
        running=self.grounded and abs(self.vx)>0.12
        state=5 if self.dash_time>0 else 4 if self.attack_time>0 else 3 if not self.grounded and self.vy<0 else 2 if not self.grounded else 1 if running else 0
        return {'x':self.x,'y':self.y,'vx':self.vx+self.knockback_x,'vy':self.vy,'face':self.face,
            'grounded':float(self.grounded),'state':state,'phase':self.phase,
            'bob':abs(math.sin(self.phase))*.035 if running else math.sin(self.time*2.5)*.012,
            'leg_l':math.sin(self.phase)*32 if running else (-18 if not self.grounded else 0),
            'leg_r':-math.sin(self.phase)*32 if running else (23 if not self.grounded else 0),
            'dash':float(self.dash_time>0),'dash_phase':1-self.dash_time/.16 if self.dash_time else 0.,'attack':float(self.attack_time>0),
            'attack_phase':1-self.attack_time/.24 if self.attack_time else 0,
            'attack_dir':self.attack_dir,'combo':self.combo,'hp':self.hp,'hits':self.hits,
            'enemy0hp':self.enemy_hp[0],'enemy1hp':self.enemy_hp[1],
            'flash':float(self.flash>0),'camera_x':self.camera_x,'time':self.time,
            'hurt':float(self.hurt_time>0),'knockback_x':self.knockback_x,
            'invulnerable':self.invulnerable,'boss_impact_speed':math.hypot(*self.boss_attack_velocity),
            'boss_limb_count':self.limb_count,
            'dash_ready':float(self.dash_cooldown<=0 and (self.grounded or self.air_dash))}

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
