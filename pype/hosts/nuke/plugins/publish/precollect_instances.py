import nuke
import pyblish.api
from avalon import io, api
from avalon.nuke import lib as anlib


@pyblish.api.log
class PreCollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all nodes with Avalon knob."""

    order = pyblish.api.CollectorOrder - 0.6
    label = "Pre-collect Instances"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):
        asset_data = io.find_one({
            "type": "asset",
            "name": api.Session["AVALON_ASSET"]
        })

        self.log.debug("asset_data: {}".format(asset_data["data"]))
        instances = []

        root = nuke.root()

        self.log.debug("nuke.allNodes(): {}".format(nuke.allNodes()))
        for node in nuke.allNodes():

            if node.Class() in ["Viewer", "Dot"]:
                continue

            try:
                if node["disable"].value():
                    continue
            except Exception as E:
                self.log.warning(E)

            # get data from avalon knob
            self.log.debug("node[name]: {}".format(node['name'].value()))
            avalon_knob_data = anlib.get_avalon_knob_data(
                node, ["avalon:", "ak:"])

            self.log.debug("avalon_knob_data: {}".format(avalon_knob_data))

            if not avalon_knob_data:
                continue

            if avalon_knob_data["id"] != "pyblish.avalon.instance":
                continue

            # establish families
            family = avalon_knob_data["family"]
            families_ak = avalon_knob_data.get("families")
            families = list()

            if families_ak:
                families.append(families_ak.lower())

            families.append(family)

            # except disabled nodes but exclude backdrops in test
            if ("nukenodes" not in family) and (node["disable"].value()):
                continue

            subset = avalon_knob_data.get(
                "subset", None) or node["name"].value()

            # Create instance
            instance = context.create_instance(subset)
            instance.append(node)

            # Add all nodes in group instances.
            if node.Class() == "Group":
                # only alter families for render family
                if "write" in families_ak:
                    target = node["render"].value()
                    if target == "Use existing frames":
                        # Local rendering
                        self.log.info("flagged for no render")
                        families.append("render")
                    elif target == "Local":
                        # Local rendering
                        self.log.info("flagged for local render")
                        families.append("{}.local".format("render"))
                    elif target == "On farm":
                        # Farm rendering
                        self.log.info("flagged for farm render")
                        instance.data["transfer"] = False
                        families.append("{}.farm".format("render"))
                    if "render" in families:
                        families.remove("render")
                        family = "write"

                node.begin()
                for i in nuke.allNodes():
                    instance.append(i)
                node.end()

            self.log.debug("__ families: `{}`".format(families))

            # Get format
            format = root['format'].value()
            resolution_width = format.width()
            resolution_height = format.height()
            pixel_aspect = format.pixelAspect()

            instance.data.update({
                "subset": subset,
                "asset": avalon_knob_data["asset"],
                "label": node.name(),
                "name": node.name(),
                "subset": subset,
                "family": family,
                "families": families,
                "avalonKnob": avalon_knob_data,
                "publish": node.knob('publish').value(),
                "step": 1,
                "fps": nuke.root()['fps'].value(),
                "resolutionWidth": resolution_width,
                "resolutionHeight": resolution_height,
                "pixelAspect": pixel_aspect,

            })
            self.log.info("collected instance: {}".format(instance.data))
            instances.append(instance)

        context.data["instances"] = instances
        self.log.debug("context: {}".format(context))
