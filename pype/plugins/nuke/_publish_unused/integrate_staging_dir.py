import pyblish.api
import shutil
import os


class CopyStagingDir(pyblish.api.InstancePlugin):
    """Copy data rendered into temp local directory
    """

    order = pyblish.api.IntegratorOrder - 2
    label = "Copy data from temp dir"
    hosts = ["nuke", "nukeassist"]
    families = ["render.local"]

    def process(self, instance):
        temp_dir = instance.data.get("stagingDir")
        output_dir = instance.data.get("outputDir")

        # copy data to correct dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.log.info("output dir has been created")

        for f in os.listdir(temp_dir):
            self.log.info("copy file to correct destination: {}".format(f))
            shutil.copy(os.path.join(temp_dir, os.path.basename(f)),
                        os.path.join(output_dir, os.path.basename(f)))
