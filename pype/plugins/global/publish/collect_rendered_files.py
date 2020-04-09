"""Loads publishing context from json and continues in publish process.

Requires:
    anatomy -> context["anatomy"] *(pyblish.api.CollectorOrder - 0.11)

Provides:
    context, instances -> All data from previous publishing process.
"""

import os
import json

import pyblish.api
from avalon import api


class CollectRenderedFiles(pyblish.api.ContextPlugin):
    """
    This collector will try to find json files in provided
    `PYPE_PUBLISH_DATA`. Those files _MUST_ share same context.

    """
    order = pyblish.api.CollectorOrder - 0.1
    targets = ["filesequence"]
    label = "Collect rendered frames"

    _context = None

    def _load_json(self, path):
        assert os.path.isfile(path), ("path to json file doesn't exist")
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

    def _process_path(self, data, anatomy):
        # validate basic necessary data
        data_err = "invalid json file - missing data"
        required = ["asset", "user", "comment",
                    "job", "instances", "session", "version"]
        assert all(elem in data.keys() for elem in required), data_err

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

        # ftrack credentials are passed as environment variables by Deadline
        # to publish job, but Muster doesn't pass them.
        if data.get("ftrack") and not os.environ.get("FTRACK_API_USER"):
            ftrack = data.get("ftrack")
            os.environ["FTRACK_API_USER"] = ftrack["FTRACK_API_USER"]
            os.environ["FTRACK_API_KEY"] = ftrack["FTRACK_API_KEY"]
            os.environ["FTRACK_SERVER"] = ftrack["FTRACK_SERVER"]

        # now we can just add instances from json file and we are done
        for instance_data in data.get("instances"):
            self.log.info("  - processing instance for {}".format(
                instance_data.get("subset")))
            instance = self._context.create_instance(
                instance_data.get("subset")
            )
            self.log.info("Filling stagignDir...")
            instance.data.update(instance_data)

            representations = []
            for repre_data in instance_data.get("representations") or []:
                staging_dir = repre_data.get("stagingDir")
                if not staging_dir:
                    pass

                elif "{root" in staging_dir:
                    repre_data["stagingDir"] = staging_dir.format(
                        **{"root": anatomy.roots}
                    )
                    self.log.debug((
                        "stagingDir was filled with root."
                        " To: \"{}\" From: \"{}\""
                    ).format(repre_data["stagingDir"], staging_dir))

                else:
                    remapped = anatomy.roots_obj.path_remapper(staging_dir)
                    if remapped:
                        repre_data["stagingDir"] = remapped
                        self.log.debug((
                            "stagingDir was remapped. To: \"{}\" From: \"{}\""
                        ).format(remapped, staging_dir))

                representations.append(repre_data)

            instance.data["representations"] = representations

    def process(self, context):
        self._context = context

        assert os.environ.get("PYPE_PUBLISH_DATA"), (
            "Missing `PYPE_PUBLISH_DATA`")
        paths = os.environ["PYPE_PUBLISH_DATA"].split(os.pathsep)

        project_name = os.environ.get("AVALON_PROJECT")
        if project_name is None:
            raise AssertionError(
                "Environment `AVALON_PROJECT` was not found."
                "Could not set project `root` which may cause issues."
            )

        # TODO root filling should happen after collect Anatomy
        self.log.info("Getting root setting for project \"{}\"".format(
            project_name
        ))

        anatomy = context.data["anatomy"]
        session_set = False
        for path in paths:
            path = path.format(**{"root": anatomy.roots})
            data = self._load_json(path)
            if not session_set:
                self.log.info("Setting session using data from file")
                api.Session.update(data.get("session"))
                os.environ.update(data.get("session"))
                session_set = True
            assert data, "failed to load json file"
            self._process_path(data, anatomy)
