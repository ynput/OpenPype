import os
import pyblish.api
from openpype.pipeline import (
    publish,
    OptionalPyblishPluginMixin
)
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection
)


class ExtractRedshiftProxy(publish.Extractor,
                           OptionalPyblishPluginMixin):
    """
    Extract Camera with AlembicExport
    """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract RedShift Proxy"
    hosts = ["max"]
    families = ["redshiftproxy"]

    def process(self, instance):
        container = instance.data["instance_node"]
        start = int(instance.context.data.get("frameStart"))
        end = int(instance.context.data.get("frameEnd"))

        self.log.info("Extracting Redshift Proxy...")
        stagingdir = self.staging_dir(instance)
        rs_filename = "{name}.rs".format(**instance.data)

        rs_filepath = os.path.join(stagingdir, rs_filename)

        # MaxScript command for export
        export_cmd = (
            f"""
fn ProxyExport fp selected:true compress:false connectivity:false startFrame: endFrame: camera:undefined warnExisting:true transformPivotToOrigin:false = (
	if startFrame == unsupplied then (
		startFrame = (currentTime.frame as integer)
	)

	if endFrame == unsupplied then (
		endFrame = (currentTime.frame as integer)
	)

    ret = rsProxy fp selected compress connectivity startFrame endFrame camera warnExisting transformPivotToOrigin

    ret
)
execute = ProxyExport fp selected:true compress:false connectivity:false startFrame:{start} endFrame:{end} warnExisting:false transformPivotToOrigin:bTransformPivotToOrigin

            """)    # noqa

        with maintained_selection():
            # select and export
            rt.select(container.Children)
            rt.execute(export_cmd)

        self.log.info("Performing Extraction ...")
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'rs',
            'ext': 'rs',
            # need to count the files
            'files': rs_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          rs_filepath))

        # TODO: set sequence
        def get_rsfiles(self, container, startFrame, endFrame):
            pass
