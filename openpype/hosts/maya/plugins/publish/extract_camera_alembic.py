import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api import lib


class ExtractCameraAlembic(openpype.api.Extractor):
    """Extract a Camera as Alembic.

    The cameras gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    """

    label = "Camera (Alembic)"
    hosts = ["maya"]
    families = ["camera"]
    bake_attributes = []

    def process(self, instance):

        # Collect the start and end including handles
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        step = instance.data.get("step", 1.0)
        bake_to_worldspace = instance.data("bakeToWorldSpace", True)

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, leaf=True, shapes=True, long=True,
                          dag=True, type="camera")

        # validate required settings
        assert len(cameras) == 1, "Not a single camera found in extraction"
        assert isinstance(step, float), "Step must be a float value"
        camera = cameras[0]

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.abc".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform alembic extraction
        with lib.maintained_selection():
            cmds.select(camera, replace=True, noExpand=True)

            # Enforce forward slashes for AbcExport because we're
            # embedding it into a job string
            path = path.replace("\\", "/")

            job_str = ' -selection -dataFormat "ogawa" '
            job_str += ' -attrPrefix cb'
            job_str += ' -frameRange {0} {1} '.format(start, end)
            job_str += ' -step {0} '.format(step)

            if bake_to_worldspace:
                transform = cmds.listRelatives(camera,
                                               parent=True,
                                               fullPath=True)[0]
                job_str += ' -worldSpace -root {0}'.format(transform)

            job_str += ' -file "{0}"'.format(path)

            # bake specified attributes in preset
            assert isinstance(self.bake_attributes, (list, tuple)), (
                "Attributes to bake must be specified as a list"
            )
            for attr in self.bake_attributes:
                self.log.info("Adding {} attribute".format(attr))
                job_str += " -attr {0}".format(attr)

            with lib.evaluation("off"):
                with lib.suspended_refresh():
                    cmds.AbcExport(j=job_str, verbose=False)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": dir_path,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
