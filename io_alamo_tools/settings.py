import bpy

material_parameter_dict = {
    "alDefault.fx": [""],
    "BatchMeshAlpha.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "BatchMeshGloss.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "Grass.fx": ["Emissive", "Diffuse", "Diffuse1", "BendScale", "BaseTexture"],
    "MeshAdditive.fx": ["BaseTexture", "UVScrollRate", "Color"],
    "MeshAlpha.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "MeshAlphaScroll.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "MeshBumpColorize.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "Colorization", "UVOffset",
                            "BaseTexture", "NormalTexture"],
    "MeshBumpColorizeVertex.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "Colorization", "UVOffset",
                            "BaseTexture", "NormalTexture"],
    "MeshBumpColorizeDetail.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "Colorization", "UVOffset",
                            "BaseTexture", "DetailTexture", "NormalTexture", "MappingScale", "BlendSharpness", "NormalDetailTexture"],
    "MeshBumpLight.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "Colorization", "UVOffset",
                         "BaseTexture", "NormalTexture"],
    "MeshCollision.fx": ["Color"],
    "MeshGloss.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "MeshGlossColorize.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture", "GlossTexture"],
    "MeshShadowVolume.fx": ["DebugColor"],
    "MeshShield.fx": ["Color", "EdgeBrightness", "BaseUVScale", "WaveUVScale", "DistortUVScale",
                      "BaseUVScrollRate",
                      "WaveUVScrollRate", "DistortUVScrollRate", "BaseTexture", "WaveTexture", "DistortionTexture"],
    "Nebula.fx": ["BaseTexture", "UVScrollRate", "DistortionScale", "SFreq", "TFreq"],
    "Planet.fx": ["Emissive", "Diffuse", "Specular", "Atmosphere", "CityColor", "AtmospherePower",
                  "CloudScrollRate", "BaseTexture", "NormalTexture", "CloudTexture", "CloudNormalTexture"],
    "RSkinAdditive.fx": ["BaseTexture", "UVScrollRate", "Color"],
    "RSkinAlpha.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "RSkinBumpColorize.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "Colorization", "UVOffset",
                             "BaseTexture", "NormalTexture"],
    "RSkinGloss.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "RSkinGlossColorize.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "Colorization", "BaseTexture",
                              "GlossTexture"],
    "RSkinShadowVolume.fx": ["DebugColor"],
    "Skydome.fx": ["Emissive", "CloudScrollRate", "CloudScale", "BaseTexture", "CloudTexture"],
    "TerrainMeshBump.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture", "NormalTexture"],
    "TerrainMeshGloss.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BaseTexture"],
    "Tree.fx": ["Emissive", "Diffuse", "Specular", "Shininess", "BendScale", "BaseTexture", "NormalTexture"],
    "LightProxy.fx": ["Diffuse"]
}

vertex_format_dict = {
    "alDefault.fx"          : "alD3dVertNU2",
    "BatchMeshAlpha.fx"     : "alD3dVertNU2",
    "BatchMeshGloss.fx"     : "alD3dVertNU2",
    "Grass.fx"              : "alD3dVertGrass",
    "MeshAdditive.fx"       : "alD3dVertNU2",
    "MeshAlpha.fx"          : "alD3dVertNU2",
    "MeshAlphaScroll.fx"    : "alD3dVertNU2",
    "MeshBumpColorize.fx"   : "alD3dVertNU2U3U3",
    "MeshBumpColorizeVertex.fx"   : "alD3dVertNU2U3U3",
    "MeshBumpColorizeDetail.fx"   : "alD3dVertNU2U3U3",
    "MeshBumpLight.fx"      : "alD3dVertNU2U3U3",
    "MeshCollision.fx"      : "alD3dVertN",
    "MeshGloss.fx"          : "alD3dVertNU2",
    "MeshGlossColorize.fx"  : "alD3dVertNU2",
    "MeshShadowVolume.fx"   : "alD3dVertN",
    "MeshShield.fx"         : "alD3dVertNU2C",
    "Nebula.fx"             : "alD3dVertNU2C",
    "Planet.fx"             : "alD3dVertNU2U3U3",
    "RSkinAdditive.fx"         : "alD3dVertRSkinNU2",
    "RSkinAlpha.fx"            : "alD3dVertRSkinNU2",
    "RSkinBumpColorize.fx"  : "alD3dVertRSkinNU2U3U3",
    "RSkinGloss.fx"         : "alD3dVertRSkinNU2",
    "RSkinGlossColorize.fx" : "alD3dVertRSkinNU2",
    "RSkinShadowVolume.fx"  : "alD3dVertRSkinNU2",
    "Skydome.fx"            : "alD3dVertNU2",
    "TerrainMeshBumb.fx"    : "alD3dVertNU2U3U3",
    "TerrainMeshGloss.fx"   : "alD3dVertNU2",
    "Tree.fx"               : "alD3dVertNU2",
    "LightProxy.fx"         : "alD3dVertNU2"
}

billboard_array = {"Disable":0, "Parallel":1, "Face":2, "ZAxis View": 3, "ZAxis Light":4, "ZAxis Wind":5, "Sunlight Glow":6, "Sun":7}

bumpMappingList = ['MeshBumpColorize.fx', 'MeshBumpColorizeVertex.fx', 'MeshBumpColorizeDetail.fx', "MeshBumpLight.fx", "Planet.fx", "RSkinBumpColorize.fx", "TerrainMeshBump.fx", "Tree.fx"]

rotation_curve_name = ['].rotation_quaternion', '].rotation_euler']

#no_UV_Shaders = {"alDefault.fx", "MeshCollision.fx", "MeshShadowVolume.fx", "RSkinShadowVolume.fx"}
