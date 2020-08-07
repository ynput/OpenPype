
import json
import clique
import pyblish.api
from pype.api import Anatomy

class ExtractJSON(pyblish.api.ContextPlugin):
    """ Extract all instances to a serialized json file. """

    order = pyblish.api.IntegratorOrder
    label = "Extract to JSON"

    def process(self, context):
        json_path = context.data['post_json_data_path']

        data = dict(self.serialize(context.data()))

        # instances_data = []
        # for instance in context:
        #
        #     iData = {}
        #     for key, value in instance.data.items():
        #         if isinstance(value, clique.Collection):
        #             value = value.format()
        #
        #         try:
        #             json.dumps(value)
        #             iData[key] = value
        #         except KeyError:
        #             msg = "\"{0}\"".format(value)
        #             msg += " in instance.data[\"{0}\"]".format(key)
        #             msg += " could not be serialized."
        #             self.log.debug(msg)
        #
        #     instances_data.append(iData)
        #
        # data["instances"] = instances_data

        with open(json_path, "w") as outfile:
            outfile.write(json.dumps(data, indent=4, sort_keys=True))

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
                value = getattr(value, '__dict__', value)
            except Exception:
                pass
            return value

        # self.log.info("1: {}".format(data))

        if isinstance(data, Anatomy):
            return

        if not isinstance(data, dict):
            # self.log.info("2: {}".format(data))
            return data

        for key, value in data.items():
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

            if isinstance(value, Anatomy):
                continue

            if isinstance(value, (list or tuple)):
                # loops if list or tuple
                for i, item in enumerate(value):
                    value[i] = self.serialize(item)
                data[key] = value

            data[key] = encoding_obj(value)

        return data
