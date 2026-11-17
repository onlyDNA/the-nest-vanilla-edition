#version 150

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 vertexColor;
in vec4 flatVertexColor;
in vec4 lightmapColor;
in vec2 texCoord0;
in vec2 texCoord1;

out vec4 fragColor;

// implementation note: translucent blocks and items in general

// add more as needed
bool shouldSkipApplyLightmap(vec4 color) {
    return
color.a == 254;
}

// adjust as needed
bool shouldDisableShading(vec4 color) {
    return
color.a == 254;
}


void main() {
    vec4 color = texture(Sampler0, texCoord0) * ColorModulator;
    vec4 normalizedTextureColor = texture(Sampler0, texCoord0) * 255;

    if (shouldDisableShading(normalizedTextureColor)) {
        color *= flatVertexColor;
    }
    else {
        color *= vertexColor;
    }

    if (color.a < 0.1) {
        discard;
    }


    if (!shouldSkipApplyLightmap(normalizedTextureColor)) {
        color *= lightmapColor;
    }

    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}
