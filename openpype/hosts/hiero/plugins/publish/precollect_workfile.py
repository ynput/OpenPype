import os
import tempfile
from pprint import pformat

import pyblish.api
from Qt.QtGui import QPixmap

import hiero.ui

from openpype.pipeline import legacy_io
from openpype.hosts.hiero import api as phiero
from openpype.hosts.hiero.api.otio import hiero_export


class PrecollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    label = "Precollect Workfile"
    order = pyblish.api.CollectorOrder - 0.491

    def process(self, context):

        asset = legacy_io.Session["AVALON_ASSET"]
        subset = "workfile"
        project = phiero.get_current_project()
        active_timeline = hiero.ui.activeSequence()
        fps = active_timeline.framerate().toFloat()

        # adding otio timeline to context
        otio_timeline = hiero_export.create_otio_timeline()

        # get workfile thumnail paths
        tmp_staging = tempfile.mkdtemp(prefix="pyblish_tmp_")
        thumbnail_name = "workfile_thumbnail.png"
        thumbnail_path = os.path.join(tmp_staging, thumbnail_name)

        # search for all windows with name of actual sequence
        _windows = [w for w in hiero.ui.windowManager().windows()
                    if active_timeline.name() in w.windowTitle()]

        # export window to thumb path
        QPixmap.grabWidget(_windows[-1]).save(thumbnail_path, 'png')

        # thumbnail
        thumb_representation = {
            'files': thumbnail_name,
            'stagingDir': tmp_staging,
            'name': "thumbnail",
            'thumbnail': True,
            'ext': "png"
        }

        # get workfile paths
        curent_file = project.path()
        staging_dir, base_name = os.path.split(curent_file)

        # creating workfile representation
        workfile_representation = {
            'name': 'hrox',
            'ext': 'hrox',
            'files': base_name,
            "stagingDir": staging_dir,
        }

        instance_data = {
            "name": "{}_{}".format(asset, subset),
            "asset": asset,
            "subset": "{}{}".format(asset, subset.capitalize()),
            "item": project,
            "family": "workfile",
            "families": [],
            "representations": [workfile_representation, thumb_representation]
        }

        # create instance with workfile
        instance = context.create_instance(**instance_data)

        # update context with main project attributes
        context_data = {
            "activeProject": project,
            "activeTimeline": active_timeline,
            "otioTimeline": otio_timeline,
            "currentFile": curent_file,
            "colorspace": self.get_colorspace(project),
            "fps": fps
        }
        self.log.debug("__ context_data: {}".format(pformat(context_data)))
        context.data.update(context_data)

        self.log.info("Creating instance: {}".format(instance))
        self.log.debug("__ instance.data: {}".format(pformat(instance.data)))
        self.log.debug("__ context_data: {}".format(pformat(context_data)))

    def get_colorspace(self, project):
        # get workfile's colorspace properties
        return {
            "useOCIOEnvironmentOverride": project.useOCIOEnvironmentOverride(),
            "lutSetting16Bit": project.lutSetting16Bit(),
            "lutSetting8Bit": project.lutSetting8Bit(),
            "lutSettingFloat": project.lutSettingFloat(),
            "lutSettingLog": project.lutSettingLog(),
            "lutSettingViewer": project.lutSettingViewer(),
            "lutSettingWorkingSpace": project.lutSettingWorkingSpace(),
            "lutUseOCIOForExport": project.lutUseOCIOForExport(),
            "ocioConfigName": project.ocioConfigName(),
            "ocioConfigPath": project.ocioConfigPath()
        }
