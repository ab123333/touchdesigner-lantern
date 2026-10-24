out vec2 slashUV;
void main() {
    // Local quad coordinates are known, so no implicit SOP uv layer is needed.
    slashUV = P.xy + vec2(0.5);
    float a = radians(-40.0);
    mat2 turn = mat2(cos(a), sin(a), -sin(a), cos(a));
    vec2 xy = turn * P.xy * 1.85 + vec2(0.72, 0.0);
    gl_Position = TDWorldToProj(TDDeform(vec3(xy, P.z)));
}
