"""Loads publishing context from json and continues in publish process.

Requires:
    anatomy -> context["anatomy"] *(pyblish.api.CollectorOrder - 0.11)

Provides:
    context, instances -> All data from previous publishing process.
"""

import os
import json
import clique

import pyblish.api
from avalon import api

FAMILY_SETTING = {  # TEMP
    "Animation": {
        "workfile": {
            "is_sequence": False,
            "extensions": ["tvp"],
            "families": []
        },
        "render": {
            "is_sequence": True,
            "extensions": [
                "png", "exr", "tiff", "tif"
            ],
            "families": ["review"]
        }
    },
    "Compositing": {
        "workfile": {
            "is_sequence": False,
            "extensions": ["aep"],
            "families": []
        },
        "render": {
            "is_sequence": True,
            "extensions": [
                "png", "exr", "tiff", "tif"
            ],
            "families": ["review"]
        }
    },
    "Layout": {
        "workfile": {
            "is_sequence": False,
            "extensions": [
                ".psd"
            ],
            "families": []
        },
        "image": {
            "is_sequence": False,
            "extensions": [
                "png",
                "jpg",
                "jpeg",
                "tiff",
                "tif"
            ],
            "families": [
                "review"
            ]
        }
    }
}

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

    def _fill_staging_dir(self, data_object, anatomy):
        staging_dir = data_object.get("stagingDir")
        if staging_dir:
            data_object["stagingDir"] = anatomy.fill_root(staging_dir)

    def _process_path(self, data):
        # validate basic necessary data
        data_err = "invalid json file - missing data"
        # required = ["asset", "user", "comment",
        #             "job", "instances", "session", "version"]
        # assert all(elem in data.keys() for elem in required), data_err

        # set context by first json file
        ctx = self._context.data

        ctx["asset"] = ctx.get("asset") or data.get("asset")
        ctx["intent"] = ctx.get("intent") or data.get("intent")
        ctx["comment"] = ctx.get("comment") or data.get("comment")
        ctx["user"] = ctx.get("user") or data.get("user")
        ctx["version"] = ctx.get("version") or data.get("version")

        # basic sanity check to see if we are working in same context
        # if some other json file has different context, bail out.
        ctx_err = "inconsistent contexts in json files - %s"
        assert ctx.get("asset") == data.get("asset"), ctx_err % "asset"
        assert ctx.get("intent") == data.get("intent"), ctx_err % "intent"
        assert ctx.get("comment") == data.get("comment"), ctx_err % "comment"
        assert ctx.get("user") == data.get("user"), ctx_err % "user"
        assert ctx.get("version") == data.get("version"), ctx_err % "version"

        # now we can just add instances from json file and we are done
        for instance_data in data.get("instances"):
            self.log.info("  - processing instance for {}".format(
                instance_data.get("subset")))
            instance = self._context.create_instance(
                instance_data.get("subset")
            )
            self.log.info("Filling stagingDir...")

            self._fill_staging_dir(instance_data, anatomy)
            instance.data.update(instance_data)

            # stash render job id for later validation
            instance.data["render_job_id"] = data.get("job").get("_id")

            representations = []
            for repre_data in instance_data.get("representations") or []:
                self._fill_staging_dir(repre_data, anatomy)
                representations.append(repre_data)

            instance.data["representations"] = representations

            # add audio if in metadata data
            if data.get("audio"):
                instance.data.update({
                    "audio": [{
                        "filename": data.get("audio"),
                        "offset": 0
                    }]
                })
                self.log.info(
                    f"Adding audio to instance: {instance.data['audio']}")

    def _process_batch(self, dir_url):
        task_subfolders = [os.path.join(dir_url, o)
                               for o in os.listdir(dir_url)
                                   if os.path.isdir(os.path.join(dir_url, o))]
        self.log.info("task_sub:: {}".format(task_subfolders))
        for task_dir in task_subfolders:
            task_data = self._load_json(os.path.join(task_dir,
                                                     "manifest.json"))
            self.log.info("task_data:: {}".format(task_data))
            ctx = task_data["context"]
            asset = subset = task = task_type = None

            subset = "Main"  # temp
            if ctx["type"] == "task":
                items = ctx["path"].split('/')
                asset = items[-2]
                os.environ["AVALON_TASK"] = ctx["name"]
                task_type = ctx["attributes"]["type"]
            else:
                asset = ctx["name"]

            is_sequence = len(task_data["files"]) > 1

            instance = self._context.create_instance(subset)
            _, extension = os.path.splitext(task_data["files"][0])
            self.log.info("asset:: {}".format(asset))
            family, families = self._get_family(FAMILY_SETTING,  # todo
                                                task_type,
                                                is_sequence,
                                                extension.replace(".", ''))
            os.environ["AVALON_ASSET"] = asset
            instance.data["asset"] = asset
            instance.data["subset"] = subset
            instance.data["family"] = family
            instance.data["families"] = families
            # instance.data["version"] = self._get_version(task_data["subset"])
            instance.data["stagingDir"] = task_dir
            instance.data["source"] = "webpublisher"

            os.environ["FTRACK_API_USER"] = task_data["user"]

            if is_sequence:
                instance.data["representations"] = self._process_sequence(
                    task_data["files"], task_dir
                )
            else:
                _, ext = os.path.splittext(task_data["files"][0])
                repre_data = {
                    "name": ext[1:],
                    "ext": ext[1:],
                    "files": task_data["files"],
                    "stagingDir": task_dir
                }
                instance.data["representation"] = repre_data

            self.log.info("instance.data:: {}".format(instance.data))

    def _process_sequence(self, files, task_dir):
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
            "stagingDir": task_dir
        }
        self.log.info("repre_data.data:: {}".format(repre_data))
        return [repre_data]

    def _get_family(self, settings, task_type, is_sequence, extension):
        """Guess family based on input data.

            Args:
                settings (dict): configuration per task_type
                task_type (str): Animation|Art etc
                is_sequence (bool): single file or sequence
                extension (str): without '.'

            Returns:
                (family, [families]) tuple
                AssertionError if not matching family found
        """
        task_obj = settings.get(task_type)
        assert task_obj, "No family configuration for '{}'".format(task_type)

        found_family = None
        for family, content in task_obj.items():
            if is_sequence != content["is_sequence"]:
                continue
            if extension in content["extensions"]:
                found_family = family
                break

        msg = "No family found for combination of " +\
              "task_type: {}, is_sequence:{}, extension: {}".format(
                  task_type, is_sequence, extension)
        assert found_family, msg

        return found_family, content["families"]

    def _get_version(self, subset_name):
        return 1

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

