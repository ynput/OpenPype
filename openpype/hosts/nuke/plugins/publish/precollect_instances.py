import nuke
import pyblish.api

from openpype.pipeline import legacy_io
from openpype.hosts.nuke.api.lib import (
    add_publish_knob,
    get_avalon_knob_data
)


@pyblish.api.log
class PreCollectNukeInstances(pyblish.api.ContextPlugin):
    """Collect all nodes with Avalon knob."""

    order = pyblish.api.CollectorOrder - 0.49
    label = "Pre-collect Instances"
    hosts = ["nuke", "nukeassist"]

    # presets
    sync_workfile_version_on_families = []

    def process(self, context):
        asset_data = legacy_io.find_one({
            "type": "asset",
            "name": legacy_io.Session["AVALON_ASSET"]
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
            avalon_knob_data = get_avalon_knob_data(
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

            # except disabled nodes but exclude backdrops in test
            if ("nukenodes" not in family) and (node["disable"].value()):
                continue

            subset = avalon_knob_data.get(
                "subset", None) or node["name"].value()

            # Create instance
            instance = context.create_instance(subset)
            instance.append(node)

            suspend_publish = False
            if "suspend_publish" in node.knobs():
                suspend_publish = node["suspend_publish"].value()
            instance.data["suspend_publish"] = suspend_publish

            # get review knob value
            review = False
            if "review" in node.knobs():
                review = node["review"].value()

            if review:
                families.append("review")

            # Add all nodes in group instances.
            if node.Class() == "Group":
                # only alter families for render family
                if families_ak and "write" in families_ak.lower():
                    target = node["render"].value()
                    if target == "Use existing frames":
                        # Local rendering
                        self.log.info("flagged for no render")
                        families.append(families_ak.lower())
                    elif target == "Local":
                        # Local rendering
                        self.log.info("flagged for local render")
                        families.append("{}.local".format(family))
                        family = families_ak.lower()
                    elif target == "On farm":
                        # Farm rendering
                        self.log.info("flagged for farm render")
                        instance.data["transfer"] = False
                        families.append("{}.farm".format(family))
                        family = families_ak.lower()

                node.begin()
                for i in nuke.allNodes():
                    instance.append(i)
                node.end()

            if not families and families_ak and family not in [
                    "render", "prerender"]:
                families.append(families_ak.lower())

            self.log.debug("__ family: `{}`".format(family))
            self.log.debug("__ families: `{}`".format(families))

            # Get format
            format = root['format'].value()
            resolution_width = format.width()
            resolution_height = format.height()
            pixel_aspect = format.pixelAspect()

            # get publish knob value
            if "publish" not in node.knobs():
                add_publish_knob(node)

            # sync workfile version
            _families_test = [family] + families
            self.log.debug("__ _families_test: `{}`".format(_families_test))
            for family_test in _families_test:
                if family_test in self.sync_workfile_version_on_families:
                    self.log.debug("Syncing version with workfile for '{}'"
                                   .format(family_test))
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
