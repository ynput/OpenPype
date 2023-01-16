import os

import bpy

from openpype.pipeline import AVALON_CONTAINER_ID, publish
from openpype.hosts.blender.api.workio import save_file


class ExtractBlenderSceneRaw(publish.Extractor):
    """Extract as Blender Scene (raw).

    This will preserve all references, construction history, etc.
    """

    label = "Blender Scene (Raw)"
    hosts = ["blender"]
    families = ["blenderScene", "layout"]
    scene_type = "blend"

    def process(self, instance):
        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # We need to get all the data blocks for all the blender objects.
        # The following set will contain all the data blocks from version
        # 2.93 of Blender.
        data_blocks = {
            *bpy.data.actions,
            *bpy.data.armatures,
            *bpy.data.brushes,
            *bpy.data.cache_files,
            *bpy.data.cameras,
            *bpy.data.collections,
            *bpy.data.curves,
            *bpy.data.fonts,
            *bpy.data.grease_pencils,
            *bpy.data.images,
            *bpy.data.lattices,
            *bpy.data.libraries,
            *bpy.data.lightprobes,
            *bpy.data.lights,
            *bpy.data.linestyles,
            *bpy.data.masks,
            *bpy.data.materials,
            *bpy.data.metaballs,
            *bpy.data.meshes,
            *bpy.data.movieclips,
            *bpy.data.node_groups,
            *bpy.data.objects,
            *bpy.data.paint_curves,
            *bpy.data.palettes,
            *bpy.data.particles,
            *bpy.data.scenes,
            *bpy.data.screens,
            *bpy.data.shape_keys,
            *bpy.data.speakers,
            *bpy.data.sounds,
            *bpy.data.texts,
            *bpy.data.textures,
            *bpy.data.volumes,
            *bpy.data.worlds
        }

        # Some data blocks are only available in certain versions of Blender.
        version = tuple(map(int, (bpy.app.version_string.split("."))))

        if version >= (3, 0, 0):
            data_blocks |= {
                *bpy.data.pointclouds
            }

        if version >= (3, 3, 0):
            data_blocks |= {
                *bpy.data.hair_curves
            }

        # Write the datablocks in a new blend file.
        bpy.data.libraries.write(path, data_blocks)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": dir_path
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
