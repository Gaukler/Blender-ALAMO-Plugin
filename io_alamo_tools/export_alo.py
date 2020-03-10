import bpy
from . import settings, utils, export_ala

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

import mathutils
import math
from math import pi
from mathutils import Vector
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
import sys
import os
import bmesh
import copy

class ALO_Exporter(bpy.types.Operator):

    """ALO Exporter"""  # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "export.alo"  # unique identifier for buttons and menu items to reference.
    bl_label = "Export ALO File"  # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # enable undo for the operator.
    bl_info = {
        "name": "ALO Exporter",
        "category": "Export",
    }
    filename_ext = ".alo"
    filter_glob : StringProperty(default="*.alo", options={'HIDDEN'})

    filepath : StringProperty(name="File Path", description="Filepath used for exporting the ALO file", maxlen=1024,
                              default="")

    exportAnimations : BoolProperty(
            name="Export Animations",
            description="Export all animation actions as .ALA files, into the same directory",
            default=True,
            )

    exportHiddenObjects : BoolProperty(
            name="Export Hidden Objects",
            description="Export all objects, regardless of if they are hidden",
            default=True,
            )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "exportAnimations")
        layout.prop(self, "exportHiddenObjects")

    def execute(self, context):  # execute() is called by blender when running the operator.

        #skeleton and bones

        def create_skeleton():

            utils.setModeToObject()
            armature = utils.findArmature()

            if armature != None:
                armature.hide_render = False
                armature.select_set(True)  # select the skeleton
                bpy.context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')

            bone_count_chunk = b"\x01\x02\x00\00"  # add chunk header
            bone_count_chunk += utils.pack_u_short(128)  # add static chunk length
            bone_count_chunk += b'\x00\x00'

            global bone_index_list  # create list of bone indices
            bone_index_list = {"Root": 0}

            # count the bones
            bone_counter = 0
            if armature != None:
                for bone in armature.data.bones:
                    bone_counter += 1   #add before adding to list because we already have root
                    bone_index_list[bone.name] = bone_counter

            global num_bones
            num_bones = bone_counter
            bone_count_chunk += utils.pack_int(num_bones+1)  #+1 because root is added by exporter

            counter = 0
            while counter < 124:  # add padding bytes
                bone_count_chunk += b"\x00"
                counter += 1

            calculate_bone_matrix(armature)

            bone_chunk = create_bone_chunk_root();

            bone_name_per_alo_index = []

            if armature != None:
                bone_name_per_alo_index.append('Root')
                for bone in armature.data.bones:
                    bone_chunk += create_bone_chunk(bone, armature)
                    bone_name_per_alo_index.append(bone.name)

            data = bone_count_chunk
            data += bone_chunk

            header = (b"\x00\x02\x00\00")
            header += utils.pack_int(chunk_size(len(data)))

            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            file.write(header + data)  # write data to file

            return bone_name_per_alo_index  #used later for mesh animation mapping

        def create_bone_chunk_root():
            bone_name_chunk = b"\x03\x02\x00\00"

            name = 'Root'

            bone_name_encoded = bytes(name, 'utf-8') + b"\x00"
            bone_name_chunk += utils.pack_int(len(bone_name_encoded))
            bone_name_chunk += bone_name_encoded

            bone_v2 = b"\x06\x02\x00\00"  # add chunk name
            bone_v2 += b"\x3c\x00\x00\00"  # add (static) chunk length
            bone_v2 += b"\xff\xff\xff\xff"  # parent
            # add visible
            bone_v2 += b"\x01\x00\x00\00"

            # add billboard
            bone_v2 += utils.pack_int(settings.billboard_array['Disable'])

            # add bone matrix
            bone_v2 += utils.pack_float(bone_matrix['Root'][0][0])
            bone_v2 += utils.pack_float(bone_matrix['Root'][0][1])
            bone_v2 += utils.pack_float(bone_matrix['Root'][0][2])
            bone_v2 += utils.pack_float(bone_matrix['Root'][0][3])

            bone_v2 += utils.pack_float(bone_matrix['Root'][1][0])
            bone_v2 += utils.pack_float(bone_matrix['Root'][1][1])
            bone_v2 += utils.pack_float(bone_matrix['Root'][1][2])
            bone_v2 += utils.pack_float(bone_matrix['Root'][1][3])

            bone_v2 += utils.pack_float(bone_matrix['Root'][2][0])
            bone_v2 += utils.pack_float(bone_matrix['Root'][2][1])
            bone_v2 += utils.pack_float(bone_matrix['Root'][2][2])
            bone_v2 += utils.pack_float(bone_matrix['Root'][2][3])

            bone_header = b"\x02\x02\x00\00"  # add header
            bone_header += utils.pack_int(chunk_size(len(bone_name_chunk) + len(bone_v2)))  # add length of chunk
            bone_header += bone_name_chunk + bone_v2
            return bone_header

        def create_bone_chunk(bone, armature):

            bone_name_chunk = b"\x03\x02\x00\00"

            name = utils.clean_name(bone.name)

            bone_name_encoded = bytes(name, 'utf-8') + b"\x00"
            bone_name_chunk += utils.pack_int(len(bone_name_encoded))
            bone_name_chunk += bone_name_encoded

            bone_v2 = b"\x06\x02\x00\00"  # add chunk name
            bone_v2 += b"\x3c\x00\x00\00"  # add (static) chunk length
            if bone.parent != None:  # add bone parent index
                bone_v2 += utils.pack_int(bone_index_list[bone.parent.name])
            else:
                bone_v2 += b"\x00\x00\x00\x00"  # if parent doesnt exist use 0 (root)


            editBone = armature.data.edit_bones[bone.name]
            # add visible
            if (editBone.Visible == 0):
                bone_v2 += b"\x00\x00\x00\00"
            else:
                bone_v2 += b"\x01\x00\x00\00"

            # add billboard
            bone_v2 += utils.pack_int(settings.billboard_array[editBone.billboardMode.billboardMode])

            # add bone matrix
            bone_v2 += utils.pack_float(bone_matrix[bone.name][0][0])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][0][1])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][0][2])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][0][3])

            bone_v2 += utils.pack_float(bone_matrix[bone.name][1][0])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][1][1])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][1][2])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][1][3])

            bone_v2 += utils.pack_float(bone_matrix[bone.name][2][0])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][2][1])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][2][2])
            bone_v2 += utils.pack_float(bone_matrix[bone.name][2][3])

            bone_header = b"\x02\x02\x00\00"  # add header
            bone_header += utils.pack_int(chunk_size(len(bone_name_chunk) + len(bone_v2)))  # add length of chunk
            bone_header += bone_name_chunk + bone_v2
            return bone_header

        def calculate_bone_matrix(armature):

            global bone_matrix
            bone_matrix = {}

            bone_matrix['Root'] = mathutils.Matrix.Identity(4)

            if armature == None:
                return

            for bone in armature.data.bones:
                editBone = armature.data.edit_bones[bone.name]
                if(bone.parent != None):
                    bone_matrix[editBone.name] = editBone.parent.matrix.inverted() @ editBone.matrix
                else:
                    bone_matrix[editBone.name] = editBone.matrix

        #mesh and materials

        def create_mesh_name_chunk(mesh):
            mesh_name_chunk = b"\x01\x04\x00\00"  # add chunk header
            mesh_name_encoded = bytes(utils.clean_name(mesh.name), 'utf-8') + b"\x00"  # create name
            mesh_name_chunk += utils.pack_int(len(mesh_name_encoded))  # add lenth
            mesh_name_chunk += mesh_name_encoded  # add name
            file.write(mesh_name_chunk)

        def create_mesh_info_chunk(object, material_list):
            mesh_information_chunk = b"\x02\x04\x00\00"  # add chunk header
            mesh_information_chunk += utils.pack_int(128)  # add static chunk length

            n_materials = len(material_list)

            mesh_information_chunk += utils.pack_int(n_materials)

            # add bounding box data
            x_list = []
            y_list = []
            z_list = []
            float_counter = 0
            while float_counter <= 7:  # write all bounding box coordinates into list
                x_list.append(object.bound_box[float_counter][0])
                y_list.append(object.bound_box[float_counter][1])
                z_list.append(object.bound_box[float_counter][2])
                float_counter += 1

            mesh_information_chunk += utils.pack_float(min(x_list))  # write min/max of file into file
            mesh_information_chunk += utils.pack_float(min(y_list))
            mesh_information_chunk += utils.pack_float(min(z_list))

            mesh_information_chunk += utils.pack_float(max(x_list))
            mesh_information_chunk += utils.pack_float(max(y_list))
            mesh_information_chunk += utils.pack_float(max(z_list))

            mesh_information_chunk += b"\x00\x00\x00\00"  # unused

            # hidden
            if (object.Hidden):
                mesh_information_chunk += b"\x01\x00\x00\00"
            else:
                mesh_information_chunk += b"\x00\x00\x00\00"

            # colission
            if (object.HasCollision):
                mesh_information_chunk += b"\x01\x00\x00\00"
            else:
                mesh_information_chunk += b"\x00\x00\x00\00"

            counter = 0
            while counter < 88:  # add padding bytes
                mesh_information_chunk += b"\x00"
                counter += 1

            file.write(mesh_information_chunk)

        def check_if_material_is_used(material, mesh):
            for face in mesh.polygons:
                if material == mesh.materials[face.material_index]:
                    return True
            return False

        class vertexData():
            def __init__(self):
                self.co = mathutils.Vector((0, 0, 0))
                self.uv = mathutils.Vector((0, 0))
                self.normal = mathutils.Vector((0, 0, 0))
                self.tangent = mathutils.Vector((0, 0, 0))
                self.bitangent  = mathutils.Vector((0, 0, 0))
                self.bone_index = 0
                self.face_index = 0

        #list of script-added modifiers on current object
        #used to clean up if runtime error is raised
        globalCleanupModifierList = []

        def cleanUpModifiers(object):
            global globalCleanupModifierList
            for modifier in globalCleanupModifierList:
                object.modifiers.remove(modifier)
            object.to_mesh_clear()

        def create_mesh(mesh_list, bone_name_per_alo_index):
            for object in mesh_list:

                context.view_layer.objects.active = object

                mesh_data_header = b"\x00\x04\x00\00"
                mesh_data_header += utils.pack_int(0)
                file.write(mesh_data_header)
                #jump back here to update the chunk size
                jumpPointSize = file.tell()-4

                triangleModifier = object.modifiers.new('Triangulate', 'TRIANGULATE')

                global globalCleanupModifierList
                globalCleanupModifierList = []
                globalCleanupModifierList.append(triangleModifier)

                #disable armature for export by setting target to None
                armatureTarget = None
                for modifier in object.modifiers:  # check if object has skeleton by checking for rig modifier
                    if modifier.type == "ARMATURE":
                        armatureTarget = modifier.object
                        modifier.object = None

                #if object is disabled modifiers are not evaluated
                #temporarily unhide
                wasHidden = object.hide_viewport
                object.hide_viewport = False;

                depsgraph = context.evaluated_depsgraph_get()
                object_eval = object.evaluated_get(depsgraph)
                mesh = bpy.data.meshes.new_from_object(object_eval, preserve_all_data_layers=True, depsgraph=depsgraph)

                object.hide_viewport = wasHidden;

                #reenable armature modifier
                for modifier in object.modifiers:  # check if object has skeleton by checking for rig modifier
                    if modifier.type == "ARMATURE":
                        modifier.object = armatureTarget

                material_list = []
                for material in mesh.materials:
                    material_is_used = check_if_material_is_used(material, mesh)
                    if material_is_used:
                        material_list.append(material)

                create_mesh_name_chunk(mesh)
                create_mesh_info_chunk(object, material_list)

                sub_mesh_data_chunk = b''
                for material in material_list:
                    create_material_chunk(material)
                    create_sub_mesh_data_chunk(mesh, material, object, bone_name_per_alo_index)

                cleanUpModifiers(object)

                jumpEndPoint = file.tell()
                file.seek(jumpPointSize, 0)
                file.write(utils.pack_int(chunk_size(jumpEndPoint - jumpPointSize - 4)))
                file.seek(jumpEndPoint, 0)

        def create_index_buffer(face_data):
            index_buffer_header = b"\x04\x00\x01\00"  # add chunk header
            index_buffer_header += utils.pack_int(len(face_data)*2)  # length of chunk is 2*(3*face_count)
            file.write(index_buffer_header)
            for face in face_data:
                file.write(utils.pack_u_short(face))

        #uses mesh vertices, bmesh uses different data layout
        def getMaxWeightGroupIndex(vertex):
            maxWeight = 0
            resultGroup = None
            for group in vertex.groups:
                weight = group.weight
                if(weight > maxWeight):
                    resultGroup = group.group
                    maxWeight = weight
            return resultGroup

        def create_animation_mapping(mesh, object, material, bone_name_per_alo_index):

            mesh.update()
            animation_mapping_chunk = b""
            for modifier in object.modifiers:  # check if object has skeleton by checking for rig modifier
                if modifier.type == "ARMATURE":

                    #add bone indices, iterate over every vertex and add group index if not yet in list
                    group_index_list = [0]   #indices of groups
                    for face in mesh.polygons:
                        if (material.name == object.material_slots[face.material_index].name):
                            for vertexIndex in face.vertices:
                                vertex = mesh.vertices[vertexIndex]
                                groupIndex = getMaxWeightGroupIndex(vertex)
                                if groupIndex not in group_index_list:
                                    group_index_list.append(groupIndex)

                    for index in group_index_list:
                        if index == None:
                            cleanUpModifiers(object)
                            raise RuntimeError('Missing vertex group on object: ' + object.name)

                    group_index_list.sort()
                    group_to_alo_index = {}

                    bone_index_list = []
                    for index, vertex_group in enumerate(group_index_list):
                        for counter, entry in enumerate(bone_name_per_alo_index):
                            if object.vertex_groups[vertex_group].name == entry:
                                bone_index_list.append(counter)
                                group_to_alo_index[vertex_group] = index
                                break

                    for counter, bone in enumerate(bone_index_list):
                        animation_mapping_chunk += utils.pack_int(bone)

                    animation_mapping_chunk_header = b"\x06\x00\x01\00"  # add chunk header
                    animation_mapping_chunk_header += utils.pack_int(len(animation_mapping_chunk))
                    chunk = animation_mapping_chunk_header + animation_mapping_chunk
                    return [chunk, group_to_alo_index]
            return [b'', None]

        def submesh_vertex_face_data(bm, object, material, uses_bump, mesh):

            # list of all faces using the current material
            faces = []
            for face in bm.faces:
                if (material.name == object.material_slots[face.material_index].name):
                    faces.append(face)

            vertices = []
            face_indices = []

            #calc_tangents() must be called before accessing the uv layer
            #otherwise the uv data will break under certain circumstances
            #blender bug?
            mesh.calc_tangents()

            uv_layer = mesh.uv_layers.active.data
            loop_to_alo_index = {}   #dictionary that maps blender vertex indices to the corresponding alo index
                                        #only smooth shaded faces are saved here, as flat shaded faces need duplicate vertices anyway

            alo_index = 0
            for face in faces:
                for loop in face.loops:

                    vert = loop.vert
                    store_vertex = True

                    if face.smooth:
                        for adjacent_loop in vert.link_loops:
                            if adjacent_loop != loop and uv_layer[loop.index].uv == uv_layer[adjacent_loop.index].uv:
                                #don't save duplicate if same vertex and same UV coordinates are used
                                if adjacent_loop.index in loop_to_alo_index:
                                    face_indices.append(loop_to_alo_index[adjacent_loop.index])
                                    store_vertex = False
                                    break


                    if store_vertex:
                        vertex = vertexData()
                        vertex.co = vert.co

                        if face.smooth:
                            vertex.normal = vert.normal
                        else:
                            vertex.normal = face.normal

                        vertex.uv =  uv_layer[loop.index].uv

                        meshVertex = mesh.vertices[vert.index]
                        vertex.bone_index = getMaxWeightGroupIndex(meshVertex)
                        if(vertex.bone_index == None):
                            vertex.bone_index = 0

                        vertices.append(vertex)
                        face_indices.append(alo_index)

                        if face.smooth:
                            loop_to_alo_index[loop.index] = alo_index

                        vertex.face_index = face.index

                        alo_index += 1

                        if uses_bump:
                            vertex.tangent = copy.copy(mesh.loops[loop.index].tangent)
                            vertex.bitangent = copy.copy(mesh.loops[loop.index].bitangent)

            return [vertices, face_indices]

        def shadow_vertex_face_data(bm, mesh, object):

            # list of all faces using the current material
            per_face_vertex_id = {}

            vertices = []
            face_indices = []

            alo_index = 0
            for face in bm.faces:
                indexArray = {}
                for vert in face.verts:
                    vertex = vertexData()
                    vertex.co = vert.co
                    vertex.normal = face.normal

                    vertex.uv =  mathutils.Vector((0, 0))

                    meshVertex = mesh.vertices[vert.index]
                    vertex.bone_index = getMaxWeightGroupIndex(meshVertex)
                    if(vertex.bone_index == None):
                        vertex.bone_index = 0


                    vertices.append(vertex)
                    face_indices.append(alo_index)

                    indexArray[vert.index] = alo_index
                    alo_index += 1
                per_face_vertex_id[face.index] = indexArray


            for edge in bm.edges:
                face1 = edge.link_faces[0]
                face2 = edge.link_faces[1]

                f1v1 = per_face_vertex_id[face1.index][edge.verts[0].index]
                f1v2 = per_face_vertex_id[face1.index][edge.verts[1].index]

                f2v1 = per_face_vertex_id[face2.index][edge.verts[0].index]
                f2v2 = per_face_vertex_id[face2.index][edge.verts[1].index]

                mid1 = mathutils.Vector((0, 0, 0))
                for vert in face1.verts:
                    mid1 += vert.co
                mid1 /= 3

                mid2 = mathutils.Vector((0, 0, 0))
                for vert in face2.verts:
                    mid2 += vert.co
                mid2 /= 3


                face1v1 = edge.verts[0].co * 0.75 + mid1 * 0.25
                face1v2 = edge.verts[1].co * 0.75 + mid1 * 0.25
                face2v1 = edge.verts[0].co * 0.75 + mid2 * 0.25
                face2v2 = edge.verts[1].co * 0.75 + mid2 * 0.25

                out = face1.normal + face2.normal

                #first face
                edge1 = face1v1 - face2v1
                edge2 = face1v2 - face2v1

                cross = mathutils.Vector.cross(edge1, edge2)
                dot = mathutils.Vector.dot(out, cross)

                if dot < 0:
                    face_indices.append(f1v1)
                    face_indices.append(f2v1)
                    face_indices.append(f1v2)
                else:
                    face_indices.append(f1v1)
                    face_indices.append(f1v2)
                    face_indices.append(f2v1)

                #second face
                edge1 = face1v1 - face2v1
                edge2 = face1v2 - face2v1

                cross = mathutils.Vector.cross(edge1, edge2)
                dot = mathutils.Vector.dot(out, cross)

                if dot < 0:
                    face_indices.append(f2v2)
                    face_indices.append(f1v2)
                    face_indices.append(f2v1)
                else:
                    face_indices.append(f2v2)
                    face_indices.append(f2v1)
                    face_indices.append(f1v2)

            return [vertices, face_indices]

        def create_sub_mesh_data_chunk(mesh, material, object, bone_name_per_alo_index):

            sub_mesh_data_header = b"\x00\x00\x01\00"
            sub_mesh_data_header += utils.pack_int(0)
            file.write(sub_mesh_data_header)
            jumpPointSize = file.tell()-4   #jump back here and correct size

            bm = bmesh.new()  # create an empty BMesh
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()

            shader = material.shaderList.shaderList
            is_shadow = False
            if shader == 'MeshShadowVolume.fx' or shader == 'RSkinShadowVolume.fx':
                is_shadow = True

            uses_bump = False
            if shader in settings.bumpMappingList:
                uses_bump = True

            vertex_face_data = None
            if is_shadow:
                vertex_face_data = shadow_vertex_face_data(bm, mesh, object)
            else:
                vertex_face_data = submesh_vertex_face_data(bm, object, material, uses_bump, mesh)

            vertices = vertex_face_data[0]
            face_indices = vertex_face_data[1]

            create_sub_mesh_info_chunk(len(vertices), len(face_indices))
            create_vertex_format_chunk(material)

            mapping_data = create_animation_mapping(mesh, object, material, bone_name_per_alo_index)

            #replace vertex group index with mapped bone index
            group_to_alo_index = mapping_data[1]
            if group_to_alo_index != None:
                for vertex in vertices:
                    vertex.bone_index = group_to_alo_index[vertex.bone_index]
            else:
                #if object has no armature modifier bone index is always 0
                for vertex in vertices:
                    vertex.bone_index = 0

            create_vertex_buffer(vertices, shader)
            create_index_buffer(face_indices)

            file.write(mapping_data[0])

            if (object.HasCollision):
                create_collision_chunk(bm, file)
            bm.free()

            jumpEndPoint = file.tell()
            file.seek(jumpPointSize, 0)
            file.write(utils.pack_int(chunk_size(jumpEndPoint - jumpPointSize -4)))
            file.seek(jumpEndPoint, 0)

        def create_vertex_buffer(vertices, shader):

            chunk_header = b"\x07\x00\x01\00"
            chunk_header += utils.pack_int(len(vertices)*144)
            file.write(chunk_header)

            for vertex in vertices:

                #location
                file.write(utils.pack_float(vertex.co[0]))
                file.write(utils.pack_float(vertex.co[1]))
                file.write(utils.pack_float(vertex.co[2]))

                #normal
                normal = vertex.normal.normalized()
                file.write(utils.pack_float(normal[0]))
                file.write(utils.pack_float(normal[1]))
                file.write(utils.pack_float(normal[2]))


                #UVs
                file.write(utils.pack_float( vertex.uv[0]))
                file.write(utils.pack_float(-vertex.uv[1])) #second UV mirrored in alo format

                #unused UVs
                counter = 0
                while (counter<6):
                    file.write(utils.pack_int(0))
                    counter += 1

                tangent   = vertex.tangent
                bitangent = vertex.bitangent

                tangent.normalize()
                bitangent.normalize()

                file.write(utils.pack_float(tangent.x))
                file.write(utils.pack_float(tangent.y))
                file.write(utils.pack_float(tangent.z))

                file.write(utils.pack_float(bitangent.x))
                file.write(utils.pack_float(bitangent.y))
                file.write(utils.pack_float(bitangent.z))

                #color
                file.write(utils.pack_float(1))
                file.write(utils.pack_float(1))
                file.write(utils.pack_float(1))
                file.write(utils.pack_float(1))

                #unused
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))

                #bone indices
                file.write(utils.pack_int(vertex.bone_index))

                #unused bone indices
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))

                #bone weight, always 1
                file.write(utils.pack_float(1))

                #unused bone weights
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))
                file.write(utils.pack_int(0))

        def create_sub_mesh_info_chunk(vertex_number, face_number):
            sub_mesh_information_chunk = b"\x01\x00\x01\00"  # add chunk header
            sub_mesh_information_chunk += utils.pack_int(128)  # add static chunk length

            #add number of vertices using material
            sub_mesh_information_chunk += utils.pack_int(vertex_number)
            # add number of faces using material
            sub_mesh_information_chunk += utils.pack_int(int(face_number/3))  #face number is number of indices

            counter = 0
            while counter < 120:  # add padding bytes
                sub_mesh_information_chunk += b"\x00"
                counter += 1
            file.write(sub_mesh_information_chunk)

        def create_vertex_format_chunk(material):
            vertex_format_chunk_header = b"\x02\x00\x01\00"

            vertex_format_chunk = bytes(settings.vertex_format_dict[material.shaderList.shaderList], 'utf-8') + b"\x00"
            vertex_format_chunk_header += utils.pack_int(len(vertex_format_chunk))  # add size
            file.write(vertex_format_chunk_header + vertex_format_chunk)

        def create_material_chunk(material):
            sub_mesh_material_info_chunk_header = b"\x00\x01\x01\00"

            mat_name = material.shaderList.shaderList
            sub_mesh_material_info_chunk = create_mat_name_chunk(mat_name)
            sub_mesh_material_info_chunk += create_mat_info_chunks(mat_name, material)

            # add length to header,then combine header and chunk
            sub_mesh_material_info_chunk_header += utils.pack_int(chunk_size(len(sub_mesh_material_info_chunk)))
            sub_mesh_material_info_chunk_header += sub_mesh_material_info_chunk

            file.write(sub_mesh_material_info_chunk_header)

        def create_mat_name_chunk(mat_name):
            chunk = b"\x01\x01\x01\00"
            chunk += utils.pack_int(len(mat_name) + 1)  # add length
            chunk += bytes(mat_name, 'utf-8') + b"\x00"  # add shader name
            return chunk

        def create_mat_info_chunks(mat_name, material):
            chunk = b''
            for parameter in settings.material_parameter_dict[mat_name]:
                if (parameter == "Color"):
                    chunk += mat_float4_chunk("Color", material.Color)
                elif (parameter == "Emissive"):
                    chunk += mat_float4_chunk("Emissive", material.Emissive)
                elif (parameter == "Diffuse"):
                    chunk += mat_float4_chunk("Diffuse", material.Diffuse)
                elif (parameter == "Specular"):
                    chunk += mat_float4_chunk("Specular", material.Specular)
                elif (parameter == "Shininess"):
                    chunk += mat_float_chunk("Shininess", material.Shininess)
                elif (parameter == "BaseTexture"):
                    chunk += mat_tex_chunk("BaseTexture", material.BaseTexture)
                elif (parameter == "NormalDetailTexture"):
                    chunk += mat_tex_chunk("NormalDetailTexture", material.NormalDetailTexture)
                elif (parameter == "DetailTexture"):
                    chunk += mat_tex_chunk("DetailTexture", material.DetailTexture)
                elif (parameter == "NormalTexture"):
                    chunk += mat_tex_chunk("NormalTexture", material.NormalTexture)
                elif (parameter == "DebugColor"):
                    chunk += mat_float4_chunk("DebugColor", material.DebugColor)
                elif (parameter == "UVScrollRate"):
                    chunk += mat_float4_chunk("UVScrollRate", material.UVScrollRate)
                elif (parameter == "BendScale"):
                    chunk += mat_float_chunk("BendScale", material.BendScale)
                elif (parameter == "UVOffset"):
                    chunk += mat_float4_chunk("UVOffset", material.UVOffset)
                elif (parameter == "Colorization"):
                    chunk += mat_float4_chunk("Colorization", material.Colorization)
                elif (parameter == "GlossTexture"):
                    chunk += mat_tex_chunk("GlossTexture", material.GlossTexture)
                elif (parameter == "BaseUVScale"):
                    chunk += mat_float_chunk("BaseUVScale", material.BaseUVScale)
                elif (parameter == "WaveUVScale"):
                    chunk += mat_float_chunk("WaveUVScale", material.WaveUVScale)
                elif (parameter == "DistortUVScale"):
                    chunk += mat_float_chunk("DistortUVScale", material.DistortUVScale)
                elif (parameter == "BaseUVScrollRate"):
                    chunk += mat_float_chunk("BaseUVScrollRate", material.BaseUVScrollRate)
                elif (parameter == "WaveUVScrollRate"):
                    chunk += mat_float_chunk("WaveUVScrollRate", material.WaveUVScrollRate)
                elif (parameter == "DistortUVScrollRate"):
                    chunk += mat_float_chunk("DistortUVScrollRate", material.DistortUVScrollRate)
                elif (parameter == "WaveTexture"):
                    chunk += mat_tex_chunk("WaveTexture", material.WaveTexture)
                elif (parameter == "DistortionTexture"):
                    chunk += mat_tex_chunk("DistortionTexture", material.DistortionTexture)
                elif (parameter == "UVScrollRate"):
                    chunk += mat_float4_chunk("UVScrollRate", material.UVScrollRate)
                elif (parameter == "DistortionScale"):
                    chunk += mat_float_chunk("DistortionScale", material.DistortionScale)
                elif (parameter == "SFreq"):
                    chunk += mat_float_chunk("SFreq", material.SFreq)
                elif (parameter == "TFreq"):
                    chunk += mat_float_chunk("TFreq", material.TFreq)
                elif (parameter == "Atmosphere"):
                    chunk += mat_float4_chunk("Atmosphere", material.Atmosphere)
                elif (parameter == "CityColor"):
                    chunk += mat_float4_chunk("CityColor", material.CityColor)
                elif (parameter == "AtmospherePower"):
                    chunk += mat_float_chunk("AtmospherePower", material.AtmospherePower)
                elif (parameter == "CloudScrollRate"):
                    chunk += mat_float_chunk("CloudScrollRate", material.CloudScrollRate)
                elif (parameter == "CloudTexture"):
                    chunk += mat_tex_chunk("CloudTexture", material.CloudTexture)
                elif (parameter == "CloudNormalTexture"):
                    chunk += mat_tex_chunk("CloudNormalTexture", material.CloudNormalTexture)
                elif (parameter == "EdgeBrightness"):
                    chunk += mat_float_chunk("EdgeBrightness", material.EdgeBrightness)
                elif (parameter == "MappingScale"):
                    chunk += mat_float_chunk("MappingScale", material.MappingScale)
                elif (parameter == "BlendSharpness"):
                    chunk += mat_float_chunk("BlendSharpness", material.MappingScale)
                #else:
                    #print("warning: unkown shader parameter: " + parameter)    #for debugging
            return chunk

        def create_collision_chunk(bm, file):

            def calc_bb_face(face):
                bb_min = face.verts[0].co.xyz
                bb_max = face.verts[0].co.xyz

                for vert in face.verts:
                    for i in range(0, 3):
                        if bb_min[i] > vert.co[i]:
                            bb_min[i] = vert.co[i]
                        if bb_max[i] < vert.co[i]:
                            bb_max[i] = vert.co[i]

                return [bb_min, bb_max]


            def calc_bb_two_bb(bb1, bb2):   #takes two bbs and calculates combined bb

                bb_min = mathutils.Vector((0, 0, 0))
                bb_max = mathutils.Vector((0, 0, 0))

                for i in range (0, 3):
                    bb_min[i] = min(bb1[0][i], bb2[0][i])
                    bb_max[i] = max(bb1[1][i], bb2[1][i])

                return [bb_min, bb_max]


            def calc_bb_list(list_start):
                current_entry = list_start
                bb_min = list_start.elem.bb_min
                bb_max = list_start.elem.bb_max
                while(current_entry != None):
                    current_bb_min = current_entry.elem.bb_min
                    current_bb_max = current_entry.elem.bb_max
                    for i in range (0, 3):
                        if bb_min[i] > current_bb_min[i]:
                            bb_min[i] = current_bb_min[i]
                        if bb_max[i] < current_bb_max[i]:
                            bb_max[i] = current_bb_max[i]
                    current_entry = current_entry.next_elem
                return [bb_min, bb_max]


            def calc_volume_bb(bb_min, bb_max):
                length = bb_max - bb_min
                return abs(length[0]) * abs(length[1]) * abs(length[2])


            def calc_parent_space(parent, child):
                child.parent_space_min = mathutils.Vector((0, 0, 0))
                child.parent_space_max = mathutils.Vector((0, 0, 0))
                for i in range(0, 3):
                    distance = parent.bb_max[i] - parent.bb_min[i]
                    if distance != 0:
                        parent_space_min = child.bb_min[i] - parent.bb_min[i]                   #normalize to 0
                        child.parent_space_min[i] = round( parent_space_min / distance * 255 )  #scale to 0-1 and then 0-255

                        parent_space_max = child.bb_max[i] - parent.bb_min[i]                   #normalize to 0
                        child.parent_space_max[i] = round( parent_space_max / distance * 255 )  #scale to 0-1 and then 0-255
                    else:
                        child.parent_space_min[i] = 0
                        child.parent_space_max[i] = 255


            def calc_parent_space_recursive(parent):
                child1 = parent.link[0]
                child2 = parent.link[1]
                calc_parent_space(parent, child1)
                calc_parent_space(parent, child2)

                if not child1.leaf:
                    calc_parent_space_recursive(child1)
                if not child2.leaf:
                    calc_parent_space_recursive(child2)

            def select_longest_side(bb_min, bb_max):
                longest_side = 0
                longest_length = abs(bb_max[0] - bb_min[0]) #abs shouldn't be neccessary?
                for i in range (1, 3):
                    length = abs(bb_max[i] - bb_min[i])
                    if length > longest_length:
                        longest_length = length
                        longest_side = i
                return longest_side

            def order_list(list, i):
                #i is the side that is ordered by
                #mean of min and max is used for ordering
                new_list_start = None
                current_entry = list
                #iterate through old list and add at ordered position in new list
                while current_entry != None:
                    #find correct position
                    current_mean = current_entry.elem.bb_mean[i]
                    active_comparison = new_list_start
                    previous_entry = None
                    while True: #used to iterate trough new_list, terminates at the latest when list end is reached
                        #list end is reached
                        if active_comparison == None:
                            if previous_entry != None:
                                previous_entry.next_elem = current_entry
                            else:
                                new_list_start = current_entry
                            next_current_entry = current_entry.next_elem
                            current_entry.next_elem = None
                            current_entry = next_current_entry
                            break
                        #case1: list mean smaller, continue searching
                        if current_mean > active_comparison.elem.bb_mean[i]:
                            previous_entry = active_comparison
                            active_comparison = active_comparison.next_elem
                        #case2: list mean bigger, correct position found
                        else:
                            #previous element was list start
                            if previous_entry == None:
                                new_list_start = current_entry
                            else:
                                previous_entry.next_elem = current_entry
                            #safe next entry before it's overwritten
                            next_current_entry = current_entry.next_elem
                            current_entry.next_elem = active_comparison
                            current_entry = next_current_entry
                            break
                return new_list_start


            def median_cut(current_node, list):
                #current node has bb set and needs links
                #median cut selects the longest side of the bb, orders all elements according to that side and cuts at the median
                #apply recursively until leaf is reached
                i = select_longest_side(current_node.bb_min, current_node.bb_max)

                list = order_list(list, i)

                list_length = list.length()
                median_index = round((list_length - 1) / 2)
                last_entry = list
                counter = 0
                while(counter < median_index):
                    last_entry = last_entry.next_elem
                    counter += 1
                second_list_start = last_entry.next_elem
                last_entry.next_elem = None

                list_1_bb = calc_bb_list(list)
                node1 = treeNode(list_1_bb[0], list_1_bb[1])

                list_2_bb = calc_bb_list(second_list_start)
                node2 = treeNode(list_2_bb[0], list_2_bb[1])

                if list.length() > 1:
                    median_cut(node1, list)
                else:
                    node1 = list.elem

                if second_list_start.length() > 1:
                    median_cut(node2, second_list_start)
                else:
                    node2 = second_list_start.elem

                current_node.link = [node1, node2]


            def tree_to_array(root):
                array = []
                to_do = [root]
                counter = 0
                while len(to_do) != 0:
                    active = to_do[0]
                    if not active.leaf:
                        to_do.append(active.link[0])
                        to_do.append(active.link[1])
                    active.index = counter
                    array.append(to_do.pop(0))
                    counter += 1
                return array


            class treeNode():
                def __init__(self, min, max):
                    self.bb_min = min
                    self.bb_max = max
                    self.bb_mean = min + max / 2
                    self.parent_space_min = None
                    self.parent_space_max = None
                    self.link = None
                    self.leaf = False
                    self.index = None
                    self.face = None


            class linkedList():
                def __init__(self):
                    self.elem = None
                    self.next_elem = None

                def length(self):
                    entry = self
                    length = 0
                    while(entry != None):
                        entry = entry.next_elem
                        length += 1
                    return length

                def print_elements(self):
                    entry = self
                    while(entry != None):
                        print(entry.elem.bb_mean)
                        entry = entry.next_elem


            #create a linked list with leaf nodes
            #Group faces with similiar bb together
            processed_faces = []
            list_start = linkedList()
            current_entry = list_start
            for index, face in enumerate(bm.faces):
                if face.index not in processed_faces:
                    bb = calc_bb_face(face)
                    start_volume = calc_volume_bb(bb[0], bb[1])
                    node = treeNode(bb[0], bb[1])
                    node.link = face
                    node.leaf = True
                    node.face = [face.index]
                    # for edge in face.edges:
                    #     for face2 in edge.link_faces:
                    #         if face2.index != face.index:
                    #             if face2.index not in processed_faces:
                    #                 new_bb = calc_bb_face(face2)
                    #                 combined_bb = calc_bb_two_bb(bb, new_bb)
                    #                 new_volume = calc_volume_bb(combined_bb[0], combined_bb[1])
                    #                 if new_volume < start_volume * 1.25:
                    #                     node.face.append(face2.index)
                    #                     processed_faces.append(face2.index)
                    #                     bb = combined_bb
                    #                     if len(node.face) >= 2:
                    #                         break

                    node.bb_min = bb[0]
                    node.bb_max = bb[1]

                    current_entry.elem = node
                    new_entry = linkedList()
                    current_entry.next_elem = new_entry
                    current_entry = new_entry

            #delete last entry, new_entry was set one more time than necessary
            index = 0
            current_entry = list_start
            while current_entry.next_elem.elem != None:
                current_entry = current_entry.next_elem
            current_entry.next_elem = None

            bb = calc_bb_list(list_start)
            root = treeNode(bb[0], bb[1])
            root.parent_space_min = mathutils.Vector((0, 0, 0))
            root.parent_space_max = mathutils.Vector((255, 255, 255))
            #print('median cut starts')
            median_cut(root, list_start)
            #print('parent space calculation starts')
            calc_parent_space_recursive(root)
            #print('tree to array starts')
            array = tree_to_array(root)
            #print('writing starts')
            treeNodeChunk = b''
            triangleMappingChunk = b''

            triangle_counter = 0
            for entry in array:

                treeNodeChunk += utils.pack_u_char(int(entry.parent_space_min[0]))
                treeNodeChunk += utils.pack_u_char(int(entry.parent_space_min[1]))
                treeNodeChunk += utils.pack_u_char(int(entry.parent_space_min[2]))

                treeNodeChunk += utils.pack_u_char(int(entry.parent_space_max[0]))
                treeNodeChunk += utils.pack_u_char(int(entry.parent_space_max[1]))
                treeNodeChunk += utils.pack_u_char(int(entry.parent_space_max[2]))

                if entry.leaf:
                    treeNodeChunk += utils.pack_short(int(len(entry.face)))
                    treeNodeChunk += utils.pack_short(triangle_counter)

                    for face in entry.face:
                        triangleMappingChunk += utils.pack_short(face)
                        triangle_counter += 1
                else:
                    treeNodeChunk += utils.pack_short(int(0))
                    treeNodeChunk += utils.pack_short(entry.link[0].index)

            treeNodeChunkHeader = b'\x02\x12\x00\00'
            treeNodeChunkHeader += utils.pack_int(len(treeNodeChunk))
            treeNodeChunkHeader += treeNodeChunk

            triangleMappingChunkHeader = b'\x03\x12\x00\00'
            triangleMappingChunkHeader += utils.pack_int(len(triangleMappingChunk))
            triangleMappingChunkHeader += triangleMappingChunk


            info = b'\x00\x0c'

            info += utils.pack_float(bb[0][0])
            info += utils.pack_float(bb[0][1])
            info += utils.pack_float(bb[0][2])

            info += b'\x01\x0c'

            info += utils.pack_float(bb[1][0])
            info += utils.pack_float(bb[1][1])
            info += utils.pack_float(bb[1][2])

            info += b'\x02\x04'
            info += utils.pack_int(len(array))
            info += b'\x03\x04'
            info += utils.pack_int(len(bm.faces))

            infoHeader = b'\x01\x12\x00\00'
            infoHeader += utils.pack_int(len(info))
            infoHeader += info

            chunk_header = b'\x00\x12\x00\00'
            chunk_header += utils.pack_int(chunk_size(len(infoHeader) + len(treeNodeChunkHeader) + len(triangleMappingChunkHeader)))

            file.write(chunk_header)
            file.write(infoHeader)
            file.write(treeNodeChunkHeader)
            file.write(triangleMappingChunkHeader)

        #material utilities

        def mat_float4_chunk(name, value):
            chunk = b"\x06\x01\x01\00"
            chunk += utils.pack_int(len(name) + 21)  # add length
            chunk += b"\x01"  # mini chunk header
            chunk += utils.pack_u_char((len(name) + 1))  # size
            chunk += bytes(name, 'utf-8') + b"\x00"  # add name
            chunk += b"\x02\x10"  # mini chunk header with size
            chunk += utils.pack_float(value[0])
            chunk += utils.pack_float(value[1])
            chunk += utils.pack_float(value[2])
            chunk += utils.pack_float(value[3])
            return chunk

        def mat_float_chunk(name, v1):
            chunk = b"\x03\x01\x01\00"
            chunk += utils.pack_int(len(name) + 9)  # add length
            chunk += b"\x01"  # mini chunk header
            chunk += utils.pack_u_char((len(name) + 1))  # size
            chunk += bytes(name, 'utf-8') + b"\x00"  # add name
            chunk += b"\x02\x04"  # mini chunk header with size
            chunk += utils.pack_float(v1)
            return chunk

        def mat_tex_chunk(type, name):
            chunk = b"\x05\x01\x01\00"
            chunk += utils.pack_int(len(name) + len(type) + 6)  # add length
            chunk += b"\x01"  # mini chunk header
            chunk += utils.pack_u_char(len(type) + 1)  # size
            chunk += bytes(type, 'utf-8') + b"\x00"  # add type
            chunk += b"\x02"  # mini chunk header
            chunk += utils.pack_u_char(len(name) + 1)  # size
            chunk += bytes(name, 'utf-8') + b"\x00"  # add type
            return chunk

        #connection and proxies

        def create_connections(mesh_list):
            object_connection = b""  # initialize
            object_connection_count = b"\x01\x06\x00\00"
            object_connection_count += utils.pack_int(12)
            object_connection_count += b"\x01\x04"

            skinned_object_counter = 0  # counts how many object have bone connections

            for counter, object in enumerate(mesh_list):
                exported = True
                object_connection += b"\x02\x06\x00\00"
                object_connection += utils.pack_int(12)
                object_connection += b"\x02\x04"
                object_connection += utils.pack_int(counter)
                object_connection += b"\x03\x04"
                written = False
                for constraint in object.constraints:
                    if constraint.type == 'CHILD_OF':
                        if constraint.subtarget != None:
                            connectedBone = constraint.subtarget
                            object_connection += utils.pack_int(bone_index_list[connectedBone])
                            written = True
                            break
                if not written:
                    object_connection += b"\x00\x00\x00\00"
                skinned_object_counter += 1

            armature = utils.findArmature()
            proxy_counter = 0

            if armature!= None:
                armature.select_set(True)  # select the skeleton
                context.view_layer.objects.active = armature

                bpy.ops.object.mode_set(mode='EDIT')
                for bone in armature.data.edit_bones:
                    if bone.EnableProxy == True:
                        proxy_chunk = b"\x05"
                        proxy_chunk += utils.pack_char(len(bone.ProxyName) + 1)  # add length
                        proxy_chunk += bytes(bone.ProxyName, 'utf-8') + b"\x00"  # add shader name
                        proxy_chunk += b"\x06"
                        proxy_chunk += utils.pack_char(4)  # add length
                        proxy_chunk += utils.pack_int(bone_index_list[bone.name])

                        #only needed if true
                        if bone.proxyIsHidden == True:
                            proxy_chunk += b"\x07"
                            proxy_chunk += utils.pack_char(4)  # add length
                            proxy_chunk += b"\x01\x00\x00\00"

                        if bone.altDecreaseStayHidden == True:
                            proxy_chunk += b"\x08"
                            proxy_chunk += utils.pack_char(4)  # add length
                            proxy_chunk += b"\x01\x00\x00\00"

                        proxy_chunk_header = b"\x03\x06\x00\00"
                        proxy_chunk_header += utils.pack_int(len(proxy_chunk))
                        object_connection += proxy_chunk_header + proxy_chunk
                        proxy_counter += 1

            object_connection_count += utils.pack_int(skinned_object_counter)
            object_connection_count += b"\x04\x04"
            object_connection_count += utils.pack_int(proxy_counter)

            object_connection_count += object_connection  # combine for length calculation
            connection_chunk = b"\x00\x06\x00\00"
            connection_chunk += utils.pack_int(chunk_size(len(object_connection))+20)    #+20 if for the connection count chunk

            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            file.write(connection_chunk + object_connection_count)

        #utilities

        def chunk_size(size):
            #high bit is used to determine if a chunk holds chunks or data
            #add 2147483648 instead of binary operation
            return size+2147483648

        def selectNonManifoldVertices(object):
            if(bpy.context.mode != 'OBJECT'):
                bpy.ops.object.mode_set(mode='OBJECT')
            object.hide_set(False)
            bpy.context.view_layer.objects.active = object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.mesh.select_non_manifold()

        def checkShadowMesh(mesh_list):  #checks if shadow meshes are correct and checks if material is missing
            for object in mesh_list:
                if len(object.data.materials) == 0:
                    raise RuntimeError('Missing material on object: ' + object.name)
                shader = object.data.materials[0].shaderList.shaderList
                if shader == 'MeshShadowVolume.fx' or shader == 'RSkinShadowVolume.fx':
                    bm = bmesh.new()  # create an empty BMesh
                    bm.from_mesh(object.data)  # fill it in from a Mesh
                    bm.verts.ensure_lookup_table()

                    for vertex in bm.verts:
                        if not vertex.is_manifold:
                            bm.free()
                            selectNonManifoldVertices(object)
                            raise RuntimeError('Non manifold geometry shadow mesh: ' + object.name)

                    for edge in bm.edges:
                        if len(edge.link_faces) < 2 :
                            bm.free()
                            selectNonManifoldVertices(object)
                            raise RuntimeError('Non manifold geometry shadow mesh: ' + object.name)

                    bm.free()


        def checkUV(mesh_list):  #throws error if object lacks UVs
            for object in mesh_list:
                for material in object.data.materials:
                    if material.shaderList.shaderList == 'MeshShadowVolume.fx' or material.shaderList.shaderList == 'RSkinShadowVolume.fx':
                        if len(object.data.materials) > 1:
                            raise RuntimeError('Multiple materials on shadow volume: ' + object.name + ' , remove additional materials')
                        else:
                            return
                    if object.HasCollision:
                        if len(object.data.materials) > 1:
                            raise RuntimeError('Multiple submeshes/materials on collision mesh: ' + object.name + ' , remove additional materials')
                if object.data.uv_layers:   #or material.shaderList.shaderList in settings.no_UV_Shaders:  #currently UVs are needed for everything but shadows
                    continue
                else:
                    raise RuntimeError('Missing UV: ' + object.name)

        def checkInvalidArmatureModifier(mesh_list): #throws error if armature modifier lacks rig, this would crash the exporter later and checks if skeleton in modifier doesn't match active skeleton
            activeSkeleton = bpy.context.scene.ActiveSkeleton.skeletonEnum
            for object in mesh_list:
                for modifier in object.modifiers:
                    if modifier.type == "ARMATURE":
                        if modifier.object == None:
                            raise RuntimeError('Armature modifier without selected skeleton on: ' + object.name)
                            return True
                        elif modifier.object.type != 'NoneType':
                            if modifier.object.name != activeSkeleton:
                                raise RuntimeError('Armature modifier skeleton doesnt match active skeleton on: ' + object.name)
                                return True
                for constraint in object.constraints:
                    if constraint.type == 'CHILD_OF':
                        if constraint.target is not None:
                            #print(type(constraint.target))
                            if constraint.target.name != activeSkeleton:
                                raise RuntimeError('Constraint doesnt match active skeleton on: ' + object.name)
                                return True

        def checkFaceNumber(mesh_list):  #checks if the number of faces exceeds max ushort, which is used to save the indices
            for object in mesh_list:
                if len(object.data.polygons) > 65535:
                    raise RuntimeError('Face number exceeds uShort max on object: ' + object.name + ' split mesh into multiple objects')
                    return True

        def checkAutosmooth(mesh_list):  #prints a warning if Autosmooth is used
            for object in mesh_list:
                if object.data.use_auto_smooth:
                    print('Warning: ' + object.name + ' uses autosmooth, ingame shading might not match blender, use edgesplit instead')

        def checkTranslation(mesh_list): #prints warning when translation is not default
            for object in mesh_list:
                if object.location != mathutils.Vector((0.0, 0.0, 0.0)) or object.rotation_euler != mathutils.Euler((0.0, 0.0, 0.0), 'XYZ') or object.scale != mathutils.Vector((1.0, 1.0, 1.0)):
                    print('Warning: ' + object.name + ' is not aligned with the world origin, apply translation or bind to bone')

        def checkTranslationArmature(): #prints warning when translation is not default
            armature = utils.findArmature()
            if armature != None:
                if armature.location != mathutils.Vector((0.0, 0.0, 0.0)) or armature.rotation_euler != mathutils.Euler((0.0, 0.0, 0.0), 'XYZ') or armature.scale != mathutils.Vector((1.0, 1.0, 1.0)):
                    print('Warning: active Armature is not aligned with the world origin')

        def unhide():
            hiddenList = []
            for object in bpy.data.objects:
                hiddenList.append(object.hide_render)
                object.hide_render = False
            return hiddenList

        def hide(hiddenList):
            counter = 0
            for object in bpy.data.objects:
                object.hide_render =  hiddenList[counter]
                counter += 1

        def create_export_list(collection):
            export_list = []

            if(collection.hide_viewport):
                return export_list

            for object in collection.objects:
                if(object.type == 'MESH' and (object.hide_viewport == False or self.exportHiddenObjects)):
                    export_list.append(object)

            for child in collection.children:
                export_list.extend(create_export_list(child))

            return export_list

        #hidden objects and collections can't be accessed, avoid problems
        def unhide_collections(collection_parent):
            collection_is_hidden_list = []
            for collection in collection_parent.children:
                collection_is_hidden_list.append(collection.hide_viewport)
                collection.hide_viewport = False

            for collection in collection_parent.children:
                collection_is_hidden_list.append(collection.hide_viewport)

            return collection_is_hidden_list


        def hide_collections(collection_parent, collection_is_hidden_list, counter):
            for collection in collection_parent.children:
                collection.hide_viewport = collection_is_hidden_list[counter]
                counter += 1

            for collection in collection_parent.children:
                counter = hide_collections(collection, collection_is_hidden_list, counter)

            return counter



        def exportAnimations(filePath):

            arm = utils.findArmature()
            if(arm == None or arm.animation_data == None):
                return

            #remove ending
            filePath = filePath[0:-4]
            fileNameIndex = filePath.rfind("\\") + 1
            path = filePath[0:fileNameIndex]
            fileName = filePath[fileNameIndex:]

            exporter = export_ala.AnimationExporter()

            for action in bpy.data.actions:
                arm.animation_data.action = action
                exporter.exportAnimation(filePath + "_" + action.name + ".ALA")


        mesh_list = create_export_list(bpy.context.scene.collection)

        #check if export objects satisfy requirements (has material, UVs, ...)
        checkShadowMesh(mesh_list)
        checkUV(mesh_list)
        checkFaceNumber(mesh_list)
        checkAutosmooth(mesh_list)
        checkTranslation(mesh_list)
        checkTranslationArmature()
        checkInvalidArmatureModifier(mesh_list)

        hiddenList = unhide()
        collection_is_hidden_list = unhide_collections(bpy.context.scene.collection)

        path = self.properties.filepath

        global file
        file = open(path, 'wb')  # open file in read binary mode

        bone_name_per_alo_index = create_skeleton()
        create_mesh(mesh_list, bone_name_per_alo_index)
        create_connections(mesh_list)

        file.close()
        file = None
        #removeShadowDoubles()
        hide(hiddenList)
        hide_collections(bpy.context.scene.collection, collection_is_hidden_list, 0)

        if(self.exportAnimations):
            exportAnimations(path)

        return {'FINISHED'}  # this lets blender know the operator finished successfully.

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

