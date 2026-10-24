"""Visual-only attack flipbook. The combat clock remains authoritative."""
import math

def slash_frame(attack,phase,start=.16,end=1.,frames=12):
    if not math.isfinite(phase) or not attack or phase<start or phase>=end:
        return {'frame':0.,'next_frame':0.,'blend':0.,'visible':0.,'fade':0.}
    t=max(0.,min(1.,(phase-start)/max(1e-6,end-start)))
    position=min(frames-1.,t*frames)
    frame=int(position)
    fade=1.-max(0.,min(1.,(t-.93)/.07))
    return {'frame':float(frame),'next_frame':float(min(frames-1,frame+1)),
            'blend':position-frame,'visible':1.,'fade':fade}
