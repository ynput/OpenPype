# -*- coding: utf-8 -*-
"""Extract project for Maya"""

import os
import pyblish.api
import tde4
from mock import patch
import types
import six

from openpype.hosts.equalizer.api import (
    ExtractScriptBase,
    maintained_model_selection,
)
from openpype.lib import import_filepath
from openpype.pipeline import (
    KnownPublishError,
    OptionalPyblishPluginMixin,
    publish,
)


class ExtractMatchmoveScriptMaya(publish.Extractor,
                                 ExtractScriptBase,
                                 OptionalPyblishPluginMixin):
    """Extract Maya MEL script for matchmove.

    This is using built-in export script from 3DEqualizer.
    """

    label = "Extract Maya Script"
    families = ["matchmove"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder

    def process(self, instance = pyblish.api.Instance):
        """Extracts Maya script from 3DEqualizer.

        This method is using export script shipped with 3DEqualizer to
        maintain as much compatibility as possible. Instead of invoking it
        from the UI, it calls directly the function that is doing the export.
        For that it needs to pass some data that are collected in 3dequalizer
        from the UI, so we need to determine them from the instance itself and
        from the state of the project.

        """
        if not self.is_active(instance.data):
            return
        
        attr_data = self.get_attr_values_from_data(instance.data)
        offset = tde4.getCameraFrameOffset(tde4.getCurrentCamera())
        staging_dir = self.staging_dir(instance)
        file_path = os.path.join(staging_dir, "maya_export.mel")
        unit_scales = {
            "mm": 3,  # cm -> mm
            "cm": 1,  # cm -> cm
            "m": 2,  # cm -> m
            "in": 4,  # cm -> in
            "ft": 5,  # cm -> ft
            "yd": 6  # cm -> yd
        }
        scale_factor = unit_scales[attr_data["units"]]
        model_selection_enum = instance.data["creator_attributes"]["model_selection"]  # noqa: E501
        camera_sel = instance.data["creator_attributes"]["camera_selection"]  

        exporter_path = os.path.join(instance.data["tde4_path"], "sys_data", "py_scripts", "export_maya.py") # noqa: E501
        module = types.ModuleType("export_nuke")
        module.__file__ = exporter_path
        self.log.debug("Importing {}".format(exporter_path))
        
        def patched_getWidgetValue(requester, key):  # noqa: N802
            """Return value for given key in widget."""
            if key == "file_browser":
                return file_path
            
            elif key == "startframe_field":
                return offset
            
            elif key == "camera_selection":
                if camera_sel == "__current__":
                    return 1
                elif camera_sel == "__selected__":
                    return 2
                elif camera_sel == "__seq__":
                    return 3
                elif camera_sel == "__ref__":
                    return 4
                return 5
            
            elif key == "hide_ref_frames":
                return bool(attr_data["hide_reference_frame"]) 
            
            elif key == "model_selection":
                if model_selection_enum == "__none__":
                    return 1
                elif model_selection_enum == "__selected__":
                    return 2
                return 3
            
            elif key == "export_overscan_width_percent":
                return attr_data["overscan_percent_width"]
            
            elif key == "export_overscan_height_percent":
                return attr_data["overscan_percent_height"]
            
            elif key == "units":
                return scale_factor
            
            elif key == "export_texture":
                return bool(attr_data["export_uv_textures"])
            
        with patch("tde4.postCustomRequester", lambda *args, **kwargs: 1),\
                patch("tde4.getWidgetValue", patched_getWidgetValue),\
                patch("tde4.postQuestionRequester", lambda *args, **kwargs: None):
            with open(exporter_path, 'r') as f:
                script = f.read()
                if not "import tde4" in script:
                    script = "import tde4\n" + script
            six.exec_(script, module.__dict__)


        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': "mel",
            'ext': "mel",
            'files': "maya_export.mel",
            "stagingDir": staging_dir,
        }
        self.log.debug("output: {}".format(file_path))
        instance.data["representations"].append(representation)
