bl_info = {
    "name": "Krunker Object Fit To Grid",
    "author": "Guest_Fast",
    "description": "Corrects object scaling and location for Krunker (Shift-F in Object Mode)",
    "version":(1, 0),
    "blender":(2, 80, 0),
    "category": "Object",
    "location": "Object > Snap"
}

import bpy

def align_verts_to_grid():
    obj = bpy.ops.object
    mesh = bpy.ops.mesh
    view = bpy.ops.view3d
    previous_mode = bpy.context.mode

    #Snap verts to the nearest grid points
    obj.mode_set(mode="EDIT")
    mesh.select_all(action="SELECT")
    view.snap_selected_to_grid()
    mesh.select_all(action="DESELECT")
        
    #Recenter origin
    #As long as you're at a multiple of 2 grid scale, this position should always be correctly centered
    obj.mode_set(mode="OBJECT")
    obj.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    if previous_mode == "EDIT_MESH":
        obj.mode_set(mode="EDIT")
    else:
        obj.mode_set(mode="OBJECT")
        

class ObjectFit(bpy.types.Operator):
    """Objects Fit To Grid"""      # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "object.all_faces_to_grid"        # unique identifier for buttons and menu items to reference.
    bl_label = "Snap all selected object's faces to the nearest grid location"         # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # enable undo for the operator.

    def execute(self, context):        # execute() is called by blender when running the operator.

        align_verts_to_grid()
        
        return {'FINISHED'}            # this lets blender know the operator finished successfully.

addon_keymaps = []

def register():
    bpy.utils.register_class(ObjectFit)

    # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    km2 = wm.keyconfigs.addon.keymaps.new(name='Mesh', space_type='EMPTY')
    
    kmi = km.keymap_items.new(ObjectFit.bl_idname, 'F', 'PRESS', ctrl=False, shift=True)
    kmi2 = km2.keymap_items.new(ObjectFit.bl_idname, 'F', 'PRESS', ctrl=False, shift=True)

    addon_keymaps.append(km)
    addon_keymaps.append(km2)
    
def unregister():
    bpy.utils.unregister_class(ObjectFit)

    # handle the keymap
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    # clear the list
    del addon_keymaps[:]
    
    
# This allows you to run the script directly from blenders text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()