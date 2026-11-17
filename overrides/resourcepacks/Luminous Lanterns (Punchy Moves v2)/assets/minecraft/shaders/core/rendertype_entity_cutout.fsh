#version 150

#moj_import <fog.glsl>

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

in float vertexDistance;
in vec4 vertexColor;
in vec4 flatVertexColor;
in vec4 lightMapColor;
in vec4 overlayColor;
in vec2 texCoord0;

out vec4 fragColor;

// add more as needed
bool shouldSkipApplyLightmap(vec4 color) {
    return
color.a == 254;
}

// adjust as needed
// note that 
bool shouldDisableShading(vec4 color) {
    return
        color.a == 254;
}

void main() {
    vec4 color = texture(Sampler0, texCoord0) * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }

    vec4 conv = color * 255;

    if (shouldDisableShading(conv)) {
        color *= flatVertexColor;
    }
    else {
        color *= vertexColor;
    }

    color.rgb = mix(overlayColor.rgb, color.rgb, overlayColor.a);
    
    if (!shouldSkipApplyLightmap(conv)) {
        color *= lightMapColor;
    }
    
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
