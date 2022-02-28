import os
import bpy
import platform

from avalon import io
import openpype.api
from openpype.lib import version_up
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractLocalInstances(openpype.api.Extractor):
    """Extract local instance as a blend file."""

    label = "Extract local instance"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = "truc.blend"
        # filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        scene = bpy.data.scenes["Scene"]

        new_scene = bpy.data.scenes.new("temp_scene")

        for collection in bpy.data.collections:
            if collection.get("avalon"):
                avalon_dict = collection.get("avalon")
                if avalon_dict.get("id") == "pyblish.avalon.container":
                    self.log.info(
                        "Extracted instance '%s' to: %s",
                        collection.name,
                        avalon_dict["id"],
                    )

                    data_blocks = set()
                    original_container_name = collection["avalon"][
                        "original_container_name"
                    ]
                    name_space = collection["avalon"]["namespace"]
                    self.log.info(
                        "Extracted instance '%s' to: %s", collection.name, filepath
                    )

                    new_scene.collection.children.link(collection)

                    for object in collection.all_objects:
                        current_object_name = object.name
                        object.name = current_object_name.replace(name_space + ":", "")
                        mesh = object.data
                        current_mesh_name = mesh.name
                        mesh.name = current_mesh_name.replace(name_space + ":", "")
                    collection.name = original_container_name

                    data_blocks.add(collection)

                    scene.name = "scene_temp"

                    new_scene.name = "Scene"
                    data_blocks.add(new_scene)



                    path = avalon_dict.get("libpath")
                    project_doc = avalon_dict.get("project")
                    asset_doc = avalon_dict.get("asset_name")
                    task_name = avalon_dict.get("task")
                    host_name = 'blender'

                    # folder = get_workdir()
                    metadata = collection.get(AVALON_PROPERTY)
                    parent = metadata["parent"]

                    representation = io.find_one(
                        {"_id": io.ObjectId(parent)})
                    source = representation["data"]['source']
                    low_platform = platform.system().lower()
                    root_work = instance.data['projectEntity']['config']['roots']['work'][low_platform]
                    self.log.info(
                        "Extracted instance '%s' to: %s", collection.name, instance.data['projectEntity']['config']['roots']['work']['darwin']
                    )
                    path =source.replace("{root[work]}",root_work)
                    filepath = version_up(path)
                    save_file(filepath, copy=False)

                    bpy.data.libraries.write(filepath, data_blocks)
                    self.log.info(
                        "Extracted instance '%s' to: %s", collection.name, filepath
                    )
                    bpy.data.scenes.remove(new_scene)
                    scene.name = "Scene"


#         # Perform extraction
#
#         self.log.info("Performing extraction..")
#
#         data_blocks = set()
#         collection = bpy.data.collections[instance.name]
#         data_blocks.add(collection)
#         for obj in collection.objects:
#             data_blocks.add(obj)
#             # Pack used images in the blend files.
#             if obj.type == 'MESH':
#                 for material_slot in obj.material_slots:
#                     mat = material_slot.material
#                     if mat and mat.use_nodes:
#                         tree = mat.node_tree
#                         if tree.type == 'SHADER':
#                             for node in tree.nodes:
#                                 if node.bl_idname == 'ShaderNodeTexImage':
#                                     if node.image:
#                                         node.image.pack()
#
#         bpy.data.libraries.write(filepath, data_blocks)
#
#         if "representations" not in instance.data:
#             instance.data["representations"] = []
#
#         representation = {
#             'name': 'blend',
#             'ext': 'blend',
#             'files': filename,
#             "stagingDir": stagingdir,
#         }
#         instance.data["representations"].append(representation)
#
#         self.log.info("Extracted instance '%s' to: %s",
#                       instance.name, representation)
#
# import bpy
#
# filepath = "D:\Users\Dimitri\Documents\test_save_selected.blend"
# scene = bpy.data.scenes["Scene"]
# NewSc = bpy.data.scenes["Scene"].copy()
# for col in scene.collection.children:
#     NewSc.collection.children.unlink(col)
# for obj in scene.collection.objects:
#     NewSc.collection.objects.unlink(obj)
#
# data_blocks = set()
#
# collection = bpy.data.collections["Model_001"]
# original_container_name = collection["avalon"]["original_container_name"]
# name_space = collection["avalon"]["namespace"]
#
# for object in collection.objects:
#     current_object_name = object.name
#     object.name = current_object_name.replace(name_space + ":", "")
#     mesh = object.data
#     current_mesh_name = mesh.name
#     mesh.name = current_mesh_name.replace(name_space + ":", "")
# collection.name = original_container_name
#
# NewSc.collection.children.link(collection)
# data_blocks.add(collection)
#
# scene.name = "scene_temp"
# data_blocks.add(NewSc)
# NewSc.name = "Scene"
#
# bpy.data.libraries.write(filepath, data_blocks)
# bpy.data.scenes.remove(NewSc)
# scene.name = "Scene"
#   {'family': 'rig', 'name': 'Rig', 'families': ['rig'], 'subset': 'rigDefault', 'asset': 'Billy', 'task': 'Rigging', 'publish': True, 'label': 'Rig', 'assetEntity': {'_id': ObjectId('620e59ef225be1d7efc7d3f3'), 'name': 'Billy', 'type': 'asset', 'schema': 'openpype:asset-3.0', 'data': {'parents': ['Character'], 'visualParent': ObjectId('620e59ef225be1d7efc7d3f2'), 'tasks': {'Modeling': {'type': 'Modeling'}, 'Rigging': {'type': 'Rigging'}}, 'clipOut': 1, 'resolutionHeight': 1080, 'fps': 25.0, 'frameEnd': 1001, 'handleStart': 0, 'handleEnd': 0, 'tools_env': [], 'frameStart': 1001, 'resolutionWidth': 1920, 'pixelAspect': 1.0, 'clipIn': 1}, 'parent': ObjectId('620e5987225be1d7efc7d3f1')}, 'latestVersion': 7, 'projectEntity':
#       {'_id': ObjectId('620e5987225be1d7efc7d3f1'), 'type': 'project', 'name': 'WOOLLY', 'data': {'code': 'woolly', 'library_project': True, 'active': True, 'clipIn': 1, 'clipOut': 1, 'fps': 25.0, 'frameEnd': 1001, 'frameStart': 1001, 'handleEnd': 0, 'handleStart': 0, 'pixelAspect': 1.0, 'resolutionHeight': 1080, 'resolutionWidth': 1920, 'tools_env': []}, 'schema': 'openpype:project-3.0', 'config': {'apps': [{'name': 'hiero/12-2'}, {'name': 'houdini/18-5'}, {'name': 'nuke/12-2'}, {'name': 'blender/2-91'}, {'name': 'photoshop/2021'}, {'name': 'harmony/20'}, {'name': 'nukex/12-2'}, {'name': 'aftereffects/2021'}, {'name': 'unreal/4-26'}, {'name': 'resolve/stable'}, {'name': 'maya/2020'}], 'imageio': {'hiero': {'workfile': {'ocioConfigName': 'nuke-default', 'ocioconfigpath': {'windows': [], 'darwin': [], 'linux': []}, 'workingSpace': 'linear', 'sixteenBitLut': 'sRGB', 'eightBitLut': 'sRGB', 'floatLut': 'linear', 'logLut': 'Cineon', 'viewerLut': 'sRGB', 'thumbnailLut': 'sRGB'}, 'regexInputs': {'inputs': [{'regex': '[^-a-zA-Z0-9](plateRef).*(?=mp4)', 'colorspace': 'sRGB'}]}}, 'nuke': {'viewer': {'viewerProcess': 'sRGB'}, 'baking': {'viewerProcess': 'rec709'}, 'workfile': {'colorManagement': 'Nuke', 'OCIO_config': 'nuke-default', 'customOCIOConfigPath': {'windows': [], 'darwin': [], 'linux': []}, 'workingSpaceLUT': 'linear', 'monitorLut': 'sRGB', 'int8Lut': 'sRGB', 'int16Lut': 'sRGB', 'logLut': 'Cineon', 'floatLut': 'linear'}, 'nodes': {'requiredNodes': [{'plugins': ['CreateWriteRender'], 'nukeNodeClass': 'Write', 'knobs': [{'name': 'file_type', 'value': 'exr'}, {'name': 'datatype', 'value': '16 bit half'}, {'name': 'compression', 'value': 'Zip (1 scanline)'}, {'name': 'autocrop', 'value': 'True'}, {'name': 'tile_color', 'value': '0xff0000ff'}, {'name': 'channels', 'value': 'rgb'}, {'name': 'colorspace', 'value': 'linear'}, {'name': 'create_directories', 'value': 'True'}]}, {'plugins': ['CreateWritePrerender'], 'nukeNodeClass': 'Write', 'knobs': [{'name': 'file_type', 'value': 'exr'}, {'name': 'datatype', 'value': '16 bit half'}, {'name': 'compression', 'value': 'Zip (1 scanline)'}, {'name': 'autocrop', 'value': 'False'}, {'name': 'tile_color', 'value': '0xadab1dff'}, {'name': 'channels', 'value': 'rgb'}, {'name': 'colorspace', 'value': 'linear'}, {'name': 'create_directories', 'value': 'True'}]}, {'plugins': ['CreateWriteStill'], 'nukeNodeClass': 'Write', 'knobs': [{'name': 'file_type', 'value': 'tiff'}, {'name': 'datatype', 'value': '16 bit'}, {'name': 'compression', 'value': 'Deflate'}, {'name': 'tile_color', 'value': '0x23ff00ff'}, {'name': 'channels', 'value': 'rgb'}, {'name': 'colorspace', 'value': 'sRGB'}, {'name': 'create_directories', 'value': 'True'}]}], 'customNodes': []}, 'regexInputs': {'inputs': [{'regex': '[^-a-zA-Z0-9]beauty[^-a-zA-Z0-9]', 'colorspace': 'linear'}]}}, 'maya': {'colorManagementPreference': {'configFilePath': {'windows': [], 'darwin': [], 'linux': []}, 'renderSpace': 'scene-linear Rec 709/sRGB', 'viewTransform': 'sRGB gamma'}}}, 'roots': {'work': {'windows': 'C:/projects', 'darwin': '/Users/normaal/Documents/projects', 'linux': '/mnt/share/projects'}}, 'tasks': {'Generic': {'short_name': 'gener'}, 'Art': {'short_name': 'art'}, 'Modeling': {'short_name': 'mdl'}, 'Texture': {'short_name': 'tex'}, 'Lookdev': {'short_name': 'look'}, 'Rigging': {'short_name': 'rig'}, 'Edit': {'short_name': 'edit'}, 'Layout': {'short_name': 'lay'}, 'Setdress': {'short_name': 'dress'}, 'Animation': {'short_name': 'anim'}, 'FX': {'short_name': 'fx'}, 'Lighting': {'short_name': 'lgt'}, 'Paint': {'short_name': 'paint'}, 'Compositing': {'short_name': 'comp'}}, 'templates': {'defaults': {'version_padding': 3, 'version': 'v{version:0>{@version_padding}}', 'frame_padding': 4, 'frame': '{frame:0>{@frame_padding}}'}, 'work': {'folder': '{root[work]}/{project[name]}/{hierarchy}/{asset}/work/{task[name]}', 'file': '{project[code]}_{asset}_{task[name]}_{@version}<_{comment}>.{ext}', 'path': '{@folder}/{@file}'}, 'render': {'folder': '{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/{@version}', 'file': '{project[code]}_{asset}_{subset}_{@version}<_{output}><.{@frame}>.{ext}', 'path': '{@folder}/{@file}'}, 'publish': {'folder': '{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/{@version}', 'file': '{project[code]}_{asset}_{subset}_{@version}<_{output}><.{@frame}><_{udim}>.{ext}', 'path': '{@folder}/{@file}', 'thumbnail': '{thumbnail_root}/{project[name]}/{_id}_{thumbnail_type}.{ext}'}, 'hero': {'folder': '{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/hero', 'file': '{project[code]}_{asset}_{subset}_hero<_{output}><.{frame}>.{ext}', 'path': '{@folder}/{@file}'}, 'delivery': {}, 'unreal': {'folder': '{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/{@version}', 'file': '{subset}_{@version}<_{output}><.{@frame}>.{ext}', 'path': '{@folder}/{@file}'}, 'others': {}}}}
#       , 'anatomyData': {'project': {'name': 'WOOLLY', 'code': 'woolly'}, 'asset': 'Billy', 'parent': 'Character', 'hierarchy': 'Character', 'task': {'name': 'Rigging', 'type': 'Rigging', 'short': 'rig'}, 'username': 'normaal', 'app': 'blender', 'studio': {'name': 'Studio name', 'code': 'stu'}, 'd': '28', 'dd': '28', 'ddd': 'Lun', 'dddd': 'Lundi', 'm': '2', 'mm': '02', 'mmm': 'fév', 'mmmm': 'février', 'yy': '22', 'yyyy': '2022', 'H': '15', 'HH': '15', 'h': '3', 'hh': '03', 'ht': '', 'M': '36', 'MM': '36', 'S': '19', 'SS': '19', 'family': 'rig', 'subset': 'rigDefault', 'version': 8}, 'version': 8, 'publishDir': '/Users/normaal/Documents/projects/WOOLLY/Character/Billy/publish/rig/rigDefault/v008', 'resourcesDir': '/Users/normaal/Documents/projects/WOOLLY/Character/Billy/publish/rig/rigDefault/v008/resources', 'stagingDir': '/var/folders/3t/sgj4fm917b10g5rrlbhzdk380000gp/T/pyblish_tmp_c_h4x6bs'}