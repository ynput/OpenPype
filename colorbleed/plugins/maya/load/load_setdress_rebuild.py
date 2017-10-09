import pprint

from avalon import api, io, pipeline
from avalon.tools.cbloader import lib


class SetDressRebuild(api.Loader):

    families = ["colorbleed.setdress"]
    representations = ["abc"]

    label = "Rebuild Set Dress"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import json
        # from maya import cmds

        print ">>>", lib.__file__

        # Ensure
        data_file = self.fname.replace(".abc", ".json")
        with open(data_file, "r") as fp:
            build_data = json.load(fp)

        pprint.pprint(build_data)
        for _id, instances in build_data.items():
            # Rebuild filename
            for inst in instances:
                nodes = self.run_loader(_id)
                # cmds.xform(nodes, matrix=inst["matrix"])

    def run_loader(self, _id):
        # get all registered plugins
        obj_id = io.ObjectId(_id)
        loader_inst = lib.iter_loaders(obj_id)
        if loader_inst is None:
            raise RuntimeError("Could not find matching loader")

        # strip the generator layer from the found loader
        loader = list(loader_inst)[0]
        context = lib.get_representation_context(obj_id)
        loader.process(**context)
