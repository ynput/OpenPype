# -*- coding: utf-8 -*-
import os

from maya import cmds  # noqa
import maya.mel as mel  # noqa
import pyblish.api
import openpype.api
from openpype.hosts.maya.api.lib import (
    root_parent,
    maintained_selection
)


class ExtractFBX(openpype.api.Extractor):
    """Extract FBX from Maya.

    This extracts reproducible FBX exports ignoring any of the settings set
    on the local machine in the FBX export options window.

    All export settings are applied with the `FBXExport*` commands prior
    to the `FBXExport` call itself. The options can be overridden with their
    nice names as seen in the "options" property on this class.

    For more information on FBX exports see:
    - https://knowledge.autodesk.com/support/maya/learn-explore/caas
    /CloudHelp/cloudhelp/2016/ENU/Maya/files/GUID-6CCE943A-2ED4-4CEE-96D4
    -9CB19C28F4E0-htm.html
    - http://forums.cgsociety.org/archive/index.php?t-1032853.html
    - https://groups.google.com/forum/#!msg/python_inside_maya/cLkaSo361oE
    /LKs9hakE28kJ

    """

    order = pyblish.api.ExtractorOrder
    label = "Extract FBX"
    families = ["fbx"]

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
            "smoothingGroups": False,
            "hardEdges": False,
            "tangents": False,
            "smoothMesh": False,
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
            "embeddedTextures": True,
            "inputConnections": True,
            "upAxis": "y",
            "triangulate": False
        }

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

    def process(self, instance):

        # Ensure FBX plug-in is loaded
        cmds.loadPlugin("fbxmaya", quiet=True)

        # Define output path
        stagingDir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(stagingDir, filename)

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.info("Extracting FBX to: {0}".format(path))

        members = instance.data["setMembers"]
        self.log.info("Members: {0}".format(members))
        self.log.info("Instance: {0}".format(instance[:]))

        # Parse export options
        options = self.default_options
        options = self.parse_overrides(instance, options)
        self.log.info("Export options: {0}".format(options))

        # Collect the start and end including handles
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

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

            template = "FBXExport{0} {1}" if key == "UpAxis" else "FBXExport{0} -v {1}"  # noqa
            cmd = template.format(key, value)
            self.log.info(cmd)
            mel.eval(cmd)

        # Never show the UI or generate a log
        mel.eval("FBXExportShowUI -v false")
        mel.eval("FBXExportGenerateLog -v false")

        # Export
        if "unrealStaticMesh" in instance.data["families"]:
            with maintained_selection():
                with root_parent(members):
                    self.log.info("Un-parenting: {}".format(members))
                    cmds.select(members, r=1, noExpand=True)
                    mel.eval('FBXExport -f "{}" -s'.format(path))
        else:
            with maintained_selection():
                cmds.select(members, r=1, noExpand=True)
                mel.eval('FBXExport -f "{}" -s'.format(path))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": stagingDir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extract FBX successful to: {0}".format(path))
