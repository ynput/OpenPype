"""Plugin exporting json file.
"""
import os
import tempfile
import json

import pyblish.api
from openpype.hosts.tvpaint.api import lib


class ExtractJson(pyblish.api.InstancePlugin):
    """ Extract a JSON file and add it to the instance representation.
    """
    order = pyblish.api.ExtractorOrder
    label = "Extract JSON"
    hosts = ["tvpaint"]
    families = ["renderPass"]

    def process(self, instance):
        # Save to staging dir
        output_dir = instance.data.get("stagingDir")
        if not output_dir:
            # Create temp folder if staging dir is not set
            output_dir = (
                tempfile.mkdtemp(prefix="tvpaint_render_")
            ).replace("\\", "/")
            instance.data["stagingDir"] = output_dir

        self.log.info('Extract Json')
        # TODO: george script in list
        george_script_lines = "tv_clipsavestructure \"{}\" \"JSON\" \"onlyvisiblelayers\" \"true\" \"patternfolder\" \"{}\" \"patternfile\" \"{}\"".format(  # noqa
            os.path.join(output_dir, 'tvpaint'), "%ln", "%pfn_%ln.%4ii"
        )

        self.log.debug("Execute: {}".format(george_script_lines))
        lib.execute_george_through_file(george_script_lines)

        raw_json_path = os.path.join(output_dir, 'tvpaint.json')
        instance.context.data['json_output_dir'] = output_dir
        instance.context.data['raw_json_data_path'] = raw_json_path

        with open(raw_json_path) as tvpaint_json:
            tvpaint_data = json.load(tvpaint_json)

        instance.context.data['tvpaint_layers_data'] = tvpaint_data['project']['clip']['layers']  # noqa
        instance_layer = [
            layer['name'] for layer in instance.data.get('layers')
        ]

        if instance.context.data.get('instance_layers'):
            instance.context.data['instance_layers'].extend(instance_layer)
        else:
            instance.context.data['instance_layers'] = instance_layer

        tvpaint_data['project']['clip']['layers'] = []
        op_json_filename = 'openpype.json'
        op_json_path = os.path.join(output_dir, op_json_filename)
        with open(op_json_path, "w") as op_json:
            json.dump(tvpaint_data, op_json)

        json_repres = {
            "name": "json",
            "ext": "json",
            "files": op_json_filename,
            "stagingDir": output_dir,
            "tags": ["json_data"]
        }
        instance.data["representations"].append(json_repres)
        self.log.debug("Add json representation: {}".format(json_repres))
