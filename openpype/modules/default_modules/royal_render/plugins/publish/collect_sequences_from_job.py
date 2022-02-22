# -*- coding: utf-8 -*-
"""Collect sequences from Royal Render Job."""
import os
import re
import copy
import json
from pprint import pformat

import pyblish.api
from avalon import api


def collect(root,
            regex=None,
            exclude_regex=None,
            frame_start=None,
            frame_end=None):
    """Collect sequence collections in root"""

    import clique

    files = []
    for filename in os.listdir(root):

        # Must have extension
        ext = os.path.splitext(filename)[1]
        if not ext:
            continue

        # Only files
        if not os.path.isfile(os.path.join(root, filename)):
            continue

        # Include and exclude regex
        if regex and not re.search(regex, filename):
            continue
        if exclude_regex and re.search(exclude_regex, filename):
            continue

        files.append(filename)

    # Match collections
    # Support filenames like: projectX_shot01_0010.tiff with this regex
    pattern = r"(?P<index>(?P<padding>0*)\d+)\.\D+\d?$"
    collections, remainder = clique.assemble(files,
                                             patterns=[pattern],
                                             minimum_items=1)

    # Ignore any remainders
    if remainder:
        print("Skipping remainder {}".format(remainder))

    # Exclude any frames outside start and end frame.
    for collection in collections:
        for index in list(collection.indexes):
            if frame_start is not None and index < frame_start:
                collection.indexes.discard(index)
                continue
            if frame_end is not None and index > frame_end:
                collection.indexes.discard(index)
                continue

    # Keep only collections that have at least a single frame
    collections = [c for c in collections if c.indexes]

    return collections


class CollectSequencesFromJob(pyblish.api.ContextPlugin):
    """Gather file sequences from job directory.

    When "OPENPYPE_PUBLISH_DATA" environment variable is set these paths
    (folders or .json files) are parsed for image sequences. Otherwise the
    current working directory is searched for file sequences.

    """
    order = pyblish.api.CollectorOrder
    targets = ["rr_control"]
    label = "Collect Rendered Frames"
    review = True

    def process(self, context):

        self.review = (
            context.data
            ["project_settings"]
            ["royalrender"]
            ["publish"]
            ["CollectSequencesFromJob"]
            ["review"]
        )

        if os.environ.get("OPENPYPE_PUBLISH_DATA"):
            self.log.debug(os.environ.get("OPENPYPE_PUBLISH_DATA"))
            paths = os.environ["OPENPYPE_PUBLISH_DATA"].split(os.pathsep)
            self.log.info("Collecting paths: {}".format(paths))
        else:
            cwd = context.get("workspaceDir", os.getcwd())
            paths = [cwd]

        for path in paths:

            self.log.info("Loading: {}".format(path))

            if path.endswith(".json"):
                # Search using .json configuration
                with open(path, "r") as f:
                    try:
                        data = json.load(f)
                    except Exception as exc:
                        self.log.error("Error loading json: "
                                       "{} - Exception: {}".format(path, exc))
                        raise

                cwd = os.path.dirname(path)
                root_override = data.get("root")
                if root_override:
                    if os.path.isabs(root_override):
                        root = root_override
                    else:
                        root = os.path.join(cwd, root_override)
                else:
                    root = cwd

                metadata = data.get("metadata")
                if metadata:
                    session = metadata.get("session")
                    if session:
                        self.log.info("setting session using metadata")
                        api.Session.update(session)
                        os.environ.update(session)

            else:
                # Search in directory
                data = {}
                root = path

            self.log.info("Collecting: {}".format(root))
            regex = data.get("regex")
            if regex:
                self.log.info("Using regex: {}".format(regex))

            collections = collect(root=root,
                                  regex=regex,
                                  exclude_regex=data.get("exclude_regex"),
                                  frame_start=data.get("frameStart"),
                                  frame_end=data.get("frameEnd"))

            self.log.info("Found collections: {}".format(collections))

            if data.get("subset") and len(collections) > 1:
                self.log.error("Forced subset can only work with a single "
                               "found sequence")
                raise RuntimeError("Invalid sequence")

            fps = data.get("fps", 25)

            # Get family from the data
            families = data.get("families", ["render"])
            if "render" not in families:
                families.append("render")
            if "ftrack" not in families:
                families.append("ftrack")
            if "review" not in families and self.review:
                self.log.info("attaching review")
                families.append("review")

            for collection in collections:
                instance = context.create_instance(str(collection))
                self.log.info("Collection: %s" % list(collection))

                # Ensure each instance gets a unique reference to the data
                data = copy.deepcopy(data)

                # If no subset provided, get it from collection's head
                subset = data.get("subset", collection.head.rstrip("_. "))

                # If no start or end frame provided, get it from collection
                indices = list(collection.indexes)
                start = data.get("frameStart", indices[0])
                end = data.get("frameEnd", indices[-1])

                ext = list(collection)[0].split('.')[-1]

                instance.data.update({
                    "name": str(collection),
                    "family": families[0],  # backwards compatibility / pyblish
                    "families": list(families),
                    "subset": subset,
                    "asset": data.get("asset", api.Session["AVALON_ASSET"]),
                    "stagingDir": root,
                    "frameStart": start,
                    "frameEnd": end,
                    "fps": fps,
                    "source": data.get('source', '')
                })
                instance.append(collection)
                instance.context.data['fps'] = fps

                if "representations" not in instance.data:
                    instance.data["representations"] = []

                representation = {
                    'name': ext,
                    'ext': '{}'.format(ext),
                    'files': list(collection),
                    "frameStart": start,
                    "frameEnd": end,
                    "stagingDir": root,
                    "anatomy_template": "render",
                    "fps": fps,
                    "tags": ['review']
                }
                instance.data["representations"].append(representation)

                if data.get('user'):
                    context.data["user"] = data['user']

                self.log.debug("Collected instance:\n"
                               "{}".format(pformat(instance.data)))
