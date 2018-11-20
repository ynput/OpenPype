import os

import nuke
import pyblish.api
import clique


@pyblish.api.log
class CollectNukeWrites(pyblish.api.ContextPlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder
    label = "Writes"
    hosts = ["nuke", "nukeassist"]

    # targets = ["default", "process"]

    def process(self, context):

        instances = []
        # creating instances per write node
        for node in nuke.allNodes():
            if node.Class() != "Write":
                continue
            if node["disable"].value():
                continue

            # Determine defined file type
            ext = node["file_type"].value()

            # Determine output type
            output_type = "img"
            if ext == "mov":
                output_type = "mov"

            # Get frame range
            start_frame = int(nuke.root()["first_frame"].getValue())
            end_frame = int(nuke.root()["last_frame"].getValue())

            if node["use_limit"].getValue():
                start_frame = int(node["first"].getValue())
                end_frame = int(node["last"].getValue())

            # Add collection
            collection = None
            path = nuke.filename(node)
            path += " [{0}-{1}]".format(start_frame, end_frame)
            collection = clique.parse(path)

            subset = node.name()
            # Include start and end render frame in label
            label = "{subset} ({start}-{end})".format(subset=subset,
                                                      start=int(start_frame),
                                                      end=int(end_frame))

            # Create instance
            instance = context.create_instance(subset)
            instance.add(node)

            # Adding/Checking publish and render target attribute
            if "render_local" not in node.knobs():
                knob = nuke.Boolean_Knob("render_local", "Local rendering")
                knob.setValue(False)
                node.addKnob(knob)

            # Compare against selection
            selection = instance.context.data.get("selection", [])
            if selection:
                if list(set(instance) and set(selection)):
                    value = True
                else:
                    value = False


            instance.data.update({
                "asset": os.environ["AVALON_ASSET"],  # todo: not a constant
                "path": nuke.filename(node),
                "subset": subset,
                "outputDir": os.path.dirname(nuke.filename(node)),
                "ext": ext,  # todo: should be redundant
                "label": label,
                "families": ["render"],
                "family": "write",
                "publish": value,
                "collection": collection,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "output_type": output_type
            })
            instances.append(instance)

            self.log.info("writeNode collected: {}".format(subset))

        context.data["write_instances"] = instances

        context.data["instances"] = (
            context.data.get("instances", []) + instances)


class CollectNukeWritesPublish(pyblish.api.ContextPlugin):
    """Collect all write instances for publishing."""

    order = CollectNukeWrites.order + 0.01
    label = "Writes Publish"
    hosts = ["nuke", "nukeassist"]

    # targets = ["default"]

    def process(self, context):

        for item in context.data["write_instances"]:

            # If the collection was not generated.
            if not item.data["collection"]:
                continue

            missing_files = []
            for f in item.data["collection"]:
                # print f
                if not os.path.exists(f):
                    missing_files.append(f)

            for f in missing_files:
                item.data["collection"].remove(f)

            if not list(item.data["collection"]):
                continue

            instance = context.create_instance(item.data["name"])

            for key, value in item.data.iteritems():
                # print key, value
                instance.data[key] = value

            instance.data["families"] = ["publish"]
            instance.data["label"] += (
                " - " + os.path.basename(instance.data["collection"].format()))

            for node in item:
                instance.add(node)

            # Adding/Checking publish attribute
            if "publish" not in node.knobs():
                knob = nuke.Boolean_Knob("publish", "Publish")
                knob.setValue(False)
                node.addKnob(knob)

            value = bool(node["publish"].getValue())

            # Compare against selection
            selection = instance.context.data.get("selection", [])
            if selection:
                if list(set(instance) & set(selection)):
                    value = True
                else:
                    value = False

            instance.data["publish"] = value

            def instanceToggled(instance, value):
                # Removing and adding the knob to support NukeAssist, where
                # you can't modify the knob value directly.
                instance[0].removeKnob(instance[0]["publish"])
                knob = nuke.Boolean_Knob("publish", "Publish")
                knob.setValue(value)
                instance[0].addKnob(knob)

            instance.data["instanceToggled"] = instanceToggled
