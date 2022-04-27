from pprint import pformat
import re
import ast
import json

import pyblish.api


class CollectFrameTagInstances(pyblish.api.ContextPlugin):
    """Collect frames from tags.

    Tag is expected to have metadata:
    {
        "family": "frame"
        "subset": "main"
    }
    """

    order = pyblish.api.CollectorOrder
    label = "Collect Frames"
    hosts = ["hiero"]

    def process(self, context):
        self._context = context

        # collect all sequence tags
        subset_data = self._create_frame_subset_data_sequence(context)

        self.log.debug("__ subset_data: {}".format(
            pformat(subset_data)
        ))

        # create instances
        self._create_instances(subset_data)

    def _get_tag_data(self, tag):
        data = {}

        # get tag metadata attribute
        tag_data = tag.metadata()

        # convert tag metadata to normal keys names and values to correct types
        for k, v in dict(tag_data).items():
            key = k.replace("tag.", "")

            try:
                # capture exceptions which are related to strings only
                if re.match(r"^[\d]+$", v):
                    value = int(v)
                elif re.match(r"^True$", v):
                    value = True
                elif re.match(r"^False$", v):
                    value = False
                elif re.match(r"^None$", v):
                    value = None
                elif re.match(r"^[\w\d_]+$", v):
                    value = v
                else:
                    value = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                value = v

            data[key] = value

        return data

    def _create_frame_subset_data_sequence(self, context):

        sequence_tags = []
        sequence = context.data["activeTimeline"]

        # get all publishable sequence frames
        publish_frames = range(int(sequence.duration() + 1))

        self.log.debug("__ publish_frames: {}".format(
            pformat(publish_frames)
        ))

        # get all sequence tags
        for tag in sequence.tags():
            tag_data = self._get_tag_data(tag)
            self.log.debug("__ tag_data: {}".format(
                pformat(tag_data)
            ))
            if not tag_data:
                continue

            if "family" not in tag_data:
                continue

            if tag_data["family"] != "frame":
                continue

            sequence_tags.append(tag_data)

        self.log.debug("__ sequence_tags: {}".format(
            pformat(sequence_tags)
        ))

        # first collect all available subset tag frames
        subset_data = {}
        for tag_data in sequence_tags:
            frame = int(tag_data["start"])

            if frame not in publish_frames:
                continue

            subset = tag_data["subset"]

            if subset in subset_data:
                # update existing subset key
                subset_data[subset]["frames"].append(frame)
            else:
                # create new subset key
                subset_data[subset] = {
                    "frames": [frame],
                    "format": tag_data["format"],
                    "asset": context.data["assetEntity"]["name"]
                }
        return subset_data

    def _create_instances(self, subset_data):
        # create instance per subset
        for subset_name, subset_data in subset_data.items():
            name = "frame" + subset_name.title()
            data = {
                "name": name,
                "label": "{} {}".format(name, subset_data["frames"]),
                "family": "image",
                "families": ["frame"],
                "asset": subset_data["asset"],
                "subset": subset_name,
                "format": subset_data["format"],
                "frames": subset_data["frames"]
            }
            self._context.create_instance(**data)

            self.log.info(
                "Created instance: {}".format(
                    json.dumps(data, sort_keys=True, indent=4)
                )
            )
