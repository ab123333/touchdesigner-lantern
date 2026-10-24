uniform sampler2D uSlashAtlas;
uniform vec4 uFrames; // current, next, interpolation, final fade
uniform vec4 uStyle;  // brightness, inset as fraction of cell, reserved, reserved
in vec2 slashUV;
out vec4 fragColor;

vec3 frameColor(float index) {
    float col = mod(index, 4.0);
    float row = floor(index / 4.0);
    // Atlas is ordered from top left; texture UV origin is bottom left.
    vec2 inside = mix(vec2(uStyle.y), vec2(1.0-uStyle.y), slashUV);
    vec2 uv = (vec2(col, 2.0-row) + inside) / vec2(4.0, 3.0);
    vec3 raw = texture(uSlashAtlas, uv).rgb;
    // Remove the supplied near-black matte on the GPU; retain blue glow.
    float peak = max(raw.r, max(raw.g, raw.b));
    float key = smoothstep(0.025, 0.14, peak);
    return max(raw - vec3(0.004,0.008,0.014), vec3(0.0)) * key;
}
void main() {
    vec3 light = mix(frameColor(uFrames.x), frameColor(uFrames.y), uFrames.z);
    float edge = smoothstep(0.0,0.018,min(min(slashUV.x,slashUV.y),min(1.0-slashUV.x,1.0-slashUV.y)));
    light *= uFrames.w * uStyle.x * edge;
    if (max(light.r,max(light.g,light.b)) < 0.001) discard;
    // ONE + ONE RGB blending: black contributes nothing, not a dark rectangle.
    fragColor = TDOutputSwizzle(vec4(light, 1.0));
}
