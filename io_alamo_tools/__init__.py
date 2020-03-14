bl_info = {
    "name": "ALAMO Tools",
    "author": "Gaukler",
    "version": (0, 0, 1, 0),
    "blender": (2, 82, 0),
    "category": "Import-Export"
}

if "bpy" in locals():
    import importlib
    importlib.reload(import_alo)
    importlib.reload(import_ala)
    importlib.reload(export_alo)
    importlib.reload(export_ala)
    importlib.reload(settings)
    importlib.reload(utils)
else:
    from . import import_alo
    from . import import_ala
    from . import export_alo
    from . import export_ala
    from . import settings
    from . import utils

import bpy
import mathutils
from bpy.props import *
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )

class createConstraintBoneButton(bpy.types.Operator):
    bl_idname = "create.constraint_bone"
    bl_label = "Create constraint bone"

    def execute(self, context):
        object = bpy.context.view_layer.objects.active
        armature = utils.findArmature()

        bpy.context.view_layer.objects.active = armature
        utils.setModeToEdit()

        bone = armature.data.edit_bones.new(object.name)
        bone.tail = bone.head +  mathutils.Vector((0, 0, 1))
        bone.matrix = object.matrix_world
        object.location = mathutils.Vector((0.0, 0.0, 0.0))
        object.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        constraint = object.constraints.new('CHILD_OF')
        constraint.target = armature
        constraint.subtarget = bone.name

        utils.setModeToObject()
        bpy.context.view_layer.objects.active = object
        return {'FINISHED'}

def skeletonEnumCallback(scene, context):
    armatures = [('None', 'None', '', '', 0)]
    counter = 1
    for arm in bpy.data.objects:  # test if armature exists
        if arm.type == 'ARMATURE':
            armatures.append((arm.name, arm.name, '', '', counter))
            counter += 1

    return armatures

class skeletonEnumClass(PropertyGroup):
    skeletonEnum : EnumProperty(
        name='Active Skeleton',
        description = "skeleton that is exported",
        items = skeletonEnumCallback
    )

class ALAMO_PT_ToolsPanel(bpy.types.Panel):

    bl_label = "ALAMO properties"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ALAMO"

    def draw(self, context):
        object = context.object
        layout = self.layout
        scene = context.scene
        c = layout.column()

        c.prop(scene.ActiveSkeleton, 'skeletonEnum')

        if type(object) != type(None):
            if(object.type == 'MESH'):
                if bpy.context.mode == 'OBJECT':
                    c.prop(object, "HasCollision")
                    c.prop(object, "Hidden")

                    armature = utils.findArmature()
                    if armature != None:
                        hasChildConstraint = False
                        for constraint in object.constraints:
                            if constraint.type == 'CHILD_OF':
                                hasChildConstraint = True
                        if not hasChildConstraint:
                            self.layout.operator("create.constraint_bone", text = 'Create Constraint Bone')

            action = utils.getCurrentAction()
            if(action != None):
                c.prop(action, "AnimationEndFrame")


        bone = bpy.context.active_bone
        if type(bone) != type(None):
            if(type(bpy.context.active_bone ) is bpy.types.EditBone):
                c.prop(bone.billboardMode, "billboardMode")
                c.prop(bone, "Visible")
                c.prop(bone, "EnableProxy")
                if bone.EnableProxy:
                    c.prop(bone, "proxyIsHidden")
                    c.prop(bone, "altDecreaseStayHidden")
                    c.prop(bone, "ProxyName")

            elif (type(bpy.context.active_bone) is bpy.types.Bone and bpy.context.mode == 'POSE'):
                poseBone = object.pose.bones[bone.name]
                c.prop(poseBone, "proxyIsHiddenAnimation")

class ALAMO_PT_materialPropertyPanel(bpy.types.Panel):
    bl_label = "Alamo material properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    def draw(self, context):
        object = context.object
        layout = self.layout
        c = layout.column()

        if type(object) != type(None):
            if(object.type == 'MESH'):
                material = bpy.context.active_object.active_material
                if (material != None):
                    #a None image is needed to represent not using a texture
                    if 'None' not in bpy.data.images:
                        bpy.data.images.new(name='None', width=1, height=1)
                    c.prop(material.shaderList, "shaderList")
                    shaderProps = settings.material_parameter_dict[material.shaderList.shaderList]
                    if material.shaderList.shaderList != 'alDefault.fx':
                        for property in shaderProps:
                            if property == 'BaseTexture':
                                layout.prop_search(material, "BaseTexture", bpy.data, "images")
                            elif property == 'CloudTexture':
                                layout.prop_search(material, "CloudTexture", bpy.data, "images")
                            elif property == 'DetailTexture':
                                layout.prop_search(material, "DetailTexture", bpy.data, "images")
                            elif property == 'CloudNormalTexture':
                                layout.prop_search(material, "CloudNormalTexture", bpy.data, "images")
                            elif property == 'NormalTexture':
                                layout.prop_search(material, "NormalTexture", bpy.data, "images")
                            elif property == 'NormalDetailTexture':
                                layout.prop_search(material, "NormalDetailTexture", bpy.data, "images")
                            elif property == 'GlossTexture':
                                layout.prop_search(material, "GlossTexture", bpy.data, "images")
                            elif property == 'WaveTexture':
                                layout.prop_search(material, "WaveTexture", bpy.data, "images")
                            elif property == 'DistortionTexture':
                                layout.prop_search(material, "DistortionTexture", bpy.data, "images")
                            else:
                                c.prop(material, property)

class shaderListProperties(bpy.types.PropertyGroup):
    mode_options = [
        ("alDefault.fx",  "alDefault.fx", '', '', 1),
        ("BatchMeshAlpha.fx", "BatchMeshAlpha.fx", '', '', 2),
        ("BatchMeshGloss.fx", "BatchMeshGloss.fx", '', '', 3),
        ("Grass.fx", "Grass.fx", '', '', 4),
        ("MeshAdditive.fx", "MeshAdditive.fx", '', '', 5),
        ("MeshAlpha.fx", "MeshAlpha.fx", '', '', 6),
        ("MeshAlphaScroll.fx", "MeshAlphaScroll.fx", '', '', 7),
        ("MeshBumpColorize.fx", "MeshBumpColorize.fx", '', '', 8),
        ("MeshBumpColorizeVertex.fx", "MeshBumpColorizeVertex.fx", '', '', 28),
        ("MeshBumpColorizeDetail.fx", "MeshBumpColorizeDetail.fx", '', '', 29),
        ("MeshBumpLight.fx", "MeshBumpLight.fx", '', '', 26),
        ("MeshCollision.fx", "MeshCollision.fx", '', '', 9),
        ("MeshGloss.fx", "MeshGloss.fx", '', '', 10),
        ("MeshGlossColorize.fx", "MeshGlossColorize.fx", '', '', 11),
        ("MeshShadowVolume.fx", "MeshShadowVolume.fx", '', '', 12),
        ("MeshShield.fx", "MeshShield.fx", '', '', 13),
        ("Nebula.fx", "Nebula.fx", '', '', 14),
        ("Planet.fx", "Planet.fx", '', '', 15),
        ("RSkinAdditive.fx", "RSkinAdditive.fx", '', '', 16),
        ("RSkinAlpha.fx", "RSkinAlpha.fx", '', '', 17),
        ("RSkinBumpColorize.fx", "RSkinBumpColorize.fx", '', '', 18),
        ("RSkinGloss.fx", "RSkinGloss.fx", '', '', 19),
        ("RSkinGlossColorize.fx", "RSkinGlossColorize.fx", '', '', 20),
        ("RSkinShadowVolume.fx", "RSkinShadowVolume.fx", '', '', 21),
        ("Skydome.fx", "Skydome.fx", '', '', 22),
        ("TerrainMeshBump.fx", "TerrainMeshBump.fx", '', '', 23),
        ("TerrainMeshGloss.fx", "TerrainMeshGloss.fx", '', '', 24),
        ("Tree.fx", "Tree.fx", '', '', 25),
        ("LightProxy.fx", "LightProxy.fx", '', '', 27)
    ]

    shaderList : bpy.props.EnumProperty(
        items=mode_options,
        description="Choose ingame Shader",
        default="alDefault.fx",
    )

class billboardListProperties(bpy.types.PropertyGroup):
    mode_options = [
        ("Disable", "Disable", 'Description WIP', '', 0),
        ("Parallel", "Parallel", 'Description WIP', '', 1),
        ("Face", "Face", 'Description WIP', '', 2),
        ("ZAxis View", "ZAxis View", 'Description WIP', '', 3),
        ("ZAxis Light", "ZAxis Light", 'Description WIP', '', 4),
        ("ZAxis Wind", "ZAxis Wind", 'Description WIP', '', 5),
        ("Sunlight Glow", "Sunlight Glow", 'Description WIP', '', 6),
        ("Sun", "Sun", 'Description WIP', '', 7),
    ]

    billboardMode : bpy.props.EnumProperty(
        items = mode_options,
        description = "billboardMode",
        default="Disable",
    )

def proxy_name_update(self, context):
    if self.ProxyName != self.ProxyName.upper():    #prevents endless recursion
        self.ProxyName = self.ProxyName.upper()

#blender registration
def menu_func_import(self, context):
    self.layout.operator(import_alo.ALO_Importer.bl_idname, text=".ALO Importer")
    self.layout.operator(import_ala.ALA_Importer.bl_idname, text=".ALA Importer")

def menu_func_export(self, context):
    self.layout.operator(export_alo.ALO_Exporter.bl_idname, text=".ALO Exporter")
    self.layout.operator(export_ala.ALA_Exporter.bl_idname, text=".ALA Exporter")

from . import_alo import ALO_Importer
from . import_ala import ALA_Importer
from . export_alo import ALO_Exporter
from . export_ala import ALA_Exporter

classes = (
    skeletonEnumClass,
    billboardListProperties,
    shaderListProperties,
    ALO_Importer,
    ALA_Importer,
    ALO_Exporter,
    ALA_Exporter,
    ALAMO_PT_materialPropertyPanel,
    createConstraintBoneButton,
    ALAMO_PT_ToolsPanel
)

def register():

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    bpy.types.Scene.ActiveSkeleton = PointerProperty(type=skeletonEnumClass)
    bpy.types.Scene.modelFileName  = StringProperty(name="")

    bpy.types.Action.AnimationEndFrame = IntProperty(default = 24)

    bpy.types.EditBone.Visible = BoolProperty(default=True)
    bpy.types.EditBone.EnableProxy = BoolProperty()
    bpy.types.EditBone.proxyIsHidden = BoolProperty()
    bpy.types.PoseBone.proxyIsHiddenAnimation = BoolProperty()
    bpy.types.EditBone.altDecreaseStayHidden = BoolProperty()
    bpy.types.EditBone.ProxyName = StringProperty(update=proxy_name_update)
    bpy.types.EditBone.billboardMode = bpy.props.PointerProperty(type=billboardListProperties)

    bpy.types.Object.HasCollision = BoolProperty()
    bpy.types.Object.Hidden = BoolProperty()

    bpy.types.Material.BaseTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.DetailTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.NormalDetailTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.NormalTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.GlossTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.WaveTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.DistortionTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.CloudTexture = bpy.props.StringProperty(default='None')
    bpy.types.Material.CloudNormalTexture = bpy.props.StringProperty(default='None')

    bpy.types.Material.shaderList = bpy.props.PointerProperty(type=shaderListProperties)
    bpy.types.Material.Emissive = bpy.props.FloatVectorProperty(min = 0, max = 1, size = 4, default=(0,0,0,0))
    bpy.types.Material.Diffuse = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(1,1,1,0))
    bpy.types.Material.Specular = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(1,1,1,0))
    bpy.types.Material.Shininess = bpy.props.FloatProperty(min=0, max=255, default = 32)
    bpy.types.Material.Colorization = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(1,1,1,0))
    bpy.types.Material.DebugColor = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(0,1,0,0))
    bpy.types.Material.UVOffset = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(0,0,0,0))
    bpy.types.Material.Color = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(1,1,1,1))
    bpy.types.Material.UVScrollRate = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(0,0,0,0))
    bpy.types.Material.DiffuseColor = bpy.props.FloatVectorProperty(min=0, max=1, size=3, default=(0.5,0.5,0.5))
    #shield shader properties
    bpy.types.Material.EdgeBrightness = bpy.props.FloatProperty(min=0, max=255, default=0.5)
    bpy.types.Material.BaseUVScale = bpy.props.FloatProperty(min=-255, max=255, default=1)
    bpy.types.Material.WaveUVScale = bpy.props.FloatProperty(min=-255, max=255, default=1)
    bpy.types.Material.DistortUVScale = bpy.props.FloatProperty(min=-255, max=255, default=1)
    bpy.types.Material.BaseUVScrollRate = bpy.props.FloatProperty(min=-255, max=255, default=-0.15)
    bpy.types.Material.WaveUVScrollRate = bpy.props.FloatProperty(min=-255, max=255, default=-0.15)
    bpy.types.Material.DistortUVScrollRate = bpy.props.FloatProperty(min=-255, max=255, default=-0.25)
    #tree properties
    bpy.types.Material.BendScale = bpy.props.FloatProperty(min=-255, max=255, default=0.4)
    #grass properties
    bpy.types.Material.Diffuse1 = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(1,1,1,1))
    #skydome.fx properties
    bpy.types.Material.CloudScrollRate = bpy.props.FloatProperty(min=-255, max=255, default=0.001)
    bpy.types.Material.CloudScale = bpy.props.FloatProperty(min=-255, max=255, default=1)
    #nebula.fx properties
    bpy.types.Material.SFreq = bpy.props.FloatProperty(min=-255, max=255, default=0.002)
    bpy.types.Material.TFreq = bpy.props.FloatProperty(min=-255, max=255, default=0.005)
    bpy.types.Material.DistortionScale = bpy.props.FloatProperty(min=-255, max=255, default=1)
    #planet.fx properties
    bpy.types.Material.Atmosphere = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(0.5, 0.5, 0.5, 0.5))
    bpy.types.Material.CityColor = bpy.props.FloatVectorProperty(min=0, max=1, size=4, default=(0.5, 0.5, 0.5, 0.5))
    bpy.types.Material.AtmospherePower = bpy.props.FloatProperty(min=-255, max=255, default=1)
    #tryplanar mapping properties
    bpy.types.Material.MappingScale = bpy.props.FloatProperty(min=0, max=255, default=0.1)
    bpy.types.Material.BlendSharpness = bpy.props.FloatProperty(min=0, max=255, default=0.1)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    bpy.types.Scene.ActiveSkeleton

    bpy.types.Action.AnimationEndFrame

    bpy.types.EditBone.Visible
    bpy.types.EditBone.EnableProxy
    bpy.types.EditBone.proxyIsHidden
    bpy.types.PoseBone.proxyIsHiddenAnimation
    bpy.types.EditBone.altDecreaseStayHidden
    bpy.types.EditBone.ProxyName
    bpy.types.EditBone.billboardMode

    bpy.types.Object.HasCollision
    bpy.types.Object.Hidden

    bpy.types.Material.BaseTexture
    bpy.types.Material.DetailTexture
    bpy.types.Material.NormalTexture
    bpy.types.Material.NormalDetailTexture
    bpy.types.Material.GlossTexture
    bpy.types.Material.WaveTexture
    bpy.types.Material.DistortionTexture
    bpy.types.Material.CloudTexture
    bpy.types.Material.CloudNormalTexture

    bpy.types.Material.shaderList
    bpy.types.Material.Emissive
    bpy.types.Material.Diffuse
    bpy.types.Material.Specular
    bpy.types.Material.Shininess
    bpy.types.Material.Colorization
    bpy.types.Material.DebugColor
    bpy.types.Material.UVOffset
    bpy.types.Material.Color
    bpy.types.Material.UVScrollRate
    bpy.types.Material.DiffuseColor
    # shield shader properties
    bpy.types.Material.EdgeBrightness
    bpy.types.Material.BaseUVScale
    bpy.types.Material.WaveUVScale
    bpy.types.Material.DistortUVScale
    bpy.types.Material.BaseUVScrollRate
    bpy.types.Material.WaveUVScrollRate
    bpy.types.Material.DistortUVScrollRate
    # tree properties
    bpy.types.Material.BendScale
    # grass properties
    bpy.types.Material.Diffuse1
    # skydome.fx properties
    bpy.types.Material.CloudScrollRate
    bpy.types.Material.CloudScale
    # nebula.fx properties
    bpy.types.Material.SFreq
    bpy.types.Material.TFreq
    bpy.types.Material.DistortionScale
    # planet.fx properties
    bpy.types.Material.Atmosphere
    bpy.types.Material.CityColor
    bpy.types.Material.AtmospherePower
    #tryplanar mapping properties
    bpy.types.Material.MappingScale
    bpy.types.Material.BlendSharpness

if __name__ == "__main__":
    register()
