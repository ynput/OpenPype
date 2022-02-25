import os
import bpy

import openpype.api
from openpype.lib import version_up
from openpype.hosts.blender.api.workio import save_file
from openpype.lib.avalon_context import get_workdir


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

                    folder = get_workdir()

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
