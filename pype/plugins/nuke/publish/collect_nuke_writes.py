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

    # targets = ["default", "process"]

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
            path += " [{0}-{1}]".format(str(first_frame), str(last_frame))
            collection = clique.parse(path)

            subset = node.name()
            # Include start and end render frame in label
            label = "{subset} ({start}-{end})".format(subset=subset,
                                                      start=int(first_frame),
                                                      end=int(last_frame))

            # Create instance
            instance = context.create_instance(subset)
            instance.add(node)

            # Adding/Checking publish and render target attribute
            if "farm" not in node.knobs():
                knob = nuke.Boolean_Knob("farm", "Farm Rendering")
                knob.setValue(False)
                node.addKnob(knob)

            # Adding/Checking publish and render target attribute
            if "render" not in node.knobs():
                knob = nuke.Boolean_Knob("render", "Render")
                knob.setValue(False)
                node.addKnob(knob)

            instance.data.update({
                "asset": os.environ["AVALON_ASSET"],  # todo: not a constant
                "path": nuke.filename(node),
                "subset": subset,
                "outputDir": os.path.dirname(nuke.filename(node)),
                "ext": ext,  # todo: should be redundant
                "label": label,
                "family": "render",
                "publish": node.knob("publish").value(),
                "collection": collection,
                "startFrame": first_frame,
                "endFrame": last_frame,
                "output_type": output_type
            })

            if node.knob('render').value():
                instance.data["families"] = ["render.local"]
                if node.knob('farm').value():
                    instance.data["families"] = ["render.farm"]
            else:
                instance.data["families"] = ["prerendered.frames"]

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=self.sort_by_family)

        return context

    def sort_by_family(self, instance):
        """Sort by family"""
        return instance.data.get("families", instance.data.get("family"))
