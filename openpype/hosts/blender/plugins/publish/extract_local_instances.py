import os
import bpy
import platform

from avalon import io
import openpype.api
from openpype.lib import version_up
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api.plugin import is_local_collection


class ExtractLocalInstances(openpype.api.Extractor):
    """Extract local instance as a blend file."""

    label = "Extract local instance"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        # Get the main scene
        scene = bpy.data.scenes["Scene"]

        # Get the local instances
        local_instances_list = list()
        for collection in bpy.data.collections:
            if collection.override_library is not None:
                if collection.get("avalon"):
                    avalon_dict = collection.get("avalon")
                    if avalon_dict.get("id") == "pyblish.avalon.container":
                        if is_local_collection(collection):
                            local_instances_list.append(collection)

        self.log.info(
            "Container: %s\nRepresentation: %s", collection.name, local_instances_list
        )
        # bpy.ops.object.make_local(type='ALL')
        for collection in local_instances_list:

            # Create a temp scene
            new_scene = bpy.data.scenes.new("temp_scene")

            # List of data blocks to extract
            data_blocks = set()

            # Get library override
            library_override_collection = collection.override_library.reference
            library_override_collection_copy = library_override_collection.copy()
            # Link the collection to the temp scene
            new_scene.collection.children.link(library_override_collection_copy)

            # Rename the collection with his original name

            # Add collection to the data block to extract
            data_blocks.add(library_override_collection_copy)

            scene.name = "scene_temp"

            new_scene.name = "Scene"

            # Add the scene to the data block to extract
            data_blocks.add(new_scene)

            # Get the parent  (work file ) of the instance
            metadata = collection.get(AVALON_PROPERTY)
            parent = metadata["parent"]
            representation = io.find_one({"_id": io.ObjectId(parent)})
            self.log.info("Container: %s\nRepresentation: %s", "metadata", metadata)
            # Get the file path of the work file of the instance
            self.log.info(
                "Container: %s\nRepresentation: %s",
                "representation",
                representation,
            )
            source = representation["data"]["source"]
            low_platform = platform.system().lower()
            root_work = instance.data["projectEntity"]["config"]["roots"]["work"][
                low_platform
            ]
            path = source.replace("{root[work]}", root_work)

            self.log.info(path)
            # Get the version_up of the path
            filepath = version_up(path)
            self.log.info(filepath)
            # Save the new work version
            # save_file(filepath, copy=False)

            # bpy.data.libraries.write(filepath, data_blocks, fake_user=True)

            # Clean the scene
        #  bpy.data.scenes.remove(new_scene)
        #    scene.name = "Scene"


# {
#     "_id": ObjectId("620a29b458d8bdaf03011a4c"),
#     "type": "project",
#     "name": "Woolly",
#     "data": {
#         "code": "woolly",
#         "library_project": True,
#         "active": True,
#         "clipIn": 1,
#         "clipOut": 1,
#         "fps": 25.0,
#         "frameEnd": 1001,
#         "frameStart": 1001,
#         "handleEnd": 0,
#         "handleStart": 0,
#         "pixelAspect": 1.0,
#         "resolutionHeight": 1080,
#         "resolutionWidth": 1920,
#         "tools_env": [],
#     },
#     "schema": "openpype:project-3.0",
#     "config": {
#         "apps": [{"name": "blender/2-91"}],
#         "imageio": {
#             "hiero": {
#                 "workfile": {
#                     "ocioConfigName": "nuke-default",
#                     "ocioconfigpath": {"windows": [], "darwin": [], "linux": []},
#                     "workingSpace": "linear",
#                     "sixteenBitLut": "sRGB",
#                     "eightBitLut": "sRGB",
#                     "floatLut": "linear",
#                     "logLut": "Cineon",
#                     "viewerLut": "sRGB",
#                     "thumbnailLut": "sRGB",
#                 },
#                 "regexInputs": {
#                     "inputs": [
#                         {
#                             "regex": "[^-a-zA-Z0-9](plateRef).*(?=mp4)",
#                             "colorspace": "sRGB",
#                         }
#                     ]
#                 },
#             },
#             "nuke": {
#                 "viewer": {"viewerProcess": "sRGB"},
#                 "baking": {"viewerProcess": "rec709"},
#                 "workfile": {
#                     "colorManagement": "Nuke",
#                     "OCIO_config": "nuke-default",
#                     "customOCIOConfigPath": {"windows": [], "darwin": [], "linux": []},
#                     "workingSpaceLUT": "linear",
#                     "monitorLut": "sRGB",
#                     "int8Lut": "sRGB",
#                     "int16Lut": "sRGB",
#                     "logLut": "Cineon",
#                     "floatLut": "linear",
#                 },
#                 "nodes": {
#                     "requiredNodes": [
#                         {
#                             "plugins": ["CreateWriteRender"],
#                             "nukeNodeClass": "Write",
#                             "knobs": [
#                                 {"name": "file_type", "value": "exr"},
#                                 {"name": "datatype", "value": "16 bit half"},
#                                 {"name": "compression", "value": "Zip (1 scanline)"},
#                                 {"name": "autocrop", "value": "True"},
#                                 {"name": "tile_color", "value": "0xff0000ff"},
#                                 {"name": "channels", "value": "rgb"},
#                                 {"name": "colorspace", "value": "linear"},
#                                 {"name": "create_directories", "value": "True"},
#                             ],
#                         },
#                         {
#                             "plugins": ["CreateWritePrerender"],
#                             "nukeNodeClass": "Write",
#                             "knobs": [
#                                 {"name": "file_type", "value": "exr"},
#                                 {"name": "datatype", "value": "16 bit half"},
#                                 {"name": "compression", "value": "Zip (1 scanline)"},
#                                 {"name": "autocrop", "value": "False"},
#                                 {"name": "tile_color", "value": "0xadab1dff"},
#                                 {"name": "channels", "value": "rgb"},
#                                 {"name": "colorspace", "value": "linear"},
#                                 {"name": "create_directories", "value": "True"},
#                             ],
#                         },
#                         {
#                             "plugins": ["CreateWriteStill"],
#                             "nukeNodeClass": "Write",
#                             "knobs": [
#                                 {"name": "file_type", "value": "tiff"},
#                                 {"name": "datatype", "value": "16 bit"},
#                                 {"name": "compression", "value": "Deflate"},
#                                 {"name": "tile_color", "value": "0x23ff00ff"},
#                                 {"name": "channels", "value": "rgb"},
#                                 {"name": "colorspace", "value": "sRGB"},
#                                 {"name": "create_directories", "value": "True"},
#                             ],
#                         },
#                     ],
#                     "customNodes": [],
#                 },
#                 "regexInputs": {
#                     "inputs": [
#                         {
#                             "regex": "[^-a-zA-Z0-9]beauty[^-a-zA-Z0-9]",
#                             "colorspace": "linear",
#                         }
#                     ]
#                 },
#             },
#             "maya": {
#                 "colorManagementPreference": {
#                     "configFilePath": {"windows": [], "darwin": [], "linux": []},
#                     "renderSpace": "scene-linear Rec 709/sRGB",
#                     "viewTransform": "sRGB gamma",
#                 }
#             },
#         },
#         "roots": {
#             "work": {
#                 "windows": "C:/projects",
#                 "darwin": "/Volumes/path",
#                 "linux": "/mnt/share/projects",
#             }
#         },
#         "tasks": {
#             "Generic": {"short_name": "gener"},
#             "Art": {"short_name": "art"},
#             "Modeling": {"short_name": "mdl"},
#             "Texture": {"short_name": "tex"},
#             "Lookdev": {"short_name": "look"},
#             "Rigging": {"short_name": "rig"},
#             "Edit": {"short_name": "edit"},
#             "Layout": {"short_name": "lay"},
#             "Setdress": {"short_name": "dress"},
#             "Animation": {"short_name": "anim"},
#             "FX": {"short_name": "fx"},
#             "Lighting": {"short_name": "lgt"},
#             "Paint": {"short_name": "paint"},
#             "Compositing": {"short_name": "comp"},
#         },
#         "templates": {
#             "defaults": {
#                 "version_padding": 3,
#                 "version": "v{version:0>{@version_padding}}",
#                 "frame_padding": 4,
#                 "frame": "{frame:0>{@frame_padding}}",
#             },
#             "work": {
#                 "folder": "{root[work]}/{project[name]}/{hierarchy}/{asset}/work/{task[name]}",
#                 "file": "{project[code]}_{asset}_{task[name]}_{@version}<_{comment}>.{ext}",
#                 "path": "{@folder}/{@file}",
#             },
#             "render": {
#                 "folder": "{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/{@version}",
#                 "file": "{project[code]}_{asset}_{subset}_{@version}<_{output}><.{@frame}>.{ext}",
#                 "path": "{@folder}/{@file}",
#             },
#             "publish": {
#                 "folder": "{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/{@version}",
#                 "file": "{project[code]}_{asset}_{subset}_{@version}<_{output}><.{@frame}><_{udim}>.{ext}",
#                 "path": "{@folder}/{@file}",
#                 "thumbnail": "{thumbnail_root}/{project[name]}/{_id}_{thumbnail_type}.{ext}",
#             },
#             "hero": {
#                 "folder": "{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/hero",
#                 "file": "{project[code]}_{asset}_{subset}_hero<_{output}><.{frame}>.{ext}",
#                 "path": "{@folder}/{@file}",
#             },
#             "delivery": {},
#             "unreal": {
#                 "folder": "{root[work]}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/{@version}",
#                 "file": "{subset}_{@version}<_{output}><.{@frame}>.{ext}",
#                 "path": "{@folder}/{@file}",
#             },
#             "others": {},
#         },
#     },
# }
{
    "schema": "openpype:container-2.0",
    "id": "pyblish.avalon.container",
    "name": "Mickey_modelDefault",
    "namespace": "Model_001",
    "loader": "BlendModelLoader",
    "representation": "6220bd448f608ff3604ab850",
    "libpath": "C:\\projects\\Woolly\\Character\\Mickey\\publish\\model\\modelDefault\\v020\\woolly_Mickey_modelDefault_v020.blend",
    "asset_name": "Mickey_modelDefault",
    "parent": "6220bd448f608ff3604ab84f",
    "family": "model",
    "objectName": "Model_001",
}
