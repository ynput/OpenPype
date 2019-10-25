# from pype import plugins
import os
import json
import re
import pyblish.api
import tempfile
from avalon import io, api

class ExtractVideoTracksLuts(pyblish.api.InstancePlugin):
    """Collect video tracks effects into context."""

    order = pyblish.api.ExtractorOrder
    label = "Export Soft Lut Effects"
    families = ["lut"]

    def process(self, instance):
        item = instance.data["item"]
        effects = instance.data.get("effectTrackItems")

        instance.data["families"] = [f for f in instance.data.get("families", []) if f not in ["lut"]]

        self.log.debug("___ instance.data[families]: `{}`".format(instance.data["families"]))

        # skip any without effects
        if not effects:
            return

        subset = instance.data.get("subset")
        subset_split = re.findall(r'[A-Z][^A-Z]*', subset)

        if len(subset_split) > 0:
            root_name = subset.replace(subset_split[0], "")
            subset_split.insert(0, root_name.capitalize())

        subset_split.insert(0, "lut")

        self.log.debug("creating staging dir")
        # staging_dir = self.staging_dir(instance)

        # TODO: only provisory will be replace by function
        staging_dir = instance.data.get('stagingDir', None)

        if not staging_dir:
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data['stagingDir'] = staging_dir

        self.log.debug("creating staging dir: `{}`".format(staging_dir))

        transfers = list()
        if "transfers" not in instance.data:
            instance.data["transfers"] = list()

        name = "".join(subset_split)
        ext = "json"
        file = name + "." + ext

        # create new instance and inherit data
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        # change names
        data["subset"] = name
        data["family"] = "lut"
        data["families"] = []
        data["name"] = data["subset"] + "_" + data["asset"]
        data["label"] = "{} - {} - ({})".format(
            data['asset'], data["subset"], os.path.splitext(file)[1]
        )
        data["source"] = data["sourcePath"]

        # create new instance
        instance = instance.context.create_instance(**data)

        dst_dir = self.resource_destination_dir(instance)

        # change paths in effects to files
        for k, effect in effects["effects"].items():
            trn = self.copy_linked_files(effect, dst_dir)
            if trn:
                transfers.append((trn[0], trn[1]))

        instance.data["transfers"].extend(transfers)
        self.log.debug("_ transfers: `{}`".format(
            instance.data["transfers"]))

        # create representations
        instance.data["representations"] = list()

        transfer_data = [
            "handleStart", "handleEnd", "sourceIn", "sourceOut",
            "frameStart", "frameEnd", "sourceInH", "sourceOutH",
            "clipIn", "clipOut", "clipInH", "clipOutH", "asset", "track",
            "version"
        ]

        # pass data to version
        version_data = dict()
        version_data.update({k: instance.data[k] for k in transfer_data})

        # add to data of representation
        version_data.update({
            "handles": version_data['handleStart'],
            "colorspace": item.sourceMediaColourTransform(),
            "colorspaceScript": instance.context.data["colorspace"],
            "families": ["plate", "lut"],
            "subset": name,
            "fps": instance.context.data["fps"]
        })
        instance.data["versionData"] = version_data

        representation = {
            'files': file,
            'stagingDir': staging_dir,
            'name': "lut" + ext.title(),
            'ext': ext
        }
        instance.data["representations"].append(representation)

        self.log.debug("_ representations: `{}`".format(
            instance.data["representations"]))

        self.log.debug("_ version_data: `{}`".format(
            instance.data["versionData"]))

        with open(os.path.join(staging_dir, file), "w") as outfile:
            outfile.write(json.dumps(effects, indent=4, sort_keys=True))

        return

    def copy_linked_files(self, effect, dst_dir):
        for k, v in effect["node"].items():
            if k in "file" and v is not '':
                base_name = os.path.basename(v)
                dst = os.path.join(dst_dir, base_name).replace("\\", "/")

                # add it to the json
                effect["node"][k] = dst
                return (v, dst)

    def resource_destination_dir(self, instance):
        anatomy = instance.context.data['anatomy']
        self.create_destination_template(instance, anatomy)

        return os.path.join(
            instance.data["assumedDestination"],
            "resources"
        )

    def create_destination_template(self, instance, anatomy):
        """Create a filepath based on the current data available

        Example template:
            {root}/{project}/{silo}/{asset}/publish/{subset}/v{version:0>3}/
            {subset}.{representation}
        Args:
            instance: the instance to publish

        Returns:
            file path (str)
        """

        # get all the stuff from the database
        subset_name = instance.data["subset"]
        self.log.info(subset_name)
        asset_name = instance.data["asset"]
        project_name = api.Session["AVALON_PROJECT"]
        a_template = anatomy.templates

        project = io.find_one({"type": "project",
                               "name": project_name},
                              projection={"config": True, "data": True})

        template = a_template['publish']['path']
        # anatomy = instance.context.data['anatomy']

        asset = io.find_one({"type": "asset",
                             "name": asset_name,
                             "parent": project["_id"]})

        assert asset, ("No asset found by the name '{}' "
                       "in project '{}'".format(asset_name, project_name))
        silo = asset.get('silo')

        subset = io.find_one({"type": "subset",
                              "name": subset_name,
                              "parent": asset["_id"]})

        # assume there is no version yet, we start at `1`
        version = None
        version_number = 1
        if subset is not None:
            version = io.find_one({"type": "version",
                                   "parent": subset["_id"]},
                                  sort=[("name", -1)])

        # if there is a subset there ought to be version
        if version is not None:
            version_number += version["name"]

        if instance.data.get('version'):
            version_number = int(instance.data.get('version'))

        padding = int(a_template['render']['padding'])

        hierarchy = asset['data']['parents']
        if hierarchy:
            # hierarchy = os.path.sep.join(hierarchy)
            hierarchy = "/".join(hierarchy)

        template_data = {"root": api.Session["AVALON_PROJECTS"],
                         "project": {"name": project_name,
                                     "code": project['data']['code']},
                         "silo": silo,
                         "family": instance.data['family'],
                         "asset": asset_name,
                         "subset": subset_name,
                         "frame": ('#' * padding),
                         "version": version_number,
                         "hierarchy": hierarchy,
                         "representation": "TEMP"}

        instance.data["assumedTemplateData"] = template_data
        self.log.info(template_data)
        instance.data["template"] = template
        # We take the parent folder of representation 'filepath'
        instance.data["assumedDestination"] = os.path.dirname(
            anatomy.format(template_data)["publish"]["path"]
        )
