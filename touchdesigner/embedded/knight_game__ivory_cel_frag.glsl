uniform vec4 uHit;in vec3 vNormal;out vec4 fragColor;
void main(){float d=dot(normalize(vNormal),normalize(vec3(-.5,.85,1.2)));float band=d>.55?1.:d>.0?.72:.40;vec3 color=vec3(0.91,0.91,0.79);fragColor=TDOutputSwizzle(vec4(mix(color*band,vec3(1.,.25,.16),uHit.x),1.));}
