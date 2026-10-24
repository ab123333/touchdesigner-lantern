out vec2 slashUV;
void main() {
    slashUV=P.xy+vec2(0.5);
    // The bright head ends just ahead of the body; wisps trail behind it.
    vec2 xy=P.xy*vec2(2.75,1.50)+vec2(-0.78,0.0);
    gl_Position=TDWorldToProj(TDDeform(vec3(xy,P.z)));
}
