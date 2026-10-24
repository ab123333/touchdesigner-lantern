"""Dash-only flipbook state; never drives physics or invulnerability."""
import math

class DashVFX:
    def __init__(self):
        self.active=False;self.tail_start=None;self.face=1.;self.x=0.;self.y=0.;self.last_time=None

    def update(self,active,phase,now,x,y,face):
        if not all(math.isfinite(float(v)) for v in (phase,now,x,y,face)):
            self.active=False;self.tail_start=None
            return self.output(0,False)
        if self.last_time is not None and now<self.last_time:
            self.active=False;self.tail_start=None
        self.last_time=now
        if active:
            if not self.active:self.face=1. if face>=0 else -1.
            self.x=x;self.y=y;self.tail_start=None
            progress=max(0.,min(1.,phase))*2/3
            visible=True
        else:
            if self.active:
                self.tail_start=now;self.x=x;self.y=y
            age=now-self.tail_start if self.tail_start is not None else 1.
            visible=0<=age<.08 and abs(x-self.x)<3 and abs(y-self.y)<3
            progress=2/3+max(0.,age)/.08/3
            if not visible:self.tail_start=None
        self.active=bool(active)
        return self.output(progress,visible)

    def output(self,progress,visible):
        position=min(11.,max(0.,progress)*12+1e-8) if visible else 0.
        frame=int(position)
        fade=1.-max(0.,min(1.,(progress-.94)/.06)) if visible else 0.
        return {'frame':float(frame),'next_frame':float(min(11,frame+1)),
                'blend':position-frame,'fade':fade,'visible':float(visible),
                'x':self.x,'y':self.y,'face':self.face}
