out vec3 vNormal;
void main(){vec4 w=TDDeform(P);vNormal=normalize(TDDeformNorm(N));gl_Position=TDWorldToProj(w);}
