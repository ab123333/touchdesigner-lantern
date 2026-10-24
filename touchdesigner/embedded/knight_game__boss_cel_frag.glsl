uniform vec4 uHit;in vec3 vNormal;out vec4 fragColor;
void main(){float d=dot(normalize(vNormal),normalize(vec3(-.5,.85,1.2)));float band=d>.55?1.:d>.0?.72:.40;vec3 color=vec3(0.49,0.29,0.6);fragColor=TDOutputSwizzle(vec4(mix(color*band,vec3(.95,.89,1.),uHit.x),1.));}
