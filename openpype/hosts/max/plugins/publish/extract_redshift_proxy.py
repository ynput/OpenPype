import os
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt
from openpype.hosts.max.api import maintained_selection


class ExtractRedshiftProxy(publish.Extractor):
    """
    Extract Redshift Proxy with rsProxy
    """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract RedShift Proxy"
    hosts = ["max"]
    families = ["redshiftproxy"]

    def process(self, instance):
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        self.log.debug("Extracting Redshift Proxy...")
        stagingdir = self.staging_dir(instance)
        rs_filename = "{name}.rs".format(**instance.data)
        rs_filepath = os.path.join(stagingdir, rs_filename)
        rs_filepath = rs_filepath.replace("\\", "/")

        rs_filenames = self.get_rsfiles(instance, start, end)

        with maintained_selection():
            # select and export
            node_list = instance.data["members"]
            rt.Select(node_list)
            # Redshift rsProxy command
            # rsProxy fp selected compress connectivity startFrame endFrame
            # camera warnExisting transformPivotToOrigin
            rt.rsProxy(rs_filepath, 1, 0, 0, start, end, 0, 1, 1)

        self.log.info("Performing Extraction ...")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'rs',
            'ext': 'rs',
            'files': rs_filenames if len(rs_filenames) > 1 else rs_filenames[0],    # noqa
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          stagingdir))

    def get_rsfiles(self, instance, startFrame, endFrame):
        rs_filenames = []
        rs_name = instance.data["name"]
        for frame in range(startFrame, endFrame + 1):
            rs_filename = "%s.%04d.rs" % (rs_name, frame)
            rs_filenames.append(rs_filename)

        return rs_filenames
