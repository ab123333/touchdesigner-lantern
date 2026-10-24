in vec3 vNormal;out vec4 fragColor;
void main(){float d=dot(normalize(vNormal),normalize(vec3(-.5,.85,1.2)));float band=d>.55?1.:d>.0?.72:.40;vec3 color=vec3(0.85,0.99,0.91);fragColor=TDOutputSwizzle(vec4(color*1.,1.));}
