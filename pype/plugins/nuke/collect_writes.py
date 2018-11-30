import os

import nuke
import pyblish.api
import clique


@pyblish.api.log
class CollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder
    label = "Collect Instances"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):

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
            first_frame = int(nuke.root()["first_frame"].getValue())
            last_frame = int(nuke.root()["last_frame"].getValue())

            if node["use_limit"].getValue():
                first_frame = int(node["first"].getValue())
                last_frame = int(node["last"].getValue())

            # Add collection
            collection = None
            path = nuke.filename(node)
            path += " [{0}-{1}]".format(
                str(first_frame),
                str(last_frame)
            )
            collection = clique.parse(path)

            # Include start and end render frame in label
            label = "{subset} ({start}-{end})".format(subset=subset,
                                                      start=int(first_frame),
                                                      end=int(last_frame))

            # Create instance
            instance = context.create_instance(subset)
            instance.add(node)

            # Adding/Checking publish and render target attribute
            if "render_local" not in node.knobs():
                knob = nuke.Boolean_Knob("render_local", "Local rendering")
                knob.setValue(False)
                node.addKnob(knob)

            instance.data.update({
                "asset": os.environ["AVALON_ASSET"],
                "path": nuke.filename(node),
                "outputDir": os.path.dirname(nuke.filename(node)),
                "ext": ext,  # todo: should be redundant
                "label": label,
                "families": ["render.local"],
                "collection": collection,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "output_type": output_type
            })

            def instanceToggled(instance, value):
                instance[0]["publish"].setValue(value)

            instance.data["instanceToggled"] = instanceToggled

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

        return context

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
