import os
import tempfile
import functools
import logging
import re
import uuid
from enum import Enum

import bpy
from bpy.app.handlers import persistent

import logging


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


bl_info = {
    "name": "Prepare scene for Deadline",
    "description": "Prepare a Blender scene for rendering to Deadline",
    "author": "Quad",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "category": "Render",
    "location": "View 3D > UI",
}


class PathsParts(Enum):
    WINDOWS = "//prod9.prs.vfx.int/fs209/Projets/2023"
    LINUX = "/prod/project"


class NodesNames(Enum):
    RENDER_LAYERS = 'R_LAYERS'
    OUTPUT_FILE = 'OUTPUT_FILE'


MODIFIERS_ATTRIBUTES_TO_REPLACE = [
    'simulation_bake_directory'
]


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
    },
    {
        'name': 'Use nodes',
        'path': 'use_nodes',
        'default': True
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
        log.info("Preparing temporary scene for Deadline's render")
        set_scene_render_properties()
        convert_cache_files_windows_path_to_linux()
        convert_modifers_windows_path_to_linux()
        set_engine('CYCLES')
        set_global_output_path()
        set_render_nodes_output_path()
        save_as_temporary_scene()

        return {'FINISHED'}


def set_scene_render_properties():
    for render_property in bpy.context.window_manager.render_bool_properties:
        set_attribute(render_property.path, render_property.value)
        log.info(f"attribute {render_property.path} has been set to {render_property.value}")

    for render_property in bpy.context.window_manager.render_list_properties:
        set_attribute(render_property.path, render_property.items)
        log.info(f"attribute {render_property.path} has been set to {render_property.value}")


def set_attribute(path, value):

    def rsetattr(obj, attr, val):
        pre, _, post = attr.rpartition('.')
        return setattr(rgetattr(obj, pre) if pre else obj, post, val)


    def rgetattr(obj, attr, *args):
        def _getattr(obj, attr):
            return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))

    rsetattr(bpy.context.scene, path, value)


def save_as_temporary_scene():
    bpy.context.window_manager.scene_filepath = bpy.data.filepath
    temporary_scene_file_path = _generate_temporary_file_path()
    if os.path.isfile(temporary_scene_file_path):
        try:
            os.remove(temporary_scene_file_path)
        except PermissionError:
            log.warning(f"Can't remove temporary scene file {temporary_scene_file_path}.")
            temporary_scene_file_path = _generate_temporary_file_path(
                suffix='_' + str(uuid.uuid4())
            )

    bpy.ops.wm.save_as_mainfile(filepath=temporary_scene_file_path)
    log.info(f"Temporary scene has been saved to {temporary_scene_file_path}")


def _generate_temporary_file_path(suffix='')
    return os.path.join(
        tempfile.gettempdir(),
        bpy.path.basename(bpy.context.blend_data.filepath) + suffix
    )


def convert_cache_files_windows_path_to_linux():
    for cache_file in bpy.data.cache_files:
        old_path = cache_file.filepath
        cache_file.filepath = _replace_paths_part(cache_file.filepath)
        log.info(f"Cache file path has updated from {old_path} to {cache_file.filepath}")

def convert_modifers_windows_path_to_linux():
    for modifier in _get_all_modifiers():
        for modifier_attribute in MODIFIERS_ATTRIBUTES_TO_REPLACE:
            path_to_replace = getattr(modifier, modifier_attribute, None)
            if not path_to_replace:
                continue

            setattr(modifier, modifier_attribute, _replace_paths_part(path_to_replace))
            new_path = getattr(modifier, modifier_attribute, None)
            log.info(f"Cache file path has updated from {path_to_replace} to {new_path}")


def _get_all_modifiers():
    modifiers = list()
    for obj in bpy.data.objects:
        modifiers.extend(obj.modifiers)

    return modifiers


def _replace_paths_part(path):
    return bpy.path.abspath(path).replace('\\', '/').replace(
        PathsParts.WINDOWS.value,
        PathsParts.LINUX.value
    )


def set_engine(engine):
    bpy.context.scene.render.engine = engine
    log.info(f"Engine has been set to {engine}")


def set_global_output_path():
    bpy.context.scene.render.filepath = bpy.context.scene.output_path
    log.info(f"Global output path has been set to {bpy.context.scene.output_path}")


def set_render_nodes_output_path():
    version = _extract_version_number_from_filepath(bpy.data.filepath)
    for output_node in [node for node in bpy.context.scene.node_tree.nodes if node.type == NodesNames.OUTPUT_FILE.value]:
        render_node = _browse_render_nodes(output_node.inputs)
        render_layer_name = render_node.layer
        output_node.base_path = bpy.context.scene.render_layer_path.format(
            render_layer_name=render_layer_name,
            version = version
        ) + '_'
        log.info(f"Output node {output_node.name} path has been set to '{output_node.base_path}'.")


def _browse_render_nodes(nodes_inputs):
    node_links = list()
    for nodes_input in nodes_inputs:
        node_links.extend(nodes_input.links)

    for node_link in node_links:
        target_node = node_link.from_node
        if target_node.type == NodesNames.RENDER_LAYERS.value:
            return target_node
        else:
            target_node = _browse_render_nodes(target_node.inputs)
            if target_node: return target_node


def _extract_version_number_from_filepath(filepath):
    version_regex = r'[^a-zA-Z\d](v\d{3})[^a-zA-Z\d]'
    results = re.search(version_regex, filepath)
    return results.groups()[-1]


class LoadPreviousScene(bpy.types.Operator):
    bl_idname = "deadline.load_previous_scene"
    bl_label = "Load previous Blender scene"
    bl_description = "Load previous Blender scene"

    def execute(self, context):
        bpy.ops.wm.open_mainfile(filepath=bpy.context.window_manager.scene_filepath)
        logging.info(f"Previous scene has been loaded from {bpy.context.window_manager.scene_filepath}")
        return {'FINISHED'}


class ExecutionOrder(bpy.types.Macro):
    bl_idname = "deadline.execute_macro"
    bl_label = "Prepare scene and render with Deadline"


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
