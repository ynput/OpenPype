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
        self.log.debug("INSTANCE KEYS: {}".format(instance.data.keys()))
        self.log.debug("CONTEXT KEYS: {}".format(instance.context.data.keys()))
        self.log.debug("CUSTOM DATA: {}".format(instance.data.get('customData')))
        self.log.debug("LAYER NAMES: {}".format(instance.data.get('layer_names')))
        self.log.debug("RENDER LAYER: {}".format(instance.data.get('renderlayer')))
        self.log.debug("CONTEXT LAYERS DATA: {}".format(instance.context.data.get('layersData')))
        self.log.debug("CONTEXT LAYERS NAME: {}".format(instance.context.data.get('layersByName')))

        layer_name = instance.data.get('layer_names')
        render_layer = instance.data.get('renderlayer')
        custom_data = instance.data.get('customData')

        if custom_data.get(render_layer):
            custom_data[render_layer].extend(layer_name)
        else:
            custom_data[render_layer] = layer_name

        self.log.debug("CUSTOM DATA: {}".format(instance.data['customData']))

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
