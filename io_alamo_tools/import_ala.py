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
import binascii

class animation_data():
        def __init__(self):

            self.num_frames = 0
            self.fps = 0
            self.num_bones = 0

            self.bone_name_list = []
            self.bone_index = []

            self.translation_offset = []
            self.translation_index = []
            self.translation_data = []
            self.translation_block_size = 0
            self.translation_scale = []
            self.translation_data = []

            self.scaleIndex = []
            self.scale_offset = []

            self.rotation_index = []
            self.default_rotation = []
            self.rotation_block_size = 0
            self.rotation_data = []

            self.visibilityAnimation = []
            self.visibilityDict = {}

def read_length(file):
    #the hight bit is used to tell if chunk holds data or chunks, so if it is set it has to be ignored when calculating length
    length = struct.unpack("<I", file.read(4))[0]
    if length >= 2147483648:
        length -= 2147483648
    return length

def read_visibility_data(data, bone_Name):
    length = struct.unpack("<I",file.read(4))[0]

    bytes = file.read(length)
    string = str(binascii.hexlify(bytes))[2:-1]

    string = string.replace('x', '').replace('b', '').replace('\\', '').replace('\'', '')#.replace('<', '')
    binary = ''
    counter = 0

    while counter < len(string):
        slice = string[counter:counter+1]
        slice += string[counter+1:counter+2]
        binary_part = bin(int(slice, 16))[2:].zfill(8)
        binaryReverse = binary_part[::-1] #file is little endian, reverse byte
        binary += binaryReverse
        counter += 2

    if bone_Name in data.visibilityDict:
        bone_Name += ".001"
        counter = 2
        while bone_Name in visibilityDict:
            if counter < 10:
                bone_Name = bone_Name[0:len(bone_Name)-4] + ".00" + str(counter)
            elif counter < 100:
                bone_Name = bone_Name[0:len(bone_Name)-4] +".0" + str(counter)
            else:
                bone_Name = bone_Name[0:len(bone_Name)-4] + "." + str(counter)
            counter += 1
    data.visibilityDict[bone_Name] = binary

def read_translation_data(data):
    counter_limit = data.num_frames * data.translation_block_size * 3
    counter = 0
    while (counter < counter_limit):
        vector = mathutils.Vector((0, 0, 0))
        vector[0] = utils.read_u_short(file.read(2))
        vector[1] = utils.read_u_short(file.read(2))
        vector[2] = utils.read_u_short(file.read(2))
        data.translation_data.append(vector)
        counter += 3

def read_rotation_data(data):
    counter_limit = data.num_frames * data.rotation_block_size * 4
    counter = 0
    while (counter < counter_limit):
        q = mathutils.Quaternion()
        q[1] = utils.read_short(file.read(2))
        q[2] = utils.read_short(file.read(2))
        q[3] = utils.read_short(file.read(2))
        q[0] = utils.read_short(file.read(2))

        for i in range(4):
            q[i] = q[i] / 32767.0

        data.rotation_data.append(q)
        counter += 4

def read_next_chunk(path):
    data = animation_data()
    while(file.tell() < os.path.getsize(path)):
        active_chunk = file.read(4)
        if active_chunk == b"\x00\x10\x00\00":
            file.seek(4, 1)  # skip size
        elif active_chunk == b"\x01\x10\x00\00":
            if(struct.unpack("<I", file.read(4))[0] != 36):
                raise("Base EaW animation format not supported, use converter")
            read_animation_information(data);
        elif active_chunk == b"\x02\x10\x00\00":
            file.seek(4, 1)  # skip size
        elif active_chunk == b"\x03\x10\x00\00":
            length = read_length(file)
            global end_position
            end_position = file.tell() + length
            read_bone_animation_info(data);
        elif active_chunk == b"\x0A\x10\x00\00":
            file.seek(4, 1)  # skip size
            read_translation_data(data)
        elif active_chunk == b"\x09\x10\x00\00":
            file.seek(4, 1)  # skip size
            read_rotation_data(data)
    return data

def read_animation_information(data):
    file.seek(2, 1)  # skip mini chunk and size
    data.num_frames = utils.read_int(file.read(4))
    file.seek(2, 1)  # skip mini chunk and size
    data.fps = utils.read_float(file.read(4))
    file.seek(2, 1)  # skip mini chunk and size
    data.num_bones = utils.read_int(file.read(4))
    file.seek(2, 1)  # skip mini chunk and size
    data.rotation_block_size = int(utils.read_int(file.read(4)) / 4)
    file.seek(2, 1)  # skip mini chunk and size
    data.translation_block_size = int(utils.read_int(file.read(4)) / 3)
    file.seek(2, 1)  # skip mini chunk and size
    data.scale_block_size = utils.read_int(file.read(4))

def read_bone_name(data):
    bytes = file.read(1) + bytearray(3)
    length = struct.unpack("<I", bytes)[0]  # get string length
    boneName = ""
    counter = 0
    while counter < length - 1:
        letter = str(file.read(1))
        letter = letter[2:len(letter) - 1]
        boneName += letter
        counter += 1
    file.seek(1, 1)  # skip end byte of name
    if boneName in data.visibilityDict:
        boneName += ".001"
        counter = 2
        while boneName in data.visibilityDict:
            if counter < 10:
                boneName = boneName[0:len(boneName)-4] + ".00" + str(counter)
            elif counter < 100:
                boneName = boneName[0:len(boneName)-4] +".0" + str(counter)
            else:
                boneName = boneName[0:len(boneName)-4] + "." + str(counter)
            counter += 1
    return boneName

def read_bone_animation_info(data):
    bone_Name = None
    while file.tell()<end_position:
        active_child_chunk = file.read(1)
        if active_child_chunk == b"\04":
            bone_Name = read_bone_name(data)
            data.bone_name_list.append(bone_Name)
            continue
        elif active_child_chunk == b"\05":
            file.seek(1, 1)  # skip mini chunk size
            data.bone_index.append(utils.read_int(file.read(4)))
            continue
        elif active_child_chunk == b"\06":
            file.seek(1, 1)  # skip mini chunk size
            vector = mathutils.Vector((0, 0, 0))
            vector[0] = utils.read_float(file.read(4))
            vector[1] = utils.read_float(file.read(4))
            vector[2] = utils.read_float(file.read(4))
            data.translation_offset.append(vector)
            continue
        elif active_child_chunk == b"\07":
            file.seek(1, 1)  # skip mini chunk size
            vector = mathutils.Vector((0, 0, 0))
            vector[0] = utils.read_float(file.read(4))
            vector[1] = utils.read_float(file.read(4))
            vector[2] = utils.read_float(file.read(4))
            data.translation_scale.append(vector)
            continue
        elif active_child_chunk == b'\08':
            file.seek(1, 1)  # skip mini chunk size
            scale_offset = []
            scale_offset.append(struct.unpack("<f", file.read(4))[0])
            scale_offset.append(struct.unpack("<f", file.read(4))[0])
            scale_offset.append(struct.unpack("<f", file.read(4))[0])
            continue
        elif active_child_chunk == b'\n':
            bytes = file.read(1) + bytearray(3)
            length = struct.unpack("<I", bytes)[0]  # get string length
            file.seek(length,1)
            continue
        elif active_child_chunk == b'\010':
            file.seek(1, 1)  # skip mini chunk size
            scale_offset = []
            scale_offset.append(struct.unpack("<f", file.read(4))[0])
            scale_offset.append(struct.unpack("<f", file.read(4))[0])
            scale_offset.append(struct.unpack("<f", file.read(4))[0])
            continue
        elif active_child_chunk == b"\t":
            file.seek(1, 1)  # skip mini chunk size
            scale_scale = []
            scale_scale.append(struct.unpack("<f", file.read(4))[0])
            scale_scale.append(struct.unpack("<f", file.read(4))[0])
            scale_scale.append(struct.unpack("<f", file.read(4))[0])
            continue
        elif active_child_chunk == b"\016":
            file.seek(1, 1)  # skip mini chunk size
            index = utils.read_short(file.read(2))
            data.translation_index.append(index)
            if index != -1:
                index = int(index / 3)
            continue
        elif active_child_chunk == b"\017":
            file.seek(1, 1)  # skip mini chunk size
            scaleIndex = []
            scaleIndex.append(utils.read_short(file.read(2)))
            continue
        elif active_child_chunk == b"\020":
            file.seek(1, 1)  # skip mini chunk and size
            index = utils.read_short(file.read(2))
            if index != -1:
                index = int(index / 4)
            data.rotation_index.append(index)
            continue
        elif active_child_chunk == b"\021":
            file.seek(1, 1)  # skip mini chunk and size
            q = mathutils.Quaternion()
            q[1] = utils.read_short(file.read(2))
            q[2] = utils.read_short(file.read(2))
            q[3] = utils.read_short(file.read(2))
            q[0] = utils.read_short(file.read(2))

            for i in range(4):
                q[i] = q[i] / 32767.0

            data.default_rotation.append(q)
            continue

    chunk = file.read(4)
    if chunk == b"\x07\x10\x00\00":
        read_visibility_data(data, bone_Name)
    else:
        file.seek(-4,1)

def create_animation(data):
    action = utils.getCurrentAction()
    action.AnimationEndFrame = data.num_frames-1
    action.use_fake_user = True

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = data.num_frames-1
    scene.render.fps = data.fps
    scene.frame_set(0)

    utils.setModeToObject()

    armature = utils.findArmature()
    armature.select_set(True)  # select the skeleton
    bpy.context.view_layer.objects.active = armature

    bpy.ops.object.mode_set(mode='POSE')  # enter pose mode

    bpy.ops.pose.rot_clear()
    bpy.ops.pose.scale_clear()
    bpy.ops.pose.transforms_clear()

    fps_counter = 0 #initialize fps_counter, coresponds to current animation frame

    while fps_counter < data.num_frames:
        bone_counter = 0
        while bone_counter < data.num_bones:
            #unpack data
            if data.rotation_index[bone_counter] != -1:
                rotation_unpacked = data.rotation_data[fps_counter * data.rotation_block_size + data.rotation_index[bone_counter]]
            else:
                rotation_unpacked = data.default_rotation[bone_counter]

            offset = data.translation_offset[bone_counter]
            if data.translation_index[bone_counter] != -1:
                scale = data.translation_scale[bone_counter]
                t_packed = data.translation_data[fps_counter * data.translation_block_size + int(data.translation_index[bone_counter] / 3)] #translation index counts floats, data is stored as vector, thats why divide by 3
                for i in range(3):
                    t_packed[i] = t_packed[i] * scale[i]
                location_unpacked = offset + t_packed
            else:
                location_unpacked = offset

            translationMatrix = mathutils.Matrix.Translation(location_unpacked).to_4x4()
            rotationMatrix = rotation_unpacked.to_matrix().to_4x4()

            if data.bone_name_list[data.bone_index[bone_counter]-1] in armature.pose.bones:
                pose = armature.pose.bones[data.bone_name_list[bone_counter]]  #pose bone of current bone
                bone = armature.data.bones[data.bone_name_list[bone_counter]]    #bone of current bone

                if(pose.parent != None):
                    pose.matrix = pose.parent.matrix @ translationMatrix @ rotationMatrix
                else:
                    pose.matrix = translationMatrix @ rotationMatrix

                if data.rotation_index[bone_counter] != -1 or fps_counter == 0 or fps_counter == data.num_frames - 1:
                     pose.keyframe_insert(data_path='rotation_quaternion')

                if data.translation_index[bone_counter] != -1:
                    pose.keyframe_insert(data_path='location')

                if bone.name in data.visibilityDict:
                    pose.proxyIsHiddenAnimation = (data.visibilityDict[pose.name][scene.frame_current] == '0')
                    pose.keyframe_insert(data_path='proxyIsHiddenAnimation')

            bone_counter += 1
        fps_counter += 1
        scene.frame_set(scene.frame_current + 1)
    scene.frame_set(0)

def validate(data):
        armature = utils.findArmature()
        fitting = True
        for name in data.bone_name_list:
            if(name not in armature.data.bones):
                fitting = False
                break
        if(fitting):
            return True
        print("animation bones not matching active armature")
        return False

class AnimationImporter():
    def loadAnimation(self, filePath):
            global file
            file = open(filePath, 'rb') # 'rb' - open for reading in binary mode
            data = read_next_chunk(filePath)
            if(validate(data)):

                filePath = filePath[0:-4]
                fileNameIndex = filePath.rfind("\\") + 1
                fileName = filePath[fileNameIndex:]

                modelName = bpy.context.scene.modelFileName #doesn't always match

                if(modelName != ""):
                    if(modelName == fileName[:len(modelName)]):
                        fileName = fileName[len(modelName)+1:]

                action = bpy.data.actions.new("")
                action.name = fileName

                arm = utils.findArmature()

                if not arm.animation_data:
                    arm.animation_data_create()
                arm.animation_data.action = action

                create_animation(data)

class ALA_Importer(bpy.types.Operator):
    """ALA Importer"""      # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "import.ala"        # unique identifier for buttons and menu items to reference.
    bl_label = "Import ALA File"         # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # enable undo for the operator.
    filename_ext = ".ala"
    filter_glob : StringProperty(default="*.ala", options={'HIDDEN'})
    bl_info = {
        "name": "ALA Importer",
        "category": "Import",
    }

    filepath : StringProperty(name="File Path", description="Filepathused for importing the ALA file", maxlen=1024, default="")

    def execute(self, context):        # execute() is called by blender when running the operator.

        importer = AnimationImporter()
        animPath = self.properties.filepath
        importer.loadAnimation(animPath)
        utils.setModeToObject()
        return {'FINISHED'}            # this lets blender know the operator finished successfully.

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
