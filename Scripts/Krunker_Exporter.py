bl_info = {
	"name": "Krunker Level Exporter",
	"author": "Guest_Fast",
	"description": "Exports cubework for the game Krunker",
	"category": "Import-Export",
	"version":(1, 1),
	"blender":(2, 80, 0),
	"location": "File > Export",
}

import bpy
import math
import json
from mathutils import Vector, Matrix

def to_rgb(linear):
	#linear color space to rgb approximation
	# if 0 < L < 0.0031308 = L * 12.92
	# if 0.0031308 < L < 1 = 1.055 * L^(1/2.4) - 0.055
	#amazing
	converted = 0

	if 0 <= linear and linear <= 0.0031308:
		converted = linear * 12.92
	elif 0.0031308 < linear and linear <= 1:
		converted = (1.055 * (linear ** (1 / 2.4))) - 0.055

	return round(converted * 255)

def clamp(x): 
	return max(0, min(x, 255))

def build_hex_string(r, g, b):
	return "#{0:02x}{1:02x}{2:02x}".format(clamp(r), clamp(g), clamp(b))

#Validates key and checks for input value match
def property_is_value(obj, name, value):
	if name in obj and obj[name] == value:
		return True
	return False

def origin_to_z_base_distance(obj):
	obj_adjusted = obj.matrix_world.translation.copy()
	#obj_matrix_3x3 = obj.matrix_world.to_3x3().copy()
	
	#rotation_euler.to_matrix fixes problems with scaled objects, for some reason
	obj_matrix_3x3 = obj.rotation_euler.to_matrix().copy()
	z_adjust = obj.dimensions.z/2
	
	trans_local = Vector((0.0, 0.0, -z_adjust))
	trans_world = obj_matrix_3x3 @ trans_local
	obj_adjusted += trans_world
	
	corrected_location = {
		"x":obj_adjusted[0],
		"y":obj_adjusted[1],
		"z":obj_adjusted[2],
	}
	
	return corrected_location

def rotations_not_zero(obj):
	for rot in obj.rotation_euler:
		if rot != 0:
			return True   
	return False

def center_origins():
	#Center every object origin (destructively because I'm lazy and no one will care)
	#Later, softly set the origin for every object in local space to the bottom of the local blender Z-axis
	#to make compatible with Krunker
	bpy.ops.object.mode_set(mode='OBJECT')
	bpy.ops.object.select_all(action='SELECT')
	bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
	bpy.ops.object.select_all(action='DESELECT')

#Texture values correspond to the Krunker engine's internal texture values, not the Krunker editor's texture list order
def get_texture_value(name):
	texlist = {
	"0_WALL":0,
	"1_DIRT":1,
	"2_FLOOR":2,
	"3_GRID":3,
	"4_GREY":4,
	#Notice that 5 is missing, read below
	"6_ROOF":6,
	"7_FLAG":7,
	"8_GRASS":8,
	"9_CHECK":9,
	"10_LINES":10,
	"11_BRICK":11,
	"12_LINK":12,
	}

	for k in texlist:
		if k in name:
			return texlist[k]

	#5 is the default texture, and does not need an image texture link
	#Any material without a subsurface image becomes Default
	return 5

def assign_map_settings(internal_map_name, spawn_loc, sky_color):
	#You can configure these settings here as you see fit
	#They correspond to the map global settings

	sky_r = to_rgb(sky_color[0])
	sky_g = to_rgb(sky_color[1])
	sky_b = to_rgb(sky_color[2])
	sky_color_hex = build_hex_string(sky_r, sky_g, sky_b)
	
	#Blender XYZ = Krunker YZX
	testing_spawn = [
		spawn_loc[1],
		spawn_loc[2],
		spawn_loc[0],
	]

	settings = {
		"name":internal_map_name,
		"ambInd":1,
		"modURL":"",
		"terrainSeed":"",
		"terrainWidth":3000,
		"terrainHeight":3000,
		"terrainMntMlt":1,
		"terrainMntCol":"#707070",
		"terrainGrsCol":"#5e692f",
		"terrainDrtCol":"#7f6238",
		"skyDome":False,
		"skyDomeCol0":"#000000",
		"skyDomeCol1":"#000000",
		"skyDomeCol2":"#000000",
		"zone":False,
		"zoneSize":500,
		"zoneSpeed":1,
		"zoneCol0":"#c542d9",
		"zoneCol1":"#c542d9",
		"zoneCol2":"#c542d9",
		"sizeMlt":2,
		"shadowR":1024,
		"ambient":16777215,
		"light":"#f2f8fc",
		"sky":sky_color_hex,
		"fog":"#8d9aa0",
		"fogD":2000,
		"dthY":-100,
		"camPos":[0,0,0],
		"spawns":[testing_spawn],
		#The objects key is filled with the cubes data later, but is here for formatting purposes
		"objects": [],
	}
	
	return settings

def dump_cubes_data(vertical_offset, rotation_collide_disabled):
	#get cube Material = objects.active_materialbpy.
	#lul bpy.data.objects[objval].active_material.node_tree.nodes["Principled BSDF"].inputs["Name"].default_value
	#get the input needed(IE subsurface color), input[val].links[0].from_node.image.name = on-disk filename

	cubes_list = []
	
	for o in bpy.data.objects:
		if "Cube" in o.name:
			#Positioning Information
			#Blender XYZ = Krunker YZX
			#This adjustment is done in each list below
			size = [
				#x
				round(o.dimensions.y),
				#y
				round(o.dimensions.z),
				#z
				round(o.dimensions.x),
			]

			#Krunker rounds to two decimal places for rotations only
			#No other rounding permitted elsewhere
			rotation = [
				#x
				round(o.rotation_euler.y, 2),
				#y
				round(o.rotation_euler.z, 2),
				#z
				round(o.rotation_euler.x, 2),
			]

			shift = origin_to_z_base_distance(o)
			location = [
				#x
				round(shift["y"]),
				#y
				round(shift["z"]),
				#z, and add the global export vertical offset value
				(round(shift["x"] + vertical_offset)),
			]

			#Colors, textures
			material_options = o.active_material.node_tree.nodes["Principled BSDF"].inputs

			color_main = material_options["Base Color"].default_value
			color_main_r = to_rgb(color_main[0])
			color_main_g = to_rgb(color_main[1])
			color_main_b = to_rgb(color_main[2])
			color_main_hex = build_hex_string(color_main_r, color_main_g, color_main_b)

			color_emission = material_options["Emission"].default_value
			color_emission_r = to_rgb(color_emission[0])
			color_emission_g = to_rgb(color_emission[1])
			color_emission_b = to_rgb(color_emission[2])
			color_emission_hex = build_hex_string(color_emission_r, color_emission_g, color_emission_b)

			#Texture Setup
			subsurface_links = material_options["Subsurface Color"].links
			if len(subsurface_links) > 0:
				material_texture_name = subsurface_links[0].from_node.image.name
			else:
				material_texture_name = "5_DEFAULT"

			tex_value = get_texture_value(material_texture_name)

			#Begin packaging all data
			cube = {
				"p":location,
				"s":size,
				"r":rotation,
				"c":color_main_hex,
				"e":color_emission_hex,
				"t":tex_value
			}

			#Custom Properties
			#They have to be handled this way as the game sometimes checks for the presence of a
			#key to determine if a setting is active or not
			#The actual value is not always relevant (unfortunately)

			#Penetrable? Assigned value of 1 means penetrable, 0 or missing parameter means not penetrable 
			if property_is_value(o, "KR-Penetrable", 1):
				cube["pe"] = 1
			#Collidable? Parameter present (ignoring value) means NO COLLISION
			if property_is_value(o, "KR-Collidable", 0) or (
				rotation_collide_disabled and rotations_not_zero(o)):
				cube["l"] = 1
			#Visible? Parameter present (ignoring value) means NOT VISIBLE
			if property_is_value(o, "KR-Visible", 0):
				cube["v"] = 1

			cubes_list.append(cube)

	return cubes_list

def write_some_data(context,
	filepath, 
	internal_map_name, 
	y_offset, 
	rotation_collide_disable, 
	spawn_loc,
	sky_color):
	
	#Set environment to baseline
	center_origins()
	
	#Retrieve information
	cubes_data = dump_cubes_data(y_offset, rotation_collide_disable)
	level_data = assign_map_settings(internal_map_name, spawn_loc, sky_color)

	level_data["objects"] = cubes_data

	#write       
	f = open(filepath, 'w', encoding='utf-8')
	f.write(json.dumps(level_data, separators=(",", ":"))) 
	f.close()

	return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, IntVectorProperty, FloatVectorProperty
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
	"""This appears in the tooltip of the operator and in the generated docs"""
	bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
	bl_label = "Export Krunker Level"

	# ExportHelper mixin class uses this
	filename_ext = ".txt"

	filter_glob: StringProperty(
		default="*.txt",
		options={'HIDDEN'},
		maxlen=255,  # Max internal buffer length, longer would be clamped.
	)

	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.
	
	internal_map_name: StringProperty(
		name="Internal Map Name",
		description="The map name embedded in the JSON data",
		default="MAP_NAME",
	)
	
	#Raise or lower all objects on the Krunker Y (Blender Z) axis, only use integers here
	y_offset: IntProperty(
		name="Vertical Offset Modifier",
		description="Offset all cubes vertically by this value",
		default=0,
		soft_min=-1000,
		soft_max=1000,
	)
	
	#Automatically disable collision for all objects with a rotation value
	#Since rotations almost always break collision, a global disable is convenient
	remove_rotated_object_collisions: BoolProperty(
		name="Disable All Rotated Objects' Collisions",
		description="Any object with a rotation that is not 0 on every axis will have its collision disabled on export",
		default=False,
	)
	
	set_test_spawn_location: IntVectorProperty(
		name="Test Spawn Location (XYZ)",
		description="Modify the coordinates of the default spawn location, using the Krunker axes in XYZ format",
		soft_min=-1000,
		soft_max=1000,
	)

	set_sky_color: FloatVectorProperty(
		name="Sky Color",
		description="Sets the color of the in-game sky",
		subtype="COLOR",
		default=(0.0, 0.0, 0.0),
		min=0.0,
		max=1.0,
		)

	def execute(self, context):
		return write_some_data(context, 
			self.filepath, 
			self.internal_map_name, 
			self.y_offset, 
			self.remove_rotated_object_collisions,
			self.set_test_spawn_location,
			self.set_sky_color)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
	self.layout.operator(ExportSomeData.bl_idname, text="Krunker Level Data (.txt)")


def register():
	bpy.utils.register_class(ExportSomeData)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
	bpy.utils.unregister_class(ExportSomeData)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
	register()

	# test call
	bpy.ops.export_test.some_data('INVOKE_DEFAULT')
