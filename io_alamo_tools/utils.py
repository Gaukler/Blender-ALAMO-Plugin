import bpy
import struct
import mathutils

#utilities
def findArmature():
    armatureName = bpy.context.scene.ActiveSkeleton.skeletonEnum
    if armatureName == 'None':
        return None
    armature = bpy.data.objects[armatureName]
    return armature

def getCurrentAction():
    arm = findArmature()
    if(arm != None):
        if arm.animation_data is not None and arm.animation_data.action is not None:
            return arm.animation_data.action
        else:
            return None
    else:
        return None

def clean_name(name):
    # remove Blenders numbers at the end of names
    if name[len(name) - 4:len(name) - 3] == ".":
        cut = name[0:len(name) - 4]
        return cut
    else:
        return name

def setModeToObject():
    if (bpy.context.mode != 'OBJECT'):
        bpy.ops.object.mode_set(mode='OBJECT')

def setModeToEdit():
    if (bpy.context.mode != 'EDIT'):
        bpy.ops.object.mode_set(mode='EDIT')

#pack

def pack_int(int):
    return struct.pack("<I", int)

def pack_float(float):
    return struct.pack("<f", float)

def pack_u_char(char):
    return struct.pack("<B", char)

def pack_char(char):
    return struct.pack("<b", char)

def pack_short(short):
    return struct.pack("<h", short)

def pack_u_short(short):
    return struct.pack("<H", short)


#unpack

def read_u_short(short):
    return struct.unpack("<H", short)[0]

def read_short(short):
    return struct.unpack("<h", short)[0]

def read_float(float):
    return struct.unpack("<f", float)[0]

def read_int(int):
    return struct.unpack("<I", int)[0]

def even(n):
    if n % 2 == 0:
        return True
    else:
        return False
