import json
import pyblish.api


class ExtractJSON(pyblish.api.ContextPlugin):
    """ Extract all instances to a serialized json file. """

    order = pyblish.api.IntegratorOrder
    label = "Extract to JSON"

    def process(self, context):
        json_path = context.data['post_json_data_path']
        data = dict(context.data)
        self.log.info(data)
        with open(json_path, "w") as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
