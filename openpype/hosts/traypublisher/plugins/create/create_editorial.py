import os
from copy import deepcopy
from pprint import pformat
import opentimelineio as otio
from openpype.client import (
    get_asset_by_name,
    get_project
)
from openpype.hosts.traypublisher.api.plugin import (
    TrayPublishCreator,
    InvisibleTrayPublishCreator
)
from openpype.hosts.traypublisher.api.editorial import (
    ShotMetadataSover
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
            "from_selection": "From selection",
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


class EditorialClipInstanceCreatorBase(InvisibleTrayPublishCreator):
    host_name = "traypublisher"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialClipInstanceCreatorBase, self).__init__(
            project_settings, *args, **kwargs
        )

    def create(self, instance_data, source_data=None):
        self.log.info(f"instance_data: {instance_data}")
        subset_name = instance_data["subset"]

        return self._create_instance(subset_name, instance_data)

    def _create_instance(self, subset_name, data):

        # Create new instance
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        self.log.info(f"instance_data: {pformat(new_instance.data)}")

        # Host implementation of storing metadata about instance
        HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)

        return new_instance


class EditorialShotInstanceCreator(EditorialClipInstanceCreatorBase):
    identifier = "editorial_shot"
    family = "shot"
    label = "Editorial Shot"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialShotInstanceCreator, self).__init__(
            project_settings, *args, **kwargs
        )

    def get_instance_attr_defs(self):
        attr_defs = [
            TextDef(
                "asset_name",
                label="Asset name",
            )
        ]
        attr_defs.extend(CLIP_ATTR_DEFS)
        return attr_defs


class EditorialPlateInstanceCreator(EditorialClipInstanceCreatorBase):
    identifier = "editorial_plate"
    family = "plate"
    label = "Editorial Plate"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialPlateInstanceCreator, self).__init__(
            project_settings, *args, **kwargs
        )


class EditorialAudioInstanceCreator(EditorialClipInstanceCreatorBase):
    identifier = "editorial_audio"
    family = "audio"
    label = "Editorial Audio"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialAudioInstanceCreator, self).__init__(
            project_settings, *args, **kwargs
        )


class EditorialReviewInstanceCreator(EditorialClipInstanceCreatorBase):
    identifier = "editorial_review"
    family = "review"
    label = "Editorial Review"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialReviewInstanceCreator, self).__init__(
            project_settings, *args, **kwargs
        )


class EditorialSimpleCreator(TrayPublishCreator):

    label = "Editorial Simple"
    family = "editorial"
    identifier = "editorial_simple"
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
        self._shot_metadata_solver = ShotMetadataSover(
            self._creator_settings, self.log)

        # try to set main attributes from settings
        if self._creator_settings.get("default_variants"):
            self.default_variants = self._creator_settings["default_variants"]

    def create(self, subset_name, instance_data, pre_create_data):
        allowed_family_presets = self._get_allowed_family_presets(
            pre_create_data)

        clip_instance_properties = {
            k: v for k, v in pre_create_data.items()
            if k != "sequence_filepath_data"
            if k not in [
                i["family"] for i in self._creator_settings["family_presets"]
            ]
        }
        # Create otio editorial instance
        asset_name = instance_data["asset"]
        asset_doc = get_asset_by_name(self.project_name, asset_name)

        self.log.info(pre_create_data["fps"])

        if pre_create_data["fps"] == "from_selection":
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
            "parent_asset_name": asset_name,
            "variant": instance_data["variant"]
        })
        self._get_clip_instances(
            otio_timeline,
            clip_instance_properties,
            family_presets=allowed_family_presets

        )

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
            "sequenceFilePath": file_path,
            "otioTimeline": otio.adapters.write_to_string(otio_timeline)
        })

        self._create_instance(self.family, subset_name, data)

        return otio_timeline

    def _get_clip_instances(
        self,
        otio_timeline,
        clip_instance_properties,
        family_presets
    ):
        self.asset_name_check = []

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

                base_instance_data = self._get_base_instance_data(
                    clip,
                    clip_instance_properties,
                    track_start_frame
                )

                parenting_data = {
                    "instance_label": None,
                    "instance_id": None
                }
                self.log.info(
                    f"Creating subsets from presets: \n{pformat(family_presets)}")

                for _fpreset in family_presets:
                    instance = self._make_subset_instance(
                        _fpreset,
                        deepcopy(base_instance_data),
                        parenting_data
                    )
                    self.log.debug(f"{pformat(dict(instance.data))}")

    def _make_subset_instance(
        self,
        _fpreset,
        future_instance_data,
        parenting_data
    ):
        family = _fpreset["family"]
        label = self._make_subset_naming(
            _fpreset,
            future_instance_data
        )
        future_instance_data["label"] = label

        # add file extension filter only if it is not shot family
        if family == "shot":
            c_instance = self.create_context.creators[
                "editorial_shot"].create(
                    future_instance_data)
            parenting_data.update({
                "instance_label": label,
                "instance_id": c_instance.data["instance_id"]
            })

        else:
            # add review family if defined
            future_instance_data.update({
                "filterExt": _fpreset["filter_ext"],
                "parent_instance_id": parenting_data["instance_id"],
                "creator_attributes": {
                    "parent_instance": parenting_data["instance_label"]
                },
                "publish_attributes": {
                    "CollectReviewFamily": {
                        "add_review_family": _fpreset.get("review")
                    }
                }
            })

            creator_identifier = f"editorial_{family}"
            editorial_clip_creator = self.create_context.creators[
                creator_identifier]
            c_instance = editorial_clip_creator.create(
                future_instance_data)

        return c_instance

    def _make_subset_naming(
        self,
        _fpreset,
        future_instance_data
    ):
        shot_name = future_instance_data["shotName"]
        variant_name = future_instance_data["variant"]
        family = _fpreset["family"]

        # get variant name from preset or from inharitance
        _variant_name = _fpreset.get("variant") or variant_name

        self.log.debug(f"__ family: {family}")
        self.log.debug(f"__ _fpreset: {_fpreset}")

        # subset name
        subset_name = "{}{}".format(
            family, _variant_name.capitalize()
        )
        label = "{}_{}".format(
            shot_name,
            subset_name
        )

        future_instance_data.update({
            "family": family,
            "label": label,
            "variant": _variant_name,
            "subset": subset_name,
        })

        return label

    def _get_base_instance_data(
        self,
        clip,
        clip_instance_properties,
        track_start_frame,
    ):
        # get clip instance properties
        parent_asset_name = clip_instance_properties["parent_asset_name"]
        handle_start = clip_instance_properties["handle_start"]
        handle_end = clip_instance_properties["handle_end"]
        timeline_offset = clip_instance_properties["timeline_offset"]
        workfile_start_frame = clip_instance_properties["workfile_start_frame"]
        fps = clip_instance_properties["fps"]
        variant_name = clip_instance_properties["variant"]

        # basic unique asset name
        clip_name = os.path.splitext(clip.name)[0].lower()
        project_doc = get_project(self.project_name)

        shot_name, shot_metadata = self._shot_metadata_solver.generate_data(
            clip_name,
            {
                "anatomy_data": {
                    "project": {
                        "name": self.project_name,
                        "code": project_doc["data"]["code"]
                    },
                    "parent": parent_asset_name,
                    "app": self.host_name
                },
                "selected_asset_doc": get_asset_by_name(
                    self.project_name, parent_asset_name),
                "project_doc": project_doc
            }
        )

        self._validate_name_uniqueness(shot_name)

        timing_data = self._get_timing_data(
            clip,
            timeline_offset,
            track_start_frame,
            workfile_start_frame
        )

        # create creator attributes
        creator_attributes = {
            "asset_name": shot_name,
            "Parent hierarchy path": shot_metadata["hierarchy"],
            "workfile_start_frame": workfile_start_frame,
            "fps": fps,
            "handle_start": int(handle_start),
            "handle_end": int(handle_end)
        }
        creator_attributes.update(timing_data)

        # create shared new instance data
        base_instance_data = {
            "shotName": shot_name,
            "variant": variant_name,

            # HACK: just for temporal bug workaround
            # TODO: should loockup shot name for update
            "asset": parent_asset_name,
            "task": "",
            # parent time properties
            "trackStartFrame": track_start_frame,
            "timelineOffset": timeline_offset,
            # creator_attributes
            "creator_attributes": creator_attributes
        }
        # add hierarchy shot metadata
        base_instance_data.update(shot_metadata)

        return base_instance_data

    def _get_timing_data(
        self,
        clip,
        timeline_offset,
        track_start_frame,
        workfile_start_frame
    ):
        # frame ranges data
        clip_in = clip.range_in_parent().start_time.value
        clip_in += track_start_frame
        clip_out = clip.range_in_parent().end_time_inclusive().value
        clip_out += track_start_frame
        self.log.info(f"clip_in: {clip_in} | clip_out: {clip_out}")

        # add offset in case there is any
        self.log.debug(f"__ timeline_offset: {timeline_offset}")
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

        return {
            "frameStart": int(frame_start),
            "frameEnd": int(frame_end),
            "clipIn": int(clip_in),
            "clipOut": int(clip_out),
            "sourceIn": int(source_in),
            "sourceOut": int(source_out)
        }

    def _get_allowed_family_presets(self, pre_create_data):
        self.log.debug(f"__ pre_create_data: {pre_create_data}")
        return [
            {"family": "shot"},
            *[
                preset for preset in self._creator_settings["family_presets"]
                if pre_create_data[preset["family"]]
            ]
        ]

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
            # TODO: perhpas better would be timecode and fps input
            NumberDef(
                "timeline_offset",
                default=0,
                label="Timeline offset"
            ),
            UISeparatorDef(),
            UILabelDef("Clip instance attributes"),
            UISeparatorDef()
        ]
        # add variants swithers
        attr_defs.extend(
            BoolDef(_var["family"], label=_var["family"])
            for _var in self._creator_settings["family_presets"]
        )
        attr_defs.append(UISeparatorDef())

        attr_defs.extend(CLIP_ATTR_DEFS)
        return attr_defs