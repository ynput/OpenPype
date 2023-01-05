# -*- coding: utf-8 -*-

__author__ = "Daniel Flehner Heen"
__credits__ = ["Jakub Jezek", "Daniel Flehner Heen"]

import os
import hiero.core
from hiero.core import util

import opentimelineio as otio
from openpype.hosts.hiero.api.otio import hiero_export

class OTIOExportTask(hiero.core.TaskBase):

    def __init__(self, initDict):
        """Initialize"""
        hiero.core.TaskBase.__init__(self, initDict)
        self.otio_timeline = None

    def name(self):
        return str(type(self))

    def startTask(self):
        self.otio_timeline = hiero_export.create_otio_timeline()

    def taskStep(self):
        return False

    def finishTask(self):
        try:
            exportPath = self.resolvedExportPath()

            # Check file extension
            if not exportPath.lower().endswith(".otio"):
                exportPath += ".otio"

            # check export root exists
            dirname = os.path.dirname(exportPath)
            util.filesystem.makeDirs(dirname)

            # write otio file
            hiero_export.write_to_file(self.otio_timeline, exportPath)

        # Catch all exceptions and log error
        except Exception as e:
            self.setError("failed to write file {f}\n{e}".format(
                f=exportPath,
                e=e)
            )

        hiero.core.TaskBase.finishTask(self)

    def forcedAbort(self):
        pass


class OTIOExportPreset(hiero.core.TaskPresetBase):
    def __init__(self, name, properties):
        """Initialise presets to default values"""
        hiero.core.TaskPresetBase.__init__(self, OTIOExportTask, name)

        self.properties()["includeTags"] = hiero_export.include_tags = True
        self.properties().update(properties)

    def supportedItems(self):
        return hiero.core.TaskPresetBase.kSequence

    def addCustomResolveEntries(self, resolver):
        resolver.addResolver(
            "{ext}",
            "Extension of the file to be output",
            lambda keyword, task: "otio"
        )

    def supportsAudio(self):
        return True


hiero.core.taskRegistry.registerTask(OTIOExportPreset, OTIOExportTask)
