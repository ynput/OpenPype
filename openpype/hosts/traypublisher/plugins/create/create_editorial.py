import os
from copy import deepcopy
from pprint import pformat
import opentimelineio as otio
from openpype.client import get_asset_by_name
from openpype.hosts.traypublisher.api.plugin import (
    TrayPublishCreator,
    InvisibleTrayPublishCreator
)


from openpype.pipeline import CreatedInstance

from openpype.lib import (
    FileDef,
    TextDef,
    NumberDef,
    EnumDef,
    BoolDef,
    UISeparatorDef,
    UILabelDef
)

from openpype.hosts.traypublisher.api.pipeline import HostContext


CLIP_ATTR_DEFS = [
    EnumDef(
        "fps",
        items={
            "from_project": "From project",
            23.997: "23.976",
            24: "24",
            25: "25",
            29.97: "29.97",
            30: "30"
        },
        label="FPS"
    ),
    NumberDef(
        "workfile_start_frame",
        default=1001,
        label="Workfile start frame"
    ),
    NumberDef(
        "handle_start",
        default=0,
        label="Handle start"
    ),
    NumberDef(
        "handle_end",
        default=0,
        label="Handle end"
    )
]


class EditorialClipInstanceCreator(InvisibleTrayPublishCreator):
    identifier = "editorialClip"
    family = "clip"
    host_name = "traypublisher"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialClipInstanceCreator, self).__init__(
            project_settings, *args, **kwargs
        )

    def create(self, instance_data, source_data):
        self.log.info(f"instance_data: {instance_data}")
        subset_name = instance_data["subset"]
        family = instance_data["family"]

        return self._create_instance(subset_name, family, instance_data)

    def _create_instance(self, subset_name, family, data):

        # Create new instance
        new_instance = CreatedInstance(family, subset_name, data, self)
        self.log.info(f"instance_data: {pformat(new_instance.data)}")

        # Host implementation of storing metadata about instance
        HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)

        return new_instance

    def get_instance_attr_defs(self):
        attr_defs = [
            TextDef(
                "asset_name",
                label="Asset name",
            )
        ]
        attr_defs.extend(CLIP_ATTR_DEFS)
        return attr_defs


class EditorialSimpleCreator(TrayPublishCreator):

    label = "Editorial Simple"
    family = "editorial"
    identifier = "editorialSimple"
    default_variants = [
        "main"
    ]
    description = "Editorial files to generate shots."
    detailed_description = """
Supporting publishing new shots to project
or updating already created. Publishing will create OTIO file.
"""
    icon = "fa.file"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialSimpleCreator, self).__init__(
            project_settings, *args, **kwargs
        )
        editorial_creators = deepcopy(
            project_settings["traypublisher"]["editorial_creators"]
        )
        # get this creator settings by identifier
        self._creator_settings = editorial_creators.get(self.identifier)

        # try to set main attributes from settings
        if self._creator_settings.get("default_variants"):
            self.default_variants = self._creator_settings["default_variants"]

    def create(self, subset_name, instance_data, pre_create_data):
        clip_instance_properties = {
            k: v for k, v in pre_create_data.items()
            if k != "sequence_filepath_data"
        }
        # Create otio editorial instance
        asset_name = instance_data["asset"]
        asset_doc = get_asset_by_name(self.project_name, asset_name)

        self.log.info(pre_create_data["fps"])

        if pre_create_data["fps"] == "from_project":
            # get asset doc data attributes
            fps = asset_doc["data"]["fps"]
        else:
            fps = float(pre_create_data["fps"])

        instance_data.update({
            "fps": fps
        })

        # get otio timeline
        otio_timeline = self._create_otio_instance(
            subset_name, instance_data, pre_create_data)

        # Create all clip instances
        clip_instance_properties.update({
            "fps": fps,
            "parent_asset_name": asset_name
        })
        self._get_clip_instances(
            otio_timeline, clip_instance_properties)

    def _create_otio_instance(self, subset_name, data, pre_create_data):
        # get path of sequence
        file_path_data = pre_create_data["sequence_filepath_data"]

        if len(file_path_data["filenames"]) == 0:
            raise FileExistsError("File path was not added")

        file_path = os.path.join(
            file_path_data["directory"], file_path_data["filenames"][0])

        self.log.info(f"file_path: {file_path}")

        # get editorial sequence file into otio timeline object
        extension = os.path.splitext(file_path)[1]
        kwargs = {}
        if extension == ".edl":
            # EDL has no frame rate embedded so needs explicit
            # frame rate else 24 is asssumed.
            kwargs["rate"] = data["fps"]

        self.log.info(f"kwargs: {kwargs}")
        otio_timeline = otio.adapters.read_from_file(
            file_path, **kwargs)

        # Pass precreate data to creator attributes
        data.update({
            "sequence_file_path": file_path
        })

        self._create_instance(self.family, subset_name, data)

        return otio_timeline

    def _get_clip_instances(
        self,
        otio_timeline,
        clip_instance_properties
    ):
        family = "plate"

        # get clip instance properties
        parent_asset_name = clip_instance_properties["parent_asset_name"]
        handle_start = clip_instance_properties["handle_start"]
        handle_end = clip_instance_properties["handle_end"]
        timeline_offset = clip_instance_properties["timeline_offset"]
        workfile_start_frame = clip_instance_properties["workfile_start_frame"]
        fps = clip_instance_properties["fps"]

        self.asset_name_check = []

        editorial_clip_creator = self.create_context.creators["editorialClip"]

        tracks = otio_timeline.each_child(
            descended_from_type=otio.schema.Track
        )

        for track in tracks:
            self.log.debug(f"track.name: {track.name}")
            try:
                track_start_frame = (
                    abs(track.source_range.start_time.value)
                )
                self.log.debug(f"track_start_frame: {track_start_frame}")
                track_start_frame -= self.timeline_frame_start
            except AttributeError:
                track_start_frame = 0

            self.log.debug(f"track_start_frame: {track_start_frame}")

            for clip in track.each_child():

                if not self._validate_clip_for_processing(clip):
                    continue

                # basic unique asset name
                clip_name = os.path.splitext(clip.name)[0].lower()
                name = f"{parent_asset_name.split('_')[0]}_{clip_name}"

                # make sure the name is unique
                self._validate_name_uniqueness(name)

                # frame ranges data
                clip_in = clip.range_in_parent().start_time.value
                clip_in += track_start_frame
                clip_out = clip.range_in_parent().end_time_inclusive().value
                clip_out += track_start_frame
                self.log.info(f"clip_in: {clip_in} | clip_out: {clip_out}")

                # add offset in case there is any
                if timeline_offset:
                    clip_in += timeline_offset
                    clip_out += timeline_offset

                clip_duration = clip.duration().value
                self.log.info(f"clip duration: {clip_duration}")

                source_in = clip.trimmed_range().start_time.value
                source_out = source_in + clip_duration

                # define starting frame for future shot
                frame_start = (
                    clip_in if workfile_start_frame is None
                    else workfile_start_frame
                )
                frame_end = frame_start + (clip_duration - 1)

                # subset name
                variant = self.get_variant()
                self.log.info(
                    f"__ variant: {variant}")

                subset_name = "{}{}".format(
                    family, variant.capitalize()
                )
                label = "{}_{}".format(
                    clip_name,
                    subset_name
                )
                # create shared new instance data
                instance_data = {
                    "label": label,
                    "variant": variant,
                    "family": family,
                    "families": ["clip"],
                    "subset": subset_name,

                    # HACK: just for temporal bug workaround
                    # TODO: should loockup shot name for update
                    "asset": parent_asset_name,
                    "name": clip_name,

                    # parent time properties
                    "trackStartFrame": track_start_frame,

                    # creator_attributes
                    "creator_attributes": {
                        "asset_name": clip_name,
                        "timeline_offset": timeline_offset,
                        "workfile_start_frame": workfile_start_frame,
                        "frameStart": frame_start,
                        "frameEnd": frame_end,
                        "fps": fps,
                        "handle_start": handle_start,
                        "handle_end": handle_end,
                        "clipIn": clip_in,
                        "clipOut": clip_out,
                        "sourceIn": source_in,
                        "sourceOut": source_out,
                    }
                }

                c_instance = editorial_clip_creator.create(instance_data, {})
                self.log.debug(f"{pformat(dict(c_instance.data))}")

    def _validate_clip_for_processing(self, clip):
        if clip.name is None:
            return False

        if isinstance(clip, otio.schema.Gap):
            return False

        # skip all generators like black empty
        if isinstance(
            clip.media_reference,
                otio.schema.GeneratorReference):
            return False

        # Transitions are ignored, because Clips have the full frame
        # range.
        if isinstance(clip, otio.schema.Transition):
            return False

        return True

    def _validate_name_uniqueness(self, name):
        if name not in self.asset_name_check:
            self.asset_name_check.append(name)
        else:
            self.log.warning(f"duplicate shot name: {name}")

    def _create_instance(self, family, subset_name, data):
        # Create new instance
        new_instance = CreatedInstance(family, subset_name, data, self)
        # Host implementation of storing metadata about instance
        HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attrobites
        attr_defs = [
            FileDef(
                "sequence_filepath_data",
                folders=False,
                extensions=[
                    ".edl",
                    ".xml",
                    ".aaf",
                    ".fcpxml"
                ],
                allow_sequences=False,
                label="Filepath",
            ),
            UILabelDef("Clip instance attributes"),
            UISeparatorDef(),
            # TODO: perhpas better would be timecode and fps input
            NumberDef(
                "timeline_offset",
                default=900000,
                label="Timeline offset"
            ),
            UISeparatorDef()
        ]
        attr_defs.extend(CLIP_ATTR_DEFS)
        return attr_defs
