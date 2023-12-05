#
#Copyright 2017-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 2 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
import subprocess
import sys
import tempfile
import logging
import functools

import bpy
from bpy.app.handlers import persistent


bl_info = {
    "name": "Prepare scene for Deadline",
    "description": "Prepare a Blender scene for rendering to Deadline",
    "author": "Quad",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "category": "Render",
    "location": "Render > Prepare scene for Deadline",
}


RENDER_PROPERTIES_SELECTORS = [
    {
        'name': 'Device',
        'path': 'cycles.device',
        'values': [
            ('CPU', 'CPU', 'CPU'),
            ('GPU', 'GPU', 'GPU')
        ],
        'default': 'CPU'
    }
]


RENDER_PROPERTIES_CHECKBOX = [
    {
        'name': 'Use single layer',
        'path': 'render.use_single_layer',
        'default': False
    },
    {
        'name': 'Use Simplify',
        'path': 'render.use_simplify',
        'default': False
    },
    {
        'name': 'Use motion blur',
        'path': 'render.use_motion_blur',
        'default': True
    },
    {
        'name': 'Render region',
        'path': 'render.use_border',
        'default': False
    }
]


def generate_enums_from_render_selectors(self, context):

    def _get_render_property_from_name(name):
         return next(
              iter(
                   render_property for render_property in RENDER_PROPERTIES_SELECTORS
                   if render_property['name'] == name
              )
         )

    items=[]
    for values in _get_render_property_from_name(self.name)['values']:
        items.append(values)

    return items


@persistent
def populate_render_properties(dummy=None):

        def _set_common_infos(item, render_property):
            item.value = render_property['default']
            item.name = render_property['name']
            item.path = render_property['path']

        bpy.context.window_manager.render_bool_properties.clear()
        bpy.context.window_manager.render_list_properties.clear()
        for render_property in RENDER_PROPERTIES_CHECKBOX:
            item = bpy.context.window_manager.render_bool_properties.add()
            _set_common_infos(item, render_property)

        for render_property in RENDER_PROPERTIES_SELECTORS:
            item = bpy.context.window_manager.render_list_properties.add()
            _set_common_infos(item, render_property)


class RenderBoolProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property name")
    path: bpy.props.StringProperty(name="Path to access property")
    value: bpy.props.BoolProperty(name="Default value", default=True)


class RenderListProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property name")
    path: bpy.props.StringProperty(name="Path to access property")
    items: bpy.props.EnumProperty(name="Selectable values", items=generate_enums_from_render_selectors)


class PrepareAndRenderScene(bpy.types.Panel):
    bl_idname = "deadline.prepare_and_render_scene"
    bl_label = "Prepare Scene for render with Deadline"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        for render_property in bpy.context.window_manager.render_bool_properties:
            col.prop(render_property, 'value', text=render_property.name)

        col.separator()
        for render_property in bpy.context.window_manager.render_list_properties:
            col.prop(render_property, 'items', text=render_property.name)

        col.separator()
        col.operator("deadline.execute_macro", icon="MESH_CUBE")


class PrepareTemporaryFile(bpy.types.Operator):
    bl_idname = "deadline.prepare_temporary_scene"
    bl_label = "Prepare Render Scene"
    bl_description = "Create temporary blender file and set properties"

    def execute(self, context):
        bpy.context.window_manager.scene_filepath = bpy.data.filepath
        temporary_scene_file_path = os.path.join(
            tempfile.gettempdir(),
            bpy.path.basename(bpy.context.blend_data.filepath)
        )
        if os.path.isfile(temporary_scene_file_path):
            os.remove(temporary_scene_file_path)

        for render_property in bpy.context.window_manager.render_bool_properties:
            set_attribute(render_property.path, render_property.value)

        for render_property in bpy.context.window_manager.render_list_properties:
            set_attribute(render_property.path, render_property.items)


        bpy.ops.wm.save_as_mainfile(filepath=temporary_scene_file_path)

        return {'FINISHED'}


def set_attribute(path, value):

    def rsetattr(obj, attr, val):
        pre, _, post = attr.rpartition('.')
        return setattr(rgetattr(obj, pre) if pre else obj, post, val)


    def rgetattr(obj, attr, *args):
        def _getattr(obj, attr):
            return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))

    rsetattr(bpy.context.scene, path, value)


class LoadPreviousScene(bpy.types.Operator):
    bl_idname = "deadline.load_previous_scene"
    bl_label = "Load previous Blender scene"
    bl_description = "Load previous Blender scene"

    def execute(self, context):
        print('LoadPreviousScene')
        bpy.ops.wm.open_mainfile(filepath=bpy.context.window_manager.scene_filepath)
        print("Everything is complete")
        return {'FINISHED'}


class ExecutionOrder(bpy.types.Macro):
    bl_idname = "deadline.execute_macro"
    bl_label = "Execution order"


def register():
        bpy.utils.register_class(PrepareTemporaryFile)
        bpy.utils.register_class(LoadPreviousScene)
        bpy.utils.register_class(ExecutionOrder)
        bpy.utils.register_class(PrepareAndRenderScene)
        bpy.utils.register_class(RenderBoolProperty)
        bpy.utils.register_class(RenderListProperty)

        bpy.types.WindowManager.scene_filepath = bpy.props.StringProperty('')
        bpy.types.WindowManager.render_bool_properties = bpy.props.CollectionProperty(type=RenderBoolProperty)
        bpy.types.WindowManager.render_list_properties = bpy.props.CollectionProperty(type=RenderListProperty)

        ExecutionOrder.define("DEADLINE_OT_prepare_temporary_scene")
        ExecutionOrder.define("OPS_OT_submit_blender_to_deadline")
        ExecutionOrder.define("DEADLINE_OT_load_previous_scene")

        bpy.app.handlers.load_post.append(populate_render_properties)

        populate_render_properties()


def unregister():
        bpy.utils.unregister_class(PrepareTemporaryFile)
        bpy.utils.unregister_class(LoadPreviousScene)
        bpy.utils.unregister_class(ExecutionOrder)
        bpy.utils.unregister_class(PrepareAndRenderScene)
        bpy.utils.unregister_class(RenderBoolProperty)
        bpy.utils.unregister_class(RenderListProperty)

        del bpy.types.WindowManager.scene_filepath
        del bpy.types.WindowManager.render_bool_properties
        del bpy.types.WindowManager.render_list_properties

        bpy.app.handlers.load_post.remove(populate_render_properties)
