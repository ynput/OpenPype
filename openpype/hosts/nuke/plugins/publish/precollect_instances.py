import nuke
import pyblish.api
from avalon import io, api
from avalon.nuke import lib as anlib


@pyblish.api.log
class PreCollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all nodes with Avalon knob."""

    order = pyblish.api.CollectorOrder - 0.59
    label = "Pre-collect Instances"
    hosts = ["nuke", "nukeassist"]

    # presets
    sync_workfile_version = False

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
            avalon_knob_data = anlib.get_avalon_knob_data(
                node, ["avalon:", "ak:"])

            self.log.debug("avalon_knob_data: {}".format(avalon_knob_data))

            if not avalon_knob_data:
                continue

            if avalon_knob_data["id"] != "pyblish.avalon.instance":
                continue

            # establish families
            family = avalon_knob_data["family"]
            families_ak = avalon_knob_data.get("families", [])
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

            # get review knob value
            review = False
            if "review" in node.knobs():
                review = node["review"].value()
                families.append("review")
                families.append("ftrack")

            # Add all nodes in group instances.
            if node.Class() == "Group":
                # only alter families for render family
                if "write" in families_ak:
                    target = node["render"].value()
                    if target == "Use existing frames":
                        # Local rendering
                        self.log.info("flagged for no render")
                        families.append(family)
                    elif target == "Local":
                        # Local rendering
                        self.log.info("flagged for local render")
                        families.append("{}.local".format(family))
                    elif target == "On farm":
                        # Farm rendering
                        self.log.info("flagged for farm render")
                        instance.data["transfer"] = False
                        families.append("{}.farm".format(family))

                    # suffle family to `write` as it is main family
                    # this will be changed later on in process
                    if "render" in families:
                        families.remove("render")
                        family = "write"
                    elif "prerender" in families:
                        families.remove("prerender")
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

            # get publish knob value
            if "publish" not in node.knobs():
                anlib.add_publish_knob(node)

            # sync workfile version
            if not next((f for f in families
                         if "prerender" in f),
                        None) and self.sync_workfile_version:
                # get version to instance for integration
                instance.data['version'] = instance.context.data['version']

            instance.data.update({
                "subset": subset,
                "asset": avalon_knob_data["asset"],
                "label": node.name(),
                "name": node.name(),
                "subset": subset,
                "family": family,
                "families": families,
                "avalonKnob": avalon_knob_data,
                "step": 1,
                "publish": node.knob('publish').value(),
                "fps": nuke.root()['fps'].value(),
                "resolutionWidth": resolution_width,
                "resolutionHeight": resolution_height,
                "pixelAspect": pixel_aspect,
                "review": review

            })
            self.log.info("collected instance: {}".format(instance.data))
            instances.append(instance)

        # create instances in context data if not are created yet
        if not context.data.get("instances"):
            context.data["instances"] = list()

        context.data["instances"].extend(instances)
        self.log.debug("context: {}".format(context))
