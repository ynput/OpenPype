import os

from maya import cmds

import avalon.maya
import colorbleed.api

import cb.utils.maya.context as context
from cb.utils.maya.animation import bakeToWorldSpace


def massage_ma_file(path):
    """Clean up .ma file for backwards compatibility.

    Massage the .ma of baked camera to stay
    backwards compatible with older versions
    of Fusion (6.4)

    """
    # Get open file's lines
    f = open(path, "r+")
    lines = f.readlines()
    f.seek(0)  # reset to start of file

    # Rewrite the file
    for line in lines:
        # Skip all 'rename -uid' lines
        stripped = line.strip()
        if stripped.startswith("rename -uid "):
            continue

        f.write(line)

    f.truncate()  # remove remainder
    f.close()


class ExtractCameraBaked(colorbleed.api.Extractor):
    """Extract as Maya Ascii and Alembic a baked camera.

    The cameras gets baked to world space and then extracted.

    The extracted Maya ascii file gets "massaged" removing the uuid values
    so they are valid for older versions of Fusion (e.g. 6.4)

    """

    label = "Camera Baked (Maya Ascii + Alembic)"
    hosts = ["maya"]
    families = ["colorbleed.camera"]

    def process(self, instance):
        nodetype = 'camera'

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        alembic_as_baked = instance.data("cameraBakedAlembic", True)

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, leaf=True, shapes=True,
                          dag=True, type=nodetype)

        # Bake the cameras
        transforms = cmds.listRelatives(cameras, parent=True,
                                        fullPath=True) or []

        framerange = [instance.data.get("startFrame", 1),
                      instance.data.get("endFrame", 1)]

        self.log.info("Performing camera bakes for: {0}".format(transforms))
        with context.evaluation("off"):
            with context.no_refresh():
                baked = bakeToWorldSpace(transforms, frameRange=framerange)

        # Extract using the shape so it includes that and its hierarchy
        # above. Otherwise Alembic takes only the transform
        baked_shapes = cmds.ls(baked, type=nodetype, dag=True,
                               shapes=True, long=True)

        # Perform maya ascii extraction
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        self.log.info("Performing extraction..")
        with avalon.maya.maintained_selection():
            cmds.select(baked_shapes, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False,
                      channels=True,    # allow animation
                      constraints=False,
                      shader=False,
                      expressions=False)

            massage_ma_file(path)

        # Perform alembic extraction
        filename = "{0}.abc".format(instance.name)
        path = os.path.join(dir_path, filename)

        if alembic_as_baked:
            abc_shapes = baked_shapes
        else:
            # get cameras in the instance
            members = instance.data['setMembers']
            abc_shapes = cmds.ls(members, leaf=True, shapes=True, dag=True,
                                 long=True, type=nodetype)

        # Whenever the camera was baked and Maya's scene time warp was enabled
        # then we want to disable it whenever we publish the baked camera
        # otherwise we'll get double the scene time warping. But whenever
        # we *do not* publish a baked camera we want to keep it enabled. This
        # way what the artist has in the scene visually represents the output.
        with context.timewarp(state=not alembic_as_baked):
            with avalon.maya.maintained_selection():
                cmds.select(abc_shapes, replace=True, noExpand=True)

                # Enforce forward slashes for AbcExport because we're
                # embedding it into a job string
                path = path.replace("\\", "/")

                job_str = ' -selection -dataFormat "ogawa" '
                job_str += ' -attrPrefix cb'
                job_str += ' -frameRange {0} {1} '.format(framerange[0],
                                                          framerange[1])
                job_str += ' -file "{0}"'.format(path)

                with context.evaluation("off"):
                    with context.no_refresh():
                        cmds.AbcExport(j=job_str, verbose=False)

        # Delete the baked camera (using transform to leave no trace)
        cmds.delete(baked)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
