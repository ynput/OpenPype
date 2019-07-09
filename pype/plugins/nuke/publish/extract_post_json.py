import os
import json
import datetime
import time

import clique
from pprint import pformat
import pyblish.api


class ExtractJSON(pyblish.api.ContextPlugin):
    """ Extract all instances to a serialized json file. """

    order = pyblish.api.IntegratorOrder + 1
    label = "Extract to JSON"
    families = ["write"]

    def process(self, context):
        workspace = os.path.join(
            os.path.dirname(context.data["currentFile"]), "workspace",
            "instances")

        if not os.path.exists(workspace):
            os.makedirs(workspace)

        context_data = context.data.copy()
        unwrapped_instance = []
        for i in context_data["instances"]:
            unwrapped_instance.append(i.data)

        context_data["instances"] = unwrapped_instance

        timestamp = datetime.datetime.fromtimestamp(
            time.time()).strftime("%Y%m%d-%H%M%S")
        filename = timestamp + "_instances.json"

        with open(os.path.join(workspace, filename), "w") as outfile:
            outfile.write(pformat(context_data, depth=20))

    def serialize(self, data):
        """
        Convert all nested content to serialized objects

        Args:
            data (dict): nested data

        Returns:
            dict: nested data
        """

        def encoding_obj(value):
            try:
                value = str(value).replace("\\", "/")
                # value = getattr(value, '__dict__', str(value))
            except Exception:
                pass
            return value

        for key, value in dict(data).items():
            if key in ["records", "instances", "results"]:
                # escape all record objects
                data[key] = None
                continue

            if hasattr(value, '__module__'):
                # only deals with module objects
                if "plugins" in value.__module__:
                    # only dealing with plugin objects
                    data[key] = str(value.__module__)
                else:
                    if ".lib." in value.__module__:
                        # will allow only anatomy dict
                        data[key] = self.serialize(value)
                    else:
                        data[key] = None
                    continue
                continue

            if isinstance(value, dict):
                # loops if dictionary
                data[key] = self.serialize(value)

            if isinstance(value, (list or tuple)):
                # loops if list or tuple
                for i, item in enumerate(value):
                    value[i] = self.serialize(item)
                data[key] = value

            data[key] = encoding_obj(value)

        return data
