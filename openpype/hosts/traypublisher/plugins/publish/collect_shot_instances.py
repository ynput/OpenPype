from pprint import pformat
import pyblish.api
import opentimelineio as otio

from openpype import AYON_SERVER_ENABLED


class CollectShotInstance(pyblish.api.InstancePlugin):
    """ Collect shot instances

    Resolving its user inputs from creator attributes
    to instance data.
    """

    label = "Collect Shot Instances"
    order = pyblish.api.CollectorOrder - 0.09

    hosts = ["traypublisher"]
    families = ["shot"]

    SHARED_KEYS = [
        "asset",
        "fps",
        "handleStart",
        "handleEnd",
        "frameStart",
        "frameEnd",
        "clipIn",
        "clipOut",
        "clipDuration",
        "sourceIn",
        "sourceOut",
        "otioClip",
        "workfileFrameStart"
    ]

    def process(self, instance):
        creator_identifier = instance.data["creator_identifier"]
        if "editorial" not in creator_identifier:
            return

        # get otio clip object
        otio_clip = self._get_otio_clip(instance)
        instance.data["otioClip"] = otio_clip

        # first solve the inputs from creator attr
        data = self._solve_inputs_to_data(instance)
        instance.data.update(data)

        # distribute all shared keys to clips instances
        self._distribute_shared_data(instance)
        self._solve_hierarchy_context(instance)

        self.log.debug(pformat(instance.data))

    def _get_otio_clip(self, instance):
        """ Converts otio string data.

        Convert them to proper otio object
        and finds its equivalent at otio timeline.
        This process is a hack to support also
        resolving parent range.

        Args:
            instance (obj): publishing instance

        Returns:
            otio.Clip: otio clip object
        """
        context = instance.context
        # convert otio clip from string to object
        otio_clip_string = instance.data.pop("otioClip")
        otio_clip = otio.adapters.read_from_string(
            otio_clip_string)

        otio_timeline = context.data["otioTimeline"]

        clips = [
            clip for clip in otio_timeline.each_child(
                descended_from_type=otio.schema.Clip)
            if clip.name == otio_clip.name
            if clip.parent().kind == "Video"
        ]

        otio_clip = clips.pop()

        return otio_clip

    def _distribute_shared_data(self, instance):
        """ Distribute all defined keys.

        All data are shared between all related
        instances in context.

        Args:
            instance (obj): publishing instance
        """
        context = instance.context

        instance_id = instance.data["instance_id"]

        if not context.data.get("editorialSharedData"):
            context.data["editorialSharedData"] = {}

        context.data["editorialSharedData"][instance_id] = {
            _k: _v for _k, _v in instance.data.items()
            if _k in self.SHARED_KEYS
        }

    def _solve_inputs_to_data(self, instance):
        """ Resolve all user inputs into instance data.

        Args:
            instance (obj): publishing instance

        Returns:
            dict: instance data updating data
        """
        _cr_attrs = instance.data["creator_attributes"]
        workfile_start_frame = _cr_attrs["workfile_start_frame"]
        frame_start = _cr_attrs["frameStart"]
        frame_end = _cr_attrs["frameEnd"]
        frame_dur = frame_end - frame_start

        data = {
            "fps": float(_cr_attrs["fps"]),
            "handleStart": _cr_attrs["handle_start"],
            "handleEnd": _cr_attrs["handle_end"],
            "frameStart": workfile_start_frame,
            "frameEnd": workfile_start_frame + frame_dur,
            "clipIn": _cr_attrs["clipIn"],
            "clipOut": _cr_attrs["clipOut"],
            "clipDuration": _cr_attrs["clipDuration"],
            "sourceIn": _cr_attrs["sourceIn"],
            "sourceOut": _cr_attrs["sourceOut"],
            "workfileFrameStart": workfile_start_frame
        }
        if AYON_SERVER_ENABLED:
            data["asset"] = _cr_attrs["folderPath"]
        else:
            data["asset"] = _cr_attrs["shotName"]

        return data

    def _solve_hierarchy_context(self, instance):
        """ Adding hierarchy data to context shared data.

        Args:
            instance (obj): publishing instance
        """
        context = instance.context

        final_context = (
            context.data["hierarchyContext"]
            if context.data.get("hierarchyContext")
            else {}
        )

        # get handles
        handle_start = int(instance.data["handleStart"])
        handle_end = int(instance.data["handleEnd"])

        in_info = {
            "entity_type": "Shot",
            "custom_attributes": {
                "handleStart": handle_start,
                "handleEnd": handle_end,
                "frameStart": instance.data["frameStart"],
                "frameEnd": instance.data["frameEnd"],
                "clipIn": instance.data["clipIn"],
                "clipOut": instance.data["clipOut"],
                "fps": instance.data["fps"]
            },
            "tasks": instance.data["tasks"]
        }

        parents = instance.data.get('parents', [])

        # Split by '/' for AYON where asset is a path
        asset_name = instance.data["asset"].split("/")[-1]
        actual = {asset_name: in_info}

        for parent in reversed(parents):
            parent_name = parent["entity_name"]
            next_dict = {
                parent_name: {
                    "entity_type": parent["entity_type"],
                    "childs": actual
                }
            }
            actual = next_dict

        final_context = self._update_dict(final_context, actual)

        # adding hierarchy context to instance
        context.data["hierarchyContext"] = final_context

    def _update_dict(self, ex_dict, new_dict):
        """ Recursion function

        Updating nested data with another nested data.

        Args:
            ex_dict (dict): nested data
            new_dict (dict): nested data

        Returns:
            dict: updated nested data
        """
        for key in ex_dict:
            if key in new_dict and isinstance(ex_dict[key], dict):
                new_dict[key] = self._update_dict(ex_dict[key], new_dict[key])
            elif not ex_dict.get(key) or not new_dict.get(key):
                new_dict[key] = ex_dict[key]

        return new_dict
