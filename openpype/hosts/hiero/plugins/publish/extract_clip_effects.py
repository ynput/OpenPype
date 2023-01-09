# from openpype import plugins
import os
import json
import pyblish.api

from openpype.pipeline import publish


class ExtractClipEffects(publish.Extractor):
    """Extract clip effects instances."""

    order = pyblish.api.ExtractorOrder
    label = "Export Clip Effects"
    families = ["effect"]

    def process(self, instance):
        item = instance.data["item"]
        effects = instance.data.get("effects")

        # skip any without effects
        if not effects:
            return

        subset = instance.data.get("subset")
        family = instance.data["family"]

        self.log.debug("creating staging dir")
        staging_dir = self.staging_dir(instance)

        transfers = list()
        if "transfers" not in instance.data:
            instance.data["transfers"] = list()

        ext = "json"
        file = subset + "." + ext

        # when instance is created during collection part
        resources_dir = instance.data["resourcesDir"]

        # change paths in effects to files
        for k, effect in effects.items():
            if "assignTo" in k:
                continue
            trn = self.copy_linked_files(effect, resources_dir)
            if trn:
                transfers.append((trn[0], trn[1]))

        instance.data["transfers"].extend(transfers)
        self.log.debug("_ transfers: `{}`".format(
            instance.data["transfers"]))

        # create representations
        instance.data["representations"] = list()

        transfer_data = [
            "handleStart", "handleEnd",
            "sourceStart", "sourceStartH", "sourceEnd", "sourceEndH",
            "frameStart", "frameEnd",
            "clipIn", "clipOut", "clipInH", "clipOutH",
            "asset", "version"
        ]

        # pass data to version
        version_data = dict()
        version_data.update({k: instance.data[k] for k in transfer_data})

        # add to data of representation
        version_data.update({
            "colorspace": item.sourceMediaColourTransform(),
            "colorspaceScript": instance.context.data["colorspace"],
            "families": [family, "plate"],
            "subset": subset,
            "fps": instance.context.data["fps"]
        })
        instance.data["versionData"] = version_data

        representation = {
            'files': file,
            'stagingDir': staging_dir,
            'name': family + ext.title(),
            'ext': ext
        }
        instance.data["representations"].append(representation)

        self.log.debug("_ representations: `{}`".format(
            instance.data["representations"]))

        self.log.debug("_ version_data: `{}`".format(
            instance.data["versionData"]))

        with open(os.path.join(staging_dir, file), "w") as outfile:
            outfile.write(json.dumps(effects, indent=4, sort_keys=True))

    def copy_linked_files(self, effect, dst_dir):
        for k, v in effect["node"].items():
            if k in "file" and v != '':
                base_name = os.path.basename(v)
                dst = os.path.join(dst_dir, base_name).replace("\\", "/")

                # add it to the json
                effect["node"][k] = dst
                return (v, dst)
