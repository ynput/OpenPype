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

        self.log.info("Registering {} items".format(len(representations)))
        io.insert_many(representations)

        # moving files
        for src, dest in traffic:
            self.log.info("Copying file .. {} -> {}".format(src, dest))
            self.copy_file(src, dest)

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
