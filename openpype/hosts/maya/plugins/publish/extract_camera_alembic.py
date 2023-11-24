import os

from maya import cmds

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib


class ExtractCameraAlembic(publish.Extractor,
                           publish.OptionalPyblishPluginMixin):
    """Extract a Camera as Alembic.

    The camera gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    'camera' family expects only single camera, if multiple cameras are needed,
    'matchmove' is better choice.

    """

    label = "Extract Camera (Alembic)"
    hosts = ["maya"]
    families = ["camera", "matchmove"]
    bake_attributes = []

    def process(self, instance):

        # Collect the start and end including handles
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        step = instance.data.get("step", 1.0)
        bake_to_worldspace = instance.data("bakeToWorldSpace", True)

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, leaf=True, long=True,
                          dag=True, type="camera")

        # validate required settings
        assert isinstance(step, float), "Step must be a float value"

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        filename = "{0}.abc".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform alembic extraction
        member_shapes = cmds.ls(
            members, leaf=True, shapes=True, long=True, dag=True)
        with lib.maintained_selection():
            cmds.select(
                member_shapes,
                replace=True, noExpand=True)

            # Enforce forward slashes for AbcExport because we're
            # embedding it into a job string
            path = path.replace("\\", "/")

            job_str = ' -selection -dataFormat "ogawa" '
            job_str += ' -attrPrefix cb'
            job_str += ' -frameRange {0} {1} '.format(start, end)
            job_str += ' -step {0} '.format(step)

            if bake_to_worldspace:
                job_str += ' -worldSpace'

                # if baked, drop the camera hierarchy to maintain
                # clean output and backwards compatibility
                camera_roots = cmds.listRelatives(
                    cameras, parent=True, fullPath=True)
                for camera_root in camera_roots:
                    job_str += ' -root {0}'.format(camera_root)

                for member in members:
                    descendants = cmds.listRelatives(member,
                                                     allDescendents=True,
                                                     fullPath=True) or []
                    shapes = cmds.ls(descendants, shapes=True,
                                     noIntermediate=True, long=True)
                    cameras = cmds.ls(shapes, type="camera", long=True)
                    if cameras:
                        if not set(shapes) - set(cameras):
                            continue
                        self.log.warning((
                            "Camera hierarchy contains additional geometry. "
                            "Extraction will fail.")
                        )
                    transform = cmds.listRelatives(
                        member, parent=True, fullPath=True)
                    transform = transform[0] if transform else member
                    job_str += ' -root {0}'.format(transform)

            job_str += ' -file "{0}"'.format(path)

            # bake specified attributes in preset
            assert isinstance(self.bake_attributes, (list, tuple)), (
                "Attributes to bake must be specified as a list"
            )
            for attr in self.bake_attributes:
                self.log.debug("Adding {} attribute".format(attr))
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

        self.log.debug("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
