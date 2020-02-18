"""
Requires:
    environment -> PYPE_PUBLISH_PATHS
    context     -> workspaceDir

Provides:
    context     -> user (str)
    instance    -> new instance
"""

import os
import re
import copy
import json

import pyblish.api
from avalon import api


def collect(root,
            regex=None,
            exclude_regex=None,
            frame_start=None,
            frame_end=None):
    """Collect sequence collections in root"""

    from avalon.vendor import clique

    files = list()
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

    return collections, remainder


class CollectRenderedFrames(pyblish.api.ContextPlugin):
    """Gather file sequences from working directory

    When "FILESEQUENCE" environment variable is set these paths (folders or
    .json files) are parsed for image sequences. Otherwise the current
    working directory is searched for file sequences.

    The json configuration may have the optional keys:
        asset (str): The asset to publish to. If not provided fall back to
            api.Session["AVALON_ASSET"]
        subset (str): The subset to publish to. If not provided the sequence's
            head (up to frame number) will be used.
        frame_start (int): The start frame for the sequence
        frame_end (int): The end frame for the sequence
        root (str): The path to collect from (can be relative to the .json)
        regex (str): A regex for the sequence filename
        exclude_regex (str): A regex for filename to exclude from collection
        metadata (dict): Custom metadata for instance.data["metadata"]

    """

    order = pyblish.api.CollectorOrder - 0.0001
    targets = ["filesequence"]
    label = "RenderedFrames"

    def process(self, context):
        pixel_aspect = 1
        resolution_width = 1920
        resolution_height = 1080
        lut_path = None
        slate_frame = None
        families_data = None
        baked_mov_path = None
        subset = None
        version = None
        frame_start = 0
        frame_end = 0
        if os.environ.get("PYPE_PUBLISH_PATHS"):
            paths = os.environ["PYPE_PUBLISH_PATHS"].split(os.pathsep)
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
                        self.log.error(
                            "Error loading json: "
                            "{} - Exception: {}".format(path, exc)
                        )
                        raise

                cwd = os.path.dirname(path)
                root_override = data.get("root")
                frame_start = int(data.get("frameStart"))
                frame_end = int(data.get("frameEnd"))
                subset = data.get("subset")

                if root_override:
                    if os.path.isabs(root_override):
                        root = root_override
                    else:
                        root = os.path.join(cwd, root_override)
                else:
                    root = cwd

                if data.get("ftrack"):
                    f = data.get("ftrack")
                    os.environ["FTRACK_API_USER"] = f["FTRACK_API_USER"]
                    os.environ["FTRACK_API_KEY"] = f["FTRACK_API_KEY"]
                    os.environ["FTRACK_SERVER"] = f["FTRACK_SERVER"]

                metadata = data.get("metadata")
                if metadata:
                    session = metadata.get("session")
                    if session:
                        self.log.info("setting session using metadata")
                        api.Session.update(session)
                        os.environ.update(session)
                    instance = metadata.get("instance")
                    if instance:
                        instance_family = instance.get("family")
                        pixel_aspect = instance.get("pixelAspect", 1)
                        resolution_width = instance.get("resolutionWidth", 1920)
                        resolution_height = instance.get("resolutionHeight", 1080)
                        lut_path = instance.get("lutPath", None)
                        baked_mov_path = instance.get("bakeRenderPath")
                        families_data = instance.get("families")
                        slate_frame = instance.get("slateFrame")
                        version = instance.get("version")


            else:
                # Search in directory
                data = dict()
                root = path

            self.log.info("Collecting: {}".format(root))

            regex = data.get("regex")
            if baked_mov_path:
                regex = "^{}.*$".format(subset)

            if regex:
                self.log.info("Using regex: {}".format(regex))

            if "slate" in families_data:
                frame_start -= 1

            collections, remainder = collect(
                root=root,
                regex=regex,
                exclude_regex=data.get("exclude_regex"),
                frame_start=frame_start,
                frame_end=frame_end,
            )

            self.log.info("Found collections: {}".format(collections))
            self.log.info("Found remainder: {}".format(remainder))

            fps = data.get("fps", 25)

            # adding publish comment and intent to context
            context.data["comment"] = data.get("comment", "")
            context.data["intent"] = data.get("intent", "")

            if data.get("user"):
                context.data["user"] = data["user"]

            if data.get("version"):
                version = data.get("version")

            # Get family from the data
            families = data.get("families", ["render"])
            if "ftrack" not in families:
                families.append("ftrack")
            if families_data and "render2d" in families_data:
                families.append("render2d")
            if families_data and "slate" in families_data:
                families.append("slate")

            if data.get("attachTo"):
                # we need to attach found collections to existing
                # subset version as review represenation.

                for attach in data.get("attachTo"):
                    self.log.info(
                        "Attaching render {}:v{}".format(
                            attach["subset"], attach["version"]))
                    instance = context.create_instance(
                        attach["subset"])
                    instance.data.update(
                        {
                            "name": attach["subset"],
                            "version": attach["version"],
                            "family": 'review',
                            "families": ['review', 'ftrack'],
                            "asset": data.get(
                                "asset", api.Session["AVALON_ASSET"]),
                            "stagingDir": root,
                            "frameStart": frame_start,
                            "frameEnd": frame_end,
                            "fps": fps,
                            "source": data.get("source", ""),
                            "pixelAspect": pixel_aspect,
                            "resolutionWidth": resolution_width,
                            "resolutionHeight": resolution_height
                        })

                    if "representations" not in instance.data:
                        instance.data["representations"] = []

                    for collection in collections:
                        self.log.info(
                            "  - adding representation: {}".format(
                                str(collection))
                        )
                        ext = collection.tail.lstrip(".")

                        representation = {
                            "name": ext,
                            "ext": "{}".format(ext),
                            "files": list(collection),
                            "stagingDir": root,
                            "anatomy_template": "render",
                            "fps": fps,
                            "tags": ["review"],
                        }
                        instance.data["representations"].append(
                            representation)

            elif subset:
                # if we have subset - add all collections and known
                # reminder as representations

                # take out review family if mov path
                # this will make imagesequence none review

                if baked_mov_path:
                    self.log.info(
                        "Baked mov is available {}".format(
                            baked_mov_path))
                    families.append("review")

                if session['AVALON_APP'] == "maya":
                    families.append("review")

                self.log.info(
                    "Adding representations to subset {}".format(
                        subset))

                instance = context.create_instance(subset)
                data = copy.deepcopy(data)

                instance.data.update(
                    {
                        "name": subset,
                        "family": families[0],
                        "families": list(families),
                        "subset": subset,
                        "asset": data.get(
                            "asset", api.Session["AVALON_ASSET"]),
                        "stagingDir": root,
                        "frameStart": frame_start,
                        "frameEnd": frame_end,
                        "fps": fps,
                        "source": data.get("source", ""),
                        "pixelAspect": pixel_aspect,
                        "resolutionWidth": resolution_width,
                        "resolutionHeight": resolution_height,
                        "slateFrame": slate_frame,
                        "version": version
                    }
                )

                if "representations" not in instance.data:
                    instance.data["representations"] = []

                for collection in collections:
                    self.log.info("  - {}".format(str(collection)))

                    ext = collection.tail.lstrip(".")

                    if "slate" in instance.data["families"]:
                        frame_start += 1

                    representation = {
                        "name": ext,
                        "ext": "{}".format(ext),
                        "files": list(collection),
                        "frameStart": frame_start,
                        "frameEnd": frame_end,
                        "stagingDir": root,
                        "anatomy_template": "render",
                        "fps": fps,
                        "tags": ["review"] if not baked_mov_path else ["thumb-nuke"],
                    }
                    instance.data["representations"].append(
                        representation)

                # filter out only relevant mov in case baked available
                self.log.debug("__ remainder {}".format(remainder))
                if baked_mov_path:
                    remainder = [r for r in remainder
                                 if r in baked_mov_path]
                    self.log.debug("__ remainder {}".format(remainder))

                # process reminders
                for rem in remainder:
                    # add only known types to representation
                    if rem.split(".")[-1] in ['mov', 'jpg', 'mp4']:
                        self.log.info("  . {}".format(rem))

                        if "slate" in instance.data["families"]:
                            frame_start += 1

                        tags = ["review"]

                        if baked_mov_path:
                            tags.append("delete")

                        representation = {
                            "name": rem.split(".")[-1],
                            "ext": "{}".format(rem.split(".")[-1]),
                            "files": rem,
                            "stagingDir": root,
                            "frameStart": frame_start,
                            "anatomy_template": "render",
                            "fps": fps,
                            "tags": tags
                        }
                    instance.data["representations"].append(
                        representation)

            else:
                # we have no subset so we take every collection and create one
                # from it
                for collection in collections:
                    instance = context.create_instance(str(collection))
                    self.log.info("Creating subset from: %s" % str(collection))

                    # Ensure each instance gets a unique reference to the data
                    data = copy.deepcopy(data)

                    # If no subset provided, get it from collection's head
                    subset = data.get("subset", collection.head.rstrip("_. "))

                    # If no start or end frame provided, get it from collection
                    indices = list(collection.indexes)
                    start = int(data.get("frameStart", indices[0]))
                    end = int(data.get("frameEnd", indices[-1]))

                    ext = list(collection)[0].split(".")[-1]

                    if "review" not in families:
                        families.append("review")

                    instance.data.update(
                        {
                            "name": str(collection),
                            "family": families[0],  # backwards compatibility
                            "families": list(families),
                            "subset": subset,
                            "asset": data.get(
                                "asset", api.Session["AVALON_ASSET"]),
                            "stagingDir": root,
                            "frameStart": start,
                            "frameEnd": end,
                            "fps": fps,
                            "source": data.get("source", ""),
                            "pixelAspect": pixel_aspect,
                            "resolutionWidth": resolution_width,
                            "resolutionHeight": resolution_height,
                            "version": version
                        }
                    )
                    if lut_path:
                        instance.data.update({"lutPath": lut_path})

                    instance.append(collection)
                    instance.context.data["fps"] = fps

                    if "representations" not in instance.data:
                        instance.data["representations"] = []

                    representation = {
                        "name": ext,
                        "ext": "{}".format(ext),
                        "files": list(collection),
                        "frameStart": start,
                        "frameEnd": end,
                        "stagingDir": root,
                        "anatomy_template": "render",
                        "fps": fps,
                        "tags": ["review"],
                    }
                    instance.data["representations"].append(representation)

                    # temporary ... allow only beauty on ftrack
                    if session['AVALON_APP'] == "maya":
                        AOV_filter = ['beauty']
                        for aov in AOV_filter:
                            if aov not in instance.data['subset']:
                                instance.data['families'].remove('review')
                                instance.data['families'].remove('ftrack')
                                representation["tags"].remove('review')

            self.log.debug(
                "__ representations {}".format(
                    instance.data["representations"]))
            self.log.debug(
                "__ instance.data {}".format(instance.data))
