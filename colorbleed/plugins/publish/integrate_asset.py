import json
import os
import errno
import shutil

import colorbleed.maya.lib as lib

import pyblish.api
from avalon import io


class IntegrateAsset(pyblish.api.InstancePlugin):
    """Write to files and metadata

    This plug-in exposes your data to others by encapsulating it
    into a new version.

    Schema:
        Data is written in the following format.
         ____________________
        |                    |
        | version            |
        |  ________________  |
        | |                | |
        | | representation | |
        | |________________| |
        | |                | |
        | | ...            | |
        | |________________| |
        |____________________|

    """

    label = "Integrate Asset"
    order = pyblish.api.IntegratorOrder + 0.1
    families = ["colorbleed.model",
                "colorbleed.rig",
                "colorbleed.animation",
                "colorbleed.camera",
                "colorbleed.lookdev",
                "colorbleed.texture",
                "colorbleed.historyLookdev",
                "colorbleed.group"]

    def process(self, instance):

        # get needed data
        traffic = instance.data["traffic"]
        representations = instance.data["representations"]
        version_folder = instance.data["versionFolder"]
        family = instance.data["family"]
        resources = instance.data("resources", [])

        self.log.info("Registering {} items".format(len(representations)))
        io.insert_many(representations)

        # moving files
        for src_dest in traffic:
            src, dest = src_dest
            self.log.info("Copying file .. {} -> {}".format(src, dest))
            self.copy_file(src, dest)

        if family == "colorbleed.texture":
            try:
                lib.remap_resource_nodes(resources, folder=version_folder)
            except Exception as e:
                self.log.error(e)

        if family == "colorbleed.lookdev":
            try:
                tmp_dir = lib.maya_temp_folder()
                resource_file = os.path.join(tmp_dir, "resources.json")
                with open(resource_file, "r") as f:
                    resources = json.load(f)
                lib.remap_resource_nodes(resources)
            except Exception as e:
                self.log.error(e)

        self.log.info("Removing temporary files and folders ...")
        stagingdir = instance.data["stagingDir"]
        shutil.rmtree(stagingdir)

    def copy_file(self, src, dst):
        """ Copy given source to destination

        Arguments:
            src (str): the source file which needs to be copied
            dst (str): the destination of the sourc file
        Returns:
            None
        """

        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        shutil.copy(src, dst)