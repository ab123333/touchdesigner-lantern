out vec3 vNormal;
void main(){vec4 w=TDDeform(P);vNormal=normalize(TDDeformNorm(N));w.xyz+=normalize(vNormal)*0.018;gl_Position=TDWorldToProj(w);}
