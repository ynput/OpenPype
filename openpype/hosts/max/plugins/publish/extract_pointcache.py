# -*- coding: utf-8 -*-
"""
Export alembic file.

Note:
    Parameters on AlembicExport (AlembicExport.Parameter):

    ParticleAsMesh (bool): Sets whether particle shapes are exported
        as meshes.
    AnimTimeRange (enum): How animation is saved:
        #CurrentFrame: saves current frame
        #TimeSlider: saves the active time segments on time slider (default)
        #StartEnd: saves a range specified by the Step
    StartFrame (int)
    EnFrame (int)
    ShapeSuffix (bool): When set to true, appends the string "Shape" to the
        name of each exported mesh. This property is set to false by default.
    SamplesPerFrame (int): Sets the number of animation samples per frame.
    Hidden (bool): When true, export hidden geometry.
    UVs (bool): When true, export the mesh UV map channel.
    Normals (bool): When true, export the mesh normals.
    VertexColors (bool): When true, export the mesh vertex color map 0 and the
        current vertex color display data when it differs
    ExtraChannels (bool): When true, export the mesh extra map channels
        (map channels greater than channel 1)
    Velocity (bool): When true, export the meh vertex and particle velocity
        data.
    MaterialIDs (bool): When true, export the mesh material ID as
        Alembic face sets.
    Visibility (bool): When true, export the node visibility data.
    LayerName (bool): When true, export the node layer name as an Alembic
        object property.
    MaterialName (bool): When true, export the geometry node material name as
        an Alembic object property
    ObjectID (bool): When true, export the geometry node g-buffer object ID as
        an Alembic object property.
    CustomAttributes (bool): When true, export the node and its modifiers
        custom attributes into an Alembic object compound property.
"""
import os
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection,
    get_all_children
)


class ExtractAlembic(publish.Extractor):
    order = pyblish.api.ExtractorOrder
    label = "Extract Pointcache"
    hosts = ["max"]
    families = ["pointcache"]

    def process(self, instance):
        start = float(instance.data.get("frameStartHandle", 1))
        end = float(instance.data.get("frameEndHandle", 1))

        container = instance.data["instance_node"]

        self.log.info("Extracting pointcache ...")

        parent_dir = self.staging_dir(instance)
        file_name = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, file_name)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        parent_dir))

        abc_export_cmd = (
            f"""
AlembicExport.ArchiveType = #ogawa
AlembicExport.CoordinateSystem = #maya
AlembicExport.StartFrame = {start}
AlembicExport.EndFrame = {end}

exportFile @"{path}" #noPrompt selectedOnly:on using:AlembicExport

            """)

        self.log.debug(f"Executing command: {abc_export_cmd}")

        with maintained_selection():
            # select and export

            rt.select(get_all_children(rt.getNodeByName(container)))
            rt.execute(abc_export_cmd)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': file_name,
            "stagingDir": parent_dir,
        }
        instance.data["representations"].append(representation)
