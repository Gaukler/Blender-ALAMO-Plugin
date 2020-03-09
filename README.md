# Blender-ALAMAO-Plugin

A plugin that allow reading and writing of ALAMO-Engine model(.alo) and animation(.ala) files.  
Specifically designed to work with Empire at War: Forces of Corruption.

# Getting Started 

Tested with Blender 2.82. Download the repository. Put the "io_alamo_tools" folder into "Blender 2.82/2.82/scripts/addons/".  
The plugin has to be enabled in Blender. See the official [documentation](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html).  
If everything worked the Import and Export menus now list options for .ALO and .ALA files.  

## Supported formats 

The exporter supports the .alo model format used in both Empire at War and it's addon Forces of Corruption.  
The animation format differs between the base game and the addon. Only the latter is supported.  
If necessary animations can be converted with an external [tool](https://modtools.petrolution.net/tools/AnimationConverter).

# Exporting Objects 

When exporting or importing it's a good idea to open the Blender [console](https://docs.blender.org/manual/en/latest/advanced/command_line/introduction.html). 
Warnings and errors are displayed here.   
Common issues when exporting include missing UVs or vertex weights when using shaders that need them and not assigning a material.  

## Transform

Every object should remain without an object level transformation, so the origin should remain at the center without rotation
and scaling.  
Object transforms will be ignored when exporting. To move an object to a specific location it has to be attached to a bone.  
This is done by using a [child of constraint](https://docs.blender.org/manual/en/latest/animation/constraints/relationship/child_of.html).  
To automate the process the 'Create Constraint Bone' button can be used. An active armature has to be selected and the selected 
object must not have a child of constraint. This will create a new bone in the active skeleton at using the transform of the object. The object will be constrained to the bone and the transform will be reset. As a result the object should remain at the same position and rotation. 

## Shadow meshes

Shadow meshes are used ingame to render shadows using [shadow volumes](https://en.wikipedia.org/wiki/Shadow_volume).  
A mesh is considered a shadow mesh when it uses the corresponding shader: 'MeshShadowVolume.fx' or 'RSkinShadowVolume.fx'.  
Shadow volumes have strict requirements. They need to be water tight, otherwise artifacts will occur.  
Furthermore the exporter requires the mesh to 
[be non-manifold](https://docs.blender.org/manual/en/latest/glossary/index.html#term-non-manifold).  
When trying to export a non manifold shadow mesh the exporter will fail 
with an appropriate error message and automatically select the problematic geometry.  
The problematic geometry can be manually selected using a Blender 
[function](https://docs.blender.org/manual/en/latest/modeling/meshes/selecting.html#select-all-by-trait).  
Note that the exporter is stricter than the game when it comes to shadow meshes. 
That means imported models might not be exportable without manually fixing the shadow mesh. 
However it also means that an exported shadow mesh should not be able to cause artifacts ingame.  

# UI

## Sidebar

The sidebar(default hotkey: 'N') offers an ALAMO properties option. 
This lists the file format specific properties of the active object.  
The avaible properties change depending on the mode and object type.

Scene propierties(always avaible): 
 - ActiveSkeleton: Files can only contain a single skeleton. Choose the skeleton that is used when exporting
 - AnimationEndFrame: per action, length of the animation

Object properties(Mesh in object-mode): 
 - HasCollision: treated as collider ingame
 - Hidden: invisible ingame
 
Bone properties (Bone in edit-mode): 
 - Visible: Visibility of attached object
 - EnableProxy: bone is a proxy to spawn effects ingame, enables additional options: 
 - proxyIsHidden: flag that determines if the proxy is initially hidden
 - altDecreaseStayHidden: prevents proxies to become visible when the alt level decreases
 - ProxyName: name of the effect to be attached to the proxy
 
 Bone properties (Bone in pose-mode):
  - proxyIsHiddenAnimation: animated visibility of the proxy, when hovering over it with mouse: press 'I' to set keyframe 
 
 ## Alamo material properties

Section in the Material Properties tab dedicated to shader settings, including textures.  
The shader to be used ingame can be selected from the shaderList. The avaible options change depending on the shader.  
Most options can be left at default values, however textures should be chosen.  
To do this load the texture into Blender as an image. The texture options offer an dropdown menu with all avaible images.  
Note that only the texture name is written to the file, the texture itself must be placed in the appropriate 
mod directory in order to be found by the game.  

# Animations 

When exporting an animation the current animation from the 3D-view is exported. 
Multiple animations can be stored in Blender using the [action editor](https://docs.blender.org/manual/en/latest/editors/dope_sheet/action.html).  
Animations can be exported in bulk by checking the 'Export Animations' property when exporting a model. This will export every 
action into a separate animation file.  

Scaling in animations is unsupported at the moment. 

# Adding custom shaders 

All shader settings are stored in 'settings.py'.  
The 'material_parameter_dict' contains a shader name as a key. The corresponding item is a list of strings. 
Every string is a shader parameter. Every paramater name needs to match the shaders HLSL parameter name exactly.  
If a new parameter is used that is not yet used by another shader it has to be added to Blenders material properties.  
This is done in 'register()' function in '__init__.py'. Adding the property is a single line of code, for reference look at the 
existing code and the Blender [documentation](https://docs.blender.org/api/current/bpy.props.html). 

Every shader also needs a vertex format. This tells the engine what vertex data to pass to the vertex shader. 
This is implemented with a second dictionary called 'vertex_format_dict', with the key being the shader name and the item the formats name as a string.  

If a shader uses normal mapping its name has to be added to the 'bumpMappingList' list.  

# References 

[Breakdown](https://modtools.petrolution.net/docs/AlaFileFormat) of the Alamo Object File Format.  
[Breakdown](https://modtools.petrolution.net/docs/AloFileFormat) of the Alamo Animation File Format.
