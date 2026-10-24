# dash_animation.py is embedded above this callback.
_dash_vfx=DashVFX()
def onCook(s):
    state=s.inputs[0]
    def c(name):return float(state[name][0])
    values=_dash_vfx.update(c('dash')>.5,c('dash_phase'),c('time'),c('x'),c('y'),c('face'))
    s.clear();s.numSamples=1
    for name,value in values.items():s.appendChan(name)[0]=value
