# -*- coding: utf-8 -*-
"""Tools to work with FBX."""
import logging

from pyblish.api import Instance

from maya import cmds  # noqa
import maya.mel as mel  # noqa


class FBXExtractor:
    """Extract FBX from Maya.

        This extracts reproducible FBX exports ignoring any of the settings set
        on the local machine in the FBX export options window.

        All export settings are applied with the `FBXExport*` commands prior
        to the `FBXExport` call itself. The options can be overridden with
        their
        nice names as seen in the "options" property on this class.

        For more information on FBX exports see:
        - https://knowledge.autodesk.com/support/maya/learn-explore/caas
        /CloudHelp/cloudhelp/2016/ENU/Maya/files/GUID-6CCE943A-2ED4-4CEE-96D4
        -9CB19C28F4E0-htm.html
        - http://forums.cgsociety.org/archive/index.php?t-1032853.html
        - https://groups.google.com/forum/#!msg/python_inside_maya/cLkaSo361oE
        /LKs9hakE28kJ

        """
    @property
    def options(self):
        """Overridable options for FBX Export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        return {
            "cameras": bool,
            "smoothingGroups": bool,
            "hardEdges": bool,
            "tangents": bool,
            "smoothMesh": bool,
            "instances": bool,
            # "referencedContainersContent": bool, # deprecated in Maya 2016+
            "bakeComplexAnimation": int,
            "bakeComplexStart": int,
            "bakeComplexEnd": int,
            "bakeComplexStep": int,
            "bakeResampleAnimation": bool,
            "animationOnly": bool,
            "useSceneName": bool,
            "quaternion": str,  # "euler"
            "shapes": bool,
            "skins": bool,
            "constraints": bool,
            "lights": bool,
            "embeddedTextures": bool,
            "inputConnections": bool,
            "upAxis": str,  # x, y or z,
            "triangulate": bool
        }

    @property
    def default_options(self):
        """The default options for FBX extraction.

        This includes shapes, skins, constraints, lights and incoming
        connections and exports with the Y-axis as up-axis.

        By default this uses the time sliders start and end time.

        """

        start_frame = int(cmds.playbackOptions(query=True,
                                               animationStartTime=True))
        end_frame = int(cmds.playbackOptions(query=True,
                                             animationEndTime=True))

        return {
            "cameras": False,
            "smoothingGroups": True,
            "hardEdges": False,
            "tangents": False,
            "smoothMesh": True,
            "instances": False,
            "bakeComplexAnimation": True,
            "bakeComplexStart": start_frame,
            "bakeComplexEnd": end_frame,
            "bakeComplexStep": 1,
            "bakeResampleAnimation": True,
            "animationOnly": False,
            "useSceneName": False,
            "quaternion": "euler",
            "shapes": True,
            "skins": True,
            "constraints": False,
            "lights": True,
            "embeddedTextures": False,
            "inputConnections": True,
            "upAxis": "y",
            "triangulate": False
        }

    def __init__(self, log=None):
        # Ensure FBX plug-in is loaded
        self.log = log or logging.getLogger(self.__class__.__name__)
        cmds.loadPlugin("fbxmaya", quiet=True)

    def parse_overrides(self, instance, options):
        """Inspect data of instance to determine overridden options

        An instance may supply any of the overridable options
        as data, the option is then added to the extraction.

        """

        for key in instance.data:
            if key not in self.options:
                continue

            # Ensure the data is of correct type
            value = instance.data[key]
            if not isinstance(value, self.options[key]):
                self.log.warning(
                    "Overridden attribute {key} was of "
                    "the wrong type: {invalid_type} "
                    "- should have been {valid_type}".format(
                        key=key,
                        invalid_type=type(value).__name__,
                        valid_type=self.options[key].__name__))
                continue

            options[key] = value

        return options

    def set_options_from_instance(self, instance):
        # type: (Instance) -> None
        """Sets FBX export options from data in the instance.

        Args:
            instance (Instance): Instance data.

        """
        # Parse export options
        options = self.default_options
        options = self.parse_overrides(instance, options)
        self.log.info("Export options: {0}".format(options))

        # Collect the start and end including handles
        start = instance.data.get("frameStartHandle") or \
            instance.context.data.get("frameStartHandle")
        end = instance.data.get("frameEndHandle") or \
            instance.context.data.get("frameEndHandle")

        options['bakeComplexStart'] = start
        options['bakeComplexEnd'] = end

        # First apply the default export settings to be fully consistent
        # each time for successive publishes
        mel.eval("FBXResetExport")

        # Apply the FBX overrides through MEL since the commands
        # only work correctly in MEL according to online
        # available discussions on the topic
        _iteritems = getattr(options, "iteritems", options.items)
        for option, value in _iteritems():
            key = option[0].upper() + option[1:]  # uppercase first letter

            # Boolean must be passed as lower-case strings
            # as to MEL standards
            if isinstance(value, bool):
                value = str(value).lower()

            template = "FBXExport{0} {1}" if key == "UpAxis" else \
                "FBXExport{0} -v {1}"  # noqa
            cmd = template.format(key, value)
            self.log.info(cmd)
            mel.eval(cmd)

        # Never show the UI or generate a log
        mel.eval("FBXExportShowUI -v false")
        mel.eval("FBXExportGenerateLog -v false")

    @staticmethod
    def export(members, path):
        # type: (list, str) -> None
        """Export members as FBX with given path.

        Args:
            members (list): List of members to export.
            path (str): Path to use for export.

        """
        cmds.select(members, r=True, noExpand=True)
        mel.eval('FBXExport -f "{}" -s'.format(path))
