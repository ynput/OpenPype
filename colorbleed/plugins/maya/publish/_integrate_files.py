import os
import shutil
import pyblish.api

import colorbleed.api


class IntegrateFiles(colorbleed.api.Integrator):
    """Integrate Files

    Copies the transfer queue to the destinations.

    """

    order = pyblish.api.IntegratorOrder + 0.1
    label = "Transfer Files"

    def process(self, instance):
        """Copy textures from srcPath to destPath

        The files should be stored in the "integrateFiles" data on the instance. Each item in the
        list should be a dictionary with 'srcPath' and 'destPath' key values.

            - srcPath: Source path (must be absolute!)
            - destPath: Destination path (can be relative)

        """
        super(IntegrateFiles, self).process(instance)

        # Get unique texture transfers
        # (since different nodes might load same texture)
        transfers = instance.data.get("transfers", [])

        for src, dest in transfers:

            self.log.info("Copying: {0} -> {1}".format(src, dest))

            # Source is destination
            if os.path.normpath(dest) == os.path.normpath(src):
                self.log.info("Skip copy of resource file: {0}".format(src))
                continue

            # Ensure folder exists
            folder = os.path.dirname(dest)
            if not os.path.exists(folder):
                os.makedirs(folder)
            shutil.copyfile(src, dest)
