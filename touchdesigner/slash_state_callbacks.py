# slash_animation.py is prepended at install; no external runtime imports.
def onCook(s):
    state=s.inputs[0]
    result=slash_frame(float(state['attack'][0]),float(state['attack_phase'][0]))
    s.clear();s.numSamples=1
    for name,value in result.items():s.appendChan(name)[0]=value
