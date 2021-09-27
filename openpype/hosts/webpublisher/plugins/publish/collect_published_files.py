"""Loads publishing context from json and continues in publish process.

Requires:
    anatomy -> context["anatomy"] *(pyblish.api.CollectorOrder - 0.11)

Provides:
    context, instances -> All data from previous publishing process.
"""

import os
import json
import clique
import tempfile

import pyblish.api
from avalon import io
from openpype.lib import prepare_template_data


class CollectPublishedFiles(pyblish.api.ContextPlugin):
    """
    This collector will try to find json files in provided
    `OPENPYPE_PUBLISH_DATA`. Those files _MUST_ share same context.

    """
    # must be really early, context values are only in json file
    order = pyblish.api.CollectorOrder - 0.490
    label = "Collect rendered frames"
    host = ["webpublisher"]

    _context = None

    # from Settings
    task_type_to_family = {}

    def _load_json(self, path):
        path = path.strip('\"')
        assert os.path.isfile(path), (
            "Path to json file doesn't exist. \"{}\"".format(path)
        )
        data = None
        with open(path, "r") as json_file:
            try:
                data = json.load(json_file)
            except Exception as exc:
                self.log.error(
                    "Error loading json: "
                    "{} - Exception: {}".format(path, exc)
                )
        return data

    def _process_batch(self, dir_url):
        task_subfolders = [
            os.path.join(dir_url, o)
            for o in os.listdir(dir_url)
            if os.path.isdir(os.path.join(dir_url, o))]
        self.log.info("task_sub:: {}".format(task_subfolders))
        for task_dir in task_subfolders:
            task_data = self._load_json(os.path.join(task_dir,
                                                     "manifest.json"))
            self.log.info("task_data:: {}".format(task_data))
            ctx = task_data["context"]
            task_type = "default_task_type"
            task_name = None

            if ctx["type"] == "task":
                items = ctx["path"].split('/')
                asset = items[-2]
                os.environ["AVALON_TASK"] = ctx["name"]
                task_name = ctx["name"]
                task_type = ctx["attributes"]["type"]
            else:
                asset = ctx["name"]
                os.environ["AVALON_TASK"] = ""

            is_sequence = len(task_data["files"]) > 1

            _, extension = os.path.splitext(task_data["files"][0])
            family, families, subset_template, tags = self._get_family(
                self.task_type_to_family,
                task_type,
                is_sequence,
                extension.replace(".", ''))

            subset = self._get_subset_name(family, subset_template, task_name,
                                           task_data["variant"])

            os.environ["AVALON_ASSET"] = asset
            io.Session["AVALON_ASSET"] = asset

            instance = self._context.create_instance(subset)
            instance.data["asset"] = asset
            instance.data["subset"] = subset
            instance.data["family"] = family
            instance.data["families"] = families
            instance.data["version"] = \
                self._get_last_version(asset, subset) + 1
            instance.data["stagingDir"] = tempfile.mkdtemp()
            instance.data["source"] = "webpublisher"

            # to store logging info into DB openpype.webpublishes
            instance.data["ctx_path"] = ctx["path"]
            instance.data["batch_id"] = task_data["batch"]

            # to convert from email provided into Ftrack username
            instance.data["user_email"] = task_data["user"]

            if is_sequence:
                instance.data["representations"] = self._process_sequence(
                    task_data["files"], task_dir, tags
                )
                instance.data["frameStart"] = \
                    instance.data["representations"][0]["frameStart"]
                instance.data["frameEnd"] = \
                    instance.data["representations"][0]["frameEnd"]
            else:
                instance.data["frameStart"] = 0
                instance.data["frameEnd"] = 1
                instance.data["representations"] = self._get_single_repre(
                    task_dir, task_data["files"], tags
                )

            self.log.info("instance.data:: {}".format(instance.data))

    def _get_subset_name(self, family, subset_template, task_name, variant):
        fill_pairs = {
            "variant": variant,
            "family": family,
            "task": task_name
        }
        subset = subset_template.format(**prepare_template_data(fill_pairs))
        return subset

    def _get_single_repre(self, task_dir, files, tags):
        _, ext = os.path.splitext(files[0])
        repre_data = {
            "name": ext[1:],
            "ext": ext[1:],
            "files": files[0],
            "stagingDir": task_dir,
            "tags": tags
        }
        self.log.info("single file repre_data.data:: {}".format(repre_data))
        return [repre_data]

    def _process_sequence(self, files, task_dir, tags):
        """Prepare reprentations for sequence of files."""
        collections, remainder = clique.assemble(files)
        assert len(collections) == 1, \
            "Too many collections in {}".format(files)

        frame_start = list(collections[0].indexes)[0]
        frame_end = list(collections[0].indexes)[-1]
        ext = collections[0].tail
        repre_data = {
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "name": ext[1:],
            "ext": ext[1:],
            "files": files,
            "stagingDir": task_dir,
            "tags": tags
        }
        self.log.info("sequences repre_data.data:: {}".format(repre_data))
        return [repre_data]

    def _get_family(self, settings, task_type, is_sequence, extension):
        """Guess family based on input data.

            Args:
                settings (dict): configuration per task_type
                task_type (str): Animation|Art etc
                is_sequence (bool): single file or sequence
                extension (str): without '.'

            Returns:
                (family, [families], subset_template_name, tags) tuple
                AssertionError if not matching family found
        """
        task_type = task_type.lower()
        lower_cased_task_types = {}
        for t_type, task in settings.items():
            lower_cased_task_types[t_type.lower()] = task
        task_obj = lower_cased_task_types.get(task_type)
        assert task_obj, "No family configuration for '{}'".format(task_type)

        found_family = None
        for family, content in task_obj.items():
            if is_sequence != content["is_sequence"]:
                continue
            if extension in content["extensions"] or \
                    '' in content["extensions"]:  # all extensions setting
                found_family = family
                break

        msg = "No family found for combination of " +\
              "task_type: {}, is_sequence:{}, extension: {}".format(
                  task_type, is_sequence, extension)
        assert found_family, msg

        return found_family, \
            content["families"], \
            content["subset_template_name"], \
            content["tags"]

    def _get_last_version(self, asset_name, subset_name):
        """Returns version number or 0 for 'asset' and 'subset'"""
        query = [
            {
                "$match": {"type": "asset", "name": asset_name}
            },
            {
                "$lookup":
                    {
                        "from": os.environ["AVALON_PROJECT"],
                        "localField": "_id",
                        "foreignField": "parent",
                        "as": "subsets"
                    }
            },
            {
                "$unwind": "$subsets"
            },
            {
                "$match": {"subsets.type": "subset",
                           "subsets.name": subset_name}},
            {
                "$lookup":
                    {
                        "from": os.environ["AVALON_PROJECT"],
                        "localField": "subsets._id",
                        "foreignField": "parent",
                        "as": "versions"
                    }
            },
            {
                "$unwind": "$versions"
            },
            {
                "$group": {
                    "_id": {
                        "asset_name": "$name",
                        "subset_name": "$subsets.name"
                    },
                    'version': {'$max': "$versions.name"}
                }
            }
        ]
        version = list(io.aggregate(query))

        if version:
            return version[0].get("version") or 0
        else:
            return 0

    def process(self, context):
        self._context = context

        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")

        assert batch_dir, (
            "Missing `OPENPYPE_PUBLISH_DATA`")

        assert batch_dir, \
            "Folder {} doesn't exist".format(batch_dir)

        project_name = os.environ.get("AVALON_PROJECT")
        if project_name is None:
            raise AssertionError(
                "Environment `AVALON_PROJECT` was not found."
                "Could not set project `root` which may cause issues."
            )

        self._process_batch(batch_dir)
