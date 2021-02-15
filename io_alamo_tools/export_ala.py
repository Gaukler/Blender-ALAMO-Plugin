import bpy
from . import settings, utils

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
import struct
import mathutils
import math
from math import pi
from mathutils import Vector
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
import sys
import os
import bmesh

def chunk_size(size):
            #high bit is used to determine if a chunk holds chunks or data
            #add 2147483648 instead of binary operation
            return size+2147483648

def calculateTranslationScale(bone, translationOffset, armature, translationList):
    scene = bpy.context.scene  # current scene
    # check for every bone if it has translation data
    if (bone.name in translationList):
        scene.frame_set(0)
        pose = armature.pose.bones[bone.name]  # get the pose bone
        # search for maximum translation
        maxX = 0
        maxY = 0
        maxZ = 0

        action = utils.getCurrentAction()
        animLength = action.AnimationEndFrame

        while (scene.frame_current <= animLength):  # iterate over every frame
            if pose.parent != None:
                translation_relative = (pose.parent.matrix.inverted() @ pose.matrix).decompose()[0]
            else:
                translation_relative = pose.matrix.decompose()[0]

            if (abs(translation_relative[0] - translationOffset[0]) > maxX):
                maxX = abs(translation_relative[0] - translationOffset[0])
            if (abs(translation_relative[1] - translationOffset[1]) > maxY):
                maxY = abs(translation_relative[1] - translationOffset[1])
            if (abs(translation_relative[2] - translationOffset[2]) > maxZ):
                maxZ = abs(translation_relative[2] - translationOffset[2])
            scene.frame_set(scene.frame_current + 1)
        scene.frame_set(0)

        if (maxX == 0):
            maxX = 1
        if (maxY == 0):
            maxY = 1
        if (maxZ == 0):
            maxZ = 1

        scaleX = maxX / 65535.0
        scaleY = maxY / 65535.0
        scaleZ = maxZ / 65535.0

        translationScale = (scaleX, scaleY, scaleZ)

        global translationScaleDict
        translationScaleDict[bone.name] = translationScale

        return mathutils.Vector(translationScale)
    else:
        return mathutils.Vector((0, 0, 0))

def calculateTranslationOffset(bone, armature, translationList):
    scene = bpy.context.scene  # current scene
    # check for every bone if it has translation data
    pose = armature.pose.bones[bone.name]

    # if the bone has no animated translation data the offset is the relative translation data at an arbitrary frame, first frame is used
    # if the bone has animated translation data, the offset is the minimum of every translation
    # this is necessary because the translation data is stored as unsigned shorts, so every relative motion has to be positive

    if (bone.name in translationList):
        scene.frame_set(0)
        minX = 65535
        minY = 65535
        minZ = 65535

        action = utils.getCurrentAction()
        animLength = action.AnimationEndFrame

        while (scene.frame_current <= animLength):  # iterate over every frame
            if pose.parent != None:
                translation_relative = (pose.parent.matrix.inverted() @ pose.matrix).decompose()[0]
            else:
                translation_relative = pose.matrix.decompose()[0]
            if (translation_relative[0] < minX):
                minX = translation_relative[0]
            if (translation_relative[1] < minY):
                minY = translation_relative[1]
            if (translation_relative[2] < minZ):
                minZ = translation_relative[2]
            scene.frame_set(scene.frame_current + 1)
        scene.frame_set(0)

        return mathutils.Vector((minX, minY, minZ))
    else:
        if pose.parent != None:
            return (pose.parent.matrix.inverted() @ pose.matrix).decompose()[0]
        else:
            return pose.matrix.decompose()[0]

def create_translation_data(translationList, armature):
    scene = bpy.context.scene
    scene.frame_set(0)
    chunk = b''

    action = utils.getCurrentAction()
    animLength = action.AnimationEndFrame

    while (scene.frame_current <= animLength):
        for name in translationList:
            bone = armature.data.bones[name]
            pose = armature.pose.bones[bone.name]
            if pose.parent != None:
                translation_relative = (pose.parent.matrix.inverted() @ pose.matrix).decompose()[0]
            else:
                translation_relative = pose.matrix.decompose()[0]

            chunk += struct.pack("<H", int((translation_relative[0] - translationOffsetDict[pose.name][0]) / translationScaleDict[bone.name][0]))
            chunk += struct.pack("<H", int((translation_relative[1] - translationOffsetDict[pose.name][1]) / translationScaleDict[bone.name][1]))
            chunk += struct.pack("<H", int((translation_relative[2] - translationOffsetDict[pose.name][2]) / translationScaleDict[bone.name][2]))

        scene.frame_set(scene.frame_current + 1)
    scene.frame_set(0)

    chunk_header = (b'\x0a\x10\x00\00')  # chunk header
    chunk_header += struct.pack("<I", len(chunk))  # chunk size
    if len(chunk) == 0:
        return b''
    return chunk_header + chunk

def create_rotation_data(rotationList, armature):
    chunk = (b'')
    scene = bpy.context.scene
    scene.frame_set(0)

    action = utils.getCurrentAction()
    animLength = action.AnimationEndFrame

    while (scene.frame_current <= animLength):
        for name in rotationList:
            bone = armature.data.bones[name]

            pose = armature.pose.bones[bone.name]
            if pose.parent == None:
                rotation_relative = pose.matrix.decompose()[1]
            else:
                rotation_relative = (pose.parent.matrix.inverted() @ pose.matrix).decompose()[1]
            chunk += struct.pack("<h", int(round(rotation_relative[1] * 32767)))
            chunk += struct.pack("<h", int(round(rotation_relative[2] * 32767)))
            chunk += struct.pack("<h", int(round(rotation_relative[3] * 32767)))
            chunk += struct.pack("<h", int(round(rotation_relative[0] * 32767)))
        scene.frame_set(scene.frame_current + 1)
    scene.frame_set(0)

    chunk_header = (b"\x09\x10\x00\00")  # chunk header
    chunk_header += struct.pack("<I", len(chunk))  # chunk size
    if len(chunk) == 0:
        return b''
    return chunk_header + chunk

def create_animation():

    chunk = b''
    # get armature name
    armature = utils.findArmature()
    if armature == None:
        print("Warning: No armature found!")
        return b''

    chunk += create_anim_info_chunk(armature)

    rotationList = []
    translationList = []

    if armature.animation_data == None:
        return b''

    # iterate over every pose bone
    for pose in armature.pose.bones:
        # iterate over every fcurves data (keyframes)
        for curve in armature.animation_data.action.fcurves:
            # by spliting and comparing the data path we know which bone has rotation/location keyframes
            if curve.data_path.split('"')[1] == pose.name and curve.data_path.split('"')[2] == '].location':
                if (not (pose.name in translationList)): translationList.append(pose.name)  # if list doesnt contaion bone name add it
            if curve.data_path.split('"')[1] == pose.name and curve.data_path.split('"')[2] in settings.rotation_curve_name:
                if (not (pose.name in rotationList)):
                    rotationList.append(pose.name)  # if list doesnt contaion bone name add it

    bpy.context.scene.frame_set(0)  # set scene to first frame, needed for default rotation/translation
    # add the bone data chunks for every bone
    for bone in armature.data.bones:
        if (bone.name != "Root"):
            chunk += create_bone_data(bone, translationList, rotationList, armature)

    chunk += create_translation_data(translationList, armature)  # add translation data chunk
    chunk += create_rotation_data(rotationList, armature)  # add rotation data chunk

    header = (b"\x00\x10\x00\00")
    header += struct.pack("<I", chunk_size(len(chunk))) # chunk size

    return header + chunk

def create_anim_info_chunk(armature):

    action = utils.getCurrentAction()
    animLength = action.AnimationEndFrame

    chunk = b'\x01\x04'  # mini chunk name and length
    chunk += struct.pack("<I", animLength + 1)  # number of animation frames

    chunk += b'\x02\x04'  # mini chunk length
    chunk += struct.pack("<f", bpy.context.scene.render.fps)

    chunk += b'\x03\x04'  # mini chunk length
    chunk += struct.pack("<I", len(
        armature.data.bones))  # add number of bones

    locationTracks = 0  # number of bones with location keyframes
    rotationTracks = 0  # number of bones with rotation keyframes
    # calculate location and rotation block sizes
    # iterate over every pose bone
    for pose in armature.pose.bones:  # iterate over every bone
        if armature.animation_data == None:
            raise RuntimeError('Warning: no animation data found')
        # iterate over every fcurves data (keyframes)
        for curve in armature.animation_data.action.fcurves:
            # by spliting and comparing the data path we know which bone has rotation/location keyframes
            if curve.data_path.split('"')[1] == pose.name and curve.data_path.split('"')[2] == '].location':
                locationTracks += 1
            if curve.data_path.split('"')[1] == pose.name and curve.data_path.split('"')[
                2] == '].rotation_quaternion':
                rotationTracks += 1

    # add rotationBlockSize
    chunk += b'\x0b\x04'  # mini chunk name and length
    chunk += struct.pack("<I", rotationTracks)

    # add translationBlockSize
    chunk += b'\x0c\x04'  # mini chunk name and length
    chunk += struct.pack("<I", locationTracks)

    # addScaleBlockSize, scale not supported set to 0
    chunk += b'\x0d\x04'  # mini chunk name and length
    chunk += struct.pack("<I", 0)

    chunkHeader = (b"\x01\x10\x00\00")  # chunk header
    chunkHeader += struct.pack("<I", len(chunk))  # add length

    return chunkHeader + chunk

def create_bone_data(bone, translationList, rotationList, armature):
    chunk = create_bone_animation_info_chunk(bone, translationList, rotationList, armature)
    header = (b"\x02\x10\x00\00")
    header += struct.pack("<I", chunk_size(len(chunk))) # add length
    return header + chunk
    # add support for step key track

def create_bone_animation_info_chunk(bone, translationList, rotationList, armature):

    # for animation data we have to go into pose mode
    utils.setModeToObject()

    # select the skeleton
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')  # enter pose mode
    pose = armature.pose.bones[bone.name]

    scene = bpy.context.scene
    scene.frame_set(0)
    translationOffset = calculateTranslationOffset(bone, armature, translationList)
    global translationOffsetDict
    translationOffsetDict[bone.name] = translationOffset
    translationScale = calculateTranslationScale(bone, translationOffset, armature, translationList)

    # default rotation is rotation of first frame
    if pose.parent != None:
        default_rotation = (pose.parent.matrix.inverted() @ pose.matrix).decompose()[1]
    else:
        default_rotation = pose.matrix.decompose()[1]

    chunk = b'\x04'  # mini chunk name
    name = utils.clean_name(bone.name)
    chunk += struct.pack("<B", (len(name) + 1))  # size of name
    chunk += bytes(name, 'utf-8') + b"\x00"  # add bone name

    chunk += b'\x05\x04'  # mini chunk name and length

    # get the index of the current bone
    counter = 1 #start at because we ignore root bone
    for b in armature.data.bones:
        if (bone.name == b.name):
            index = counter
            break
        counter += 1
    chunk += struct.pack("<i", index)  # index of bone

    chunk += b'\x0a\x04'  # mini chunk name and length
    chunk += b'\x00\x00\00\00'  # unknown chunk

    chunk += b'\x06\x0c'  # mini chunk name and length
    # translation offset, is the location at the first frame, relative to the parent
    chunk += struct.pack("<f", translationOffset[0])
    chunk += struct.pack("<f", translationOffset[1])
    chunk += struct.pack("<f", translationOffset[2])

    chunk += b'\x07\x0c'  # mini chunk name and length
    # translation scale
    chunk += struct.pack("<f", translationScale[0])
    chunk += struct.pack("<f", translationScale[1])
    chunk += struct.pack("<f", translationScale[2])

    chunk += b'\x08\x0c'  # mini chunk name and length
    # scale offset, just 1 for now
    chunk += struct.pack("<f", 1)
    chunk += struct.pack("<f", 1)
    chunk += struct.pack("<f", 1)

    chunk += b'\x09\x0c'  # mini chunk name and length
    # scale scale, just 1 for now
    chunk += struct.pack("<f", 1)
    chunk += struct.pack("<f", 1)
    chunk += struct.pack("<f", 1)

    # add translation index
    chunk += b'\x0e\x02'  # mini chunk name and length
    if (bone.name in translationList):
        translationIndex = translationList.index(bone.name) * 3  # if bone is in location list use index in list as index
    else:
        translationIndex = -1  # if bone is not in location list use -1
    chunk += struct.pack("<h", translationIndex)

    # add scale index
    chunk += b'\x0f\x02'  # mini chunk name and length
    chunk += struct.pack("<h", -1)  # scale index, scale not implemented

    # add rotation index
    chunk += b'\x10\x02'  # mini chunk name and length
    if (bone.name in rotationList):
        rotationIndex = 4 * rotationList.index(
            bone.name)  # if bone is in rotation list use index in list as index
    else:
        rotationIndex = -1  # if bone is not in rotation list use -1

    chunk += struct.pack("<h", rotationIndex)

    # add default rotation
    chunk += b'\x11\x08'  # mini chunk name and length

    chunk += struct.pack("<h", int(default_rotation[1] * 32767))
    chunk += struct.pack("<h", int(default_rotation[2] * 32767))
    chunk += struct.pack("<h", int(default_rotation[3] * 32767))
    chunk += struct.pack("<h", int(default_rotation[0] * 32767))

    header = (b"\x03\x10\x00\00")
    header += struct.pack("<I", len(chunk))  # add length

    chunk = header + chunk

    visibility_chunk = create_visibility_chunk(armature, bone)

    return chunk + visibility_chunk

def create_visibility_chunk(armature, bone):
    dataExists = False
    for curve in armature.animation_data.action.fcurves:
        # by spliting and comparing the data path we know which bone has rotation/location keyframes
        parts = curve.data_path.split('"');
        if (parts[2] == '].proxyIsHiddenAnimation'):
            if parts[1] == bone.name or (bone.parent != None and bone.parent.name == parts[1]):
                dataExists = True
                break

    if not dataExists:
        return b''

    scene = bpy.context.scene
    binary = ''

    pose = armature.pose.bones[bone.name]
    
    parentPose = {}
    if bone.parent != None:
        parentPose = armature.pose.bones[bone.parent.name]
    else:
        parentPose = None

    action = utils.getCurrentAction()
    animLength = action.AnimationEndFrame

    scene.frame_set(0)
    while scene.frame_current <= animLength:
        if pose.proxyIsHiddenAnimation == True or (parentPose != None and parentPose.proxyIsHiddenAnimation):
            binary += '0'
        else:
            binary += '1'
        scene.frame_set(scene.frame_current + 1)
    scene.frame_set(0)

    while len(binary)%8 != 0:
        binary += '0'

    chunk = b''

    while len(binary) > 1:
        binaryReverse = binary[0:8][::-1] #file is little endian, reverse byte
        int_value = int(binaryReverse, 2)
        chunk += struct.pack('<B', int_value)
        binary = binary[8:]
    print()
    chunkHeader = b'\x07\x10\x00\00'
    chunkHeader += struct.pack('<I', len(chunk))
    return chunkHeader + chunk

class AnimationExporter():

    def exportAnimation(self, path):
        file = open(path, 'wb')  # open file in read binary mode

        global translationOffsetDict
        translationOffsetDict = {}
        global translationScaleDict
        translationScaleDict = {}
        file.write(create_animation())
        file.close()
        file = None

class ALA_Exporter(bpy.types.Operator):

    """ALA Exporter"""  # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "export.ala"  # unique identifier for buttons and menu items to reference.
    bl_label = "Export ALA File"  # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # enable undo for the operator.
    bl_info = {
        "name": "ALA Exporter",
        "category": "Export",
    }
    filename_ext = ".ala"
    filter_glob : StringProperty(default="*.ala", options={'HIDDEN'})

    filepath : StringProperty(name="File Path", description="Filepath used for exporting the ALO file", maxlen=1024,
                              default="")


    def execute(self, context):

        path = self.properties.filepath

        exporter = AnimationExporter()
        exporter.exportAnimation(path)

        return {'FINISHED'}  # this lets blender know the operator finished successfully.

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
