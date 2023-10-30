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
from openpype.pipeline import publish, OptionalPyblishPluginMixin
from pymxs import runtime as rt
from openpype.hosts.max.api import maintained_selection
from openpype.hosts.max.api.lib import suspended_refresh
from openpype.lib import BoolDef


class ExtractAlembic(publish.Extractor,
                     OptionalPyblishPluginMixin):
    order = pyblish.api.ExtractorOrder
    label = "Extract Pointcache"
    hosts = ["max"]
    families = ["pointcache"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        parent_dir = self.staging_dir(instance)
        file_name = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, file_name)

        with suspended_refresh():
            self._set_abc_attributes(instance)
            with maintained_selection():
                # select and export
                node_list = instance.data["members"]
                rt.Select(node_list)
                rt.exportFile(
                    path,
                    rt.name("noPrompt"),
                    selectedOnly=True,
                    using=rt.AlembicExport,
                )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "abc",
            "ext": "abc",
            "files": file_name,
            "stagingDir": parent_dir,
        }
        instance.data["representations"].append(representation)

    def _set_abc_attributes(self, instance):
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]
        attr_values = self.get_attr_values_from_data(instance.data)
        custom_attrs = attr_values.get("custom_attrs", False)
        if not custom_attrs:
            self.log.debug(
                "No Custom Attributes included in this abc export...")
        rt.AlembicExport.ArchiveType = rt.Name("ogawa")
        rt.AlembicExport.CoordinateSystem = rt.Name("maya")
        rt.AlembicExport.StartFrame = start
        rt.AlembicExport.EndFrame = end
        rt.AlembicExport.CustomAttributes = custom_attrs

    @classmethod
    def get_attribute_defs(cls):
        return [
            BoolDef("custom_attrs",
                    label="Custom Attributes",
                    default=False),
        ]


class ExtractCameraAlembic(ExtractAlembic):
    """Extract Camera with AlembicExport."""

    label = "Extract Alembic Camera"
    families = ["camera"]


class ExtractModel(ExtractAlembic):
    """Extract Geometry in Alembic Format"""
    label = "Extract Geometry (Alembic)"
    families = ["model"]

    def _set_abc_attributes(self, instance):
        attr_values = self.get_attr_values_from_data(instance.data)
        custom_attrs = attr_values.get("custom_attrs", False)
        if not custom_attrs:
            self.log.debug(
                "No Custom Attributes included in this abc export...")
        rt.AlembicExport.ArchiveType = rt.name("ogawa")
        rt.AlembicExport.CoordinateSystem = rt.name("maya")
        rt.AlembicExport.CustomAttributes = custom_attrs
        rt.AlembicExport.UVs = True
        rt.AlembicExport.VertexColors = True
        rt.AlembicExport.PreserveInstances = True
