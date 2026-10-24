in vec3 vNormal;out vec4 fragColor;
void main(){float d=dot(normalize(vNormal),normalize(vec3(-.5,.85,1.2)));float band=d>.55?1.:d>.0?.72:.40;vec3 color=vec3(0.07,0.14,0.19);fragColor=TDOutputSwizzle(vec4(color*band,1.));}
