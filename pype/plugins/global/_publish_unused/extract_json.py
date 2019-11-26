import os
import json
import datetime
import time

import pyblish.api
import clique


class ExtractJSON(pyblish.api.ContextPlugin):
    """ Extract all instances to a serialized json file. """

    order = pyblish.api.IntegratorOrder
    label = "JSON"
    hosts = ['maya']

    def process(self, context):

        workspace = os.path.join(
            os.path.dirname(context.data["currentFile"]), "workspace",
            "instances")

        if not os.path.exists(workspace):
            os.makedirs(workspace)

        output_data = []
        for instance in context:
            self.log.debug(instance['data'])

            data = {}
            for key, value in instance.data.iteritems():
                if isinstance(value, clique.Collection):
                    value = value.format()

                try:
                    json.dumps(value)
                    data[key] = value
                except KeyError:
                    msg = "\"{0}\"".format(value)
                    msg += " in instance.data[\"{0}\"]".format(key)
                    msg += " could not be serialized."
                    self.log.debug(msg)

            output_data.append(data)

        timestamp = datetime.datetime.fromtimestamp(
            time.time()).strftime("%Y%m%d-%H%M%S")
        filename = timestamp + "_instances.json"

        with open(os.path.join(workspace, filename), "w") as outfile:
            outfile.write(json.dumps(output_data, indent=4, sort_keys=True))
