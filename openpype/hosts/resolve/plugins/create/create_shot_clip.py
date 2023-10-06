import copy

from openpype.hosts.resolve.api import plugin, lib
from openpype.hosts.resolve.api.lib import (
    get_video_track_names,
    create_bin,
)
from openpype.pipeline.create import CreatorError, CreatedInstance
from openpype.lib import BoolDef, EnumDef, TextDef, UILabelDef, NumberDef


class CreateShotClip(plugin.Creator):
    """Publishable clip"""

    identifier = "io.openpype.creators.resolve.clip"
    label = "Create Publishable Clip"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    create_allow_context_change = False
    create_allow_thumbnail = False

    def get_pre_create_attr_defs(self):

        def header_label(text):
            return f"<br><b>{text}</b>"

        tokens_help = """\nUsable tokens:
    {_clip_}: name of used clip
    {_track_}: name of parent track layer
    {_sequence_}: name of parent sequence (timeline)"""
        # gui_name = "OpenPype publish attributes creator"
        # gui_info = "Define sequential rename and fill hierarchy data."
        gui_tracks = get_video_track_names()

        # TODO: Apply defaults from `presets` in project settings
        # get key pares from presets and match it on ui inputs
        # for k, v in self.gui_inputs.items():
        #     if v["type"] in ("dict", "section"):
        #         # nested dictionary (only one level allowed
        #         # for sections and dict)
        #         for _k, _v in v["value"].items():
        #             if self.presets.get(_k) is not None:
        #                 self.gui_inputs[k][
        #                     "value"][_k]["value"] = self.presets[_k]
        #     if self.presets.get(k):
        #         self.gui_inputs[k]["value"] = self.presets[k]

        return [

            # renameHierarchy
            UILabelDef(
                label=header_label("Shot Hierarchy And Rename Settings")
            ),
            TextDef(
                "hierarchy",
                label="Shot Parent Hierarchy",
                tooltip="Parents folder for shot root folder, "
                        "Template filled with *Hierarchy Data* section",
                default="{folder}/{sequence}",
            ),
            BoolDef(
                "clipRename",
                label="Rename clips",
                tooltip="Renaming selected clips on fly",
                default=False,
            ),
            TextDef(
                "clipName",
                label="Clip Name Template",
                tooltip="template for creating shot names, used for "
                        "renaming (use rename: on)",
                default="{sequence}{shot}",
            ),
            NumberDef(
                "countFrom",
                label="Count sequence from",
                tooltip="Set where the sequence number starts from",
                default=10,
            ),
            NumberDef(
                "countSteps",
                label="Stepping number",
                tooltip="What number is adding every new step",
                default=10,
            ),

            # hierarchyData
            UILabelDef(
                label=header_label("Shot Template Keywords")
            ),
            TextDef(
                "folder",
                label="{folder}",
                tooltip="Name of folder used for root of generated shots.\n"
                        f"{tokens_help}",
                default="shots",
            ),
            TextDef(
                "episode",
                label="{episode}",
                tooltip=f"Name of episode.\n{tokens_help}",
                default="ep01",
            ),
            TextDef(
                "sequence",
                label="{sequence}",
                tooltip=f"Name of sequence of shots.\n{tokens_help}",
                default="sq01",
            ),
            TextDef(
                "track",
                label="{track}",
                tooltip=f"Name of timeline track.\n{tokens_help}",
                default="{_track_}",
            ),
            TextDef(
                "shot",
                label="{shot}",
                tooltip="Name of shot. '#' is converted to padded number."
                        f"\n{tokens_help}",
                default="sh###",
            ),

            # verticalSync
            UILabelDef(
                label=header_label("Vertical Synchronization Of Attributes")
            ),
            BoolDef(
                "vSyncOn",
                label="Enable Vertical Sync",
                tooltip="Switch on if you want clips above "
                        "each other to share its attributes",
                default=True,
            ),
            EnumDef(
                "vSyncTrack",
                label="Hero track",
                tooltip="Select driving track name which should "
                        "be mastering all others",
                items=gui_tracks or ["<nothing to select>"],
            ),

            # publishSettings
            UILabelDef(
                label=header_label("Publish Settings")
            ),
            EnumDef(
                "subsetName",
                label="Subset Name",
                tooltip="chose subset name pattern, if <track_name> "
                        "is selected, name of track layer will be used",
                items=['<track_name>', 'main', 'bg', 'fg', 'bg', 'animatic'],
            ),
            EnumDef(
                "subsetFamily",
                label="Subset Family",
                tooltip="What use of this subset is for",
                items=['plate', 'take'],
            ),
            EnumDef(
                "reviewTrack",
                label="Use Review Track",
                tooltip="Generate preview videos on fly, if "
                        "'< none >' is defined nothing will be generated.",
                items=['< none >'] + gui_tracks,
            ),
            BoolDef(
                "audio",
                label="Include audio",
                tooltip="Process subsets with corresponding audio",
                default=False,
            ),
            BoolDef(
                "sourceResolution",
                label="Source resolution",
                tooltip="Is resloution taken from timeline or source?",
                default=False,
            ),

            # shotAttr
            UILabelDef(
                label=header_label("Shot Attributes"),
            ),
            NumberDef(
                "workfileFrameStart",
                label="Workfiles Start Frame",
                tooltip="Set workfile starting frame number",
                default=1001,
            ),
            NumberDef(
                "handleStart",
                label="Handle start (head)",
                tooltip="Handle at start of clip",
                default=0,
            ),
            NumberDef(
                "handleEnd",
                label="Handle end (tail)",
                tooltip="Handle at end of clip",
                default=0,
            ),
        ]

    presets = None
    rename_index = 0

    def create(self, subset_name, instance_data, pre_create_data):
        super(CreateShotClip, self).create(subset_name,
                                           instance_data,
                                           pre_create_data)

        if len(self.selected) < 1:
            return

        self.log.info(self.selected)

        if not self.timeline:
            raise CreatorError(
                "You must be in an active timeline to "
                "create the publishable clips.\n\n"
                "Go into a timeline and then reset the publisher."
            )

        self.log.debug(f"Selected: {self.selected}")

        # sort selected trackItems by vSync track
        sorted_selected_track_items = []
        unsorted_selected_track_items = []
        v_sync_track = pre_create_data.get("vSyncTrack", "")
        for track_item_data in self.selected:
            if track_item_data["track"]["name"] in v_sync_track:
                sorted_selected_track_items.append(track_item_data)
            else:
                unsorted_selected_track_items.append(track_item_data)

        sorted_selected_track_items.extend(unsorted_selected_track_items)

        # create media bin for compound clips (trackItems)
        media_pool_folder = create_bin(self.timeline.GetName())

        # Get the to imprint data
        # TODO: Make sure the correct data is added with new creator as
        #   it was with legacy. We will somehow need to persist the correct
        #   data per instance entry in the publisher UI?
        # data["id"] = "pyblish.avalon.instance"
        # data["family"] = self.family
        # data["asset"] = asset
        # data["subset"] = name
        # data["active"] = True

        instances = []
        for i, track_item_data in enumerate(sorted_selected_track_items):
            self.log.info(
                "Processing track item data: {}".format(track_item_data)
            )

            # convert track item to timeline media pool item
            publish_clip = plugin.PublishClip(
                track_item_data,
                pre_create_data,
                media_pool_folder,
                rename_index=i,
                # TODO: Refactor `avalon` to more sensible argument name
                avalon=instance_data)

            track_item = publish_clip.convert()
            if track_item is None:
                # Ignore input clips that do not convert into a track item
                # from `PublishClip.convert`
                continue

            track_item.SetClipColor(lib.publish_clip_color)

            instance_data = copy.deepcopy(instance_data)
            # TODO: set 'task', 'family' and 'variant' correctly
            #  and build its subset name correctly
            # TODO: We can't set the asset because the asset does not exist
            #   and the new publisher doesn't like non-existing assets
            # instance_data["asset"] = publish_clip.tag_data["asset"]
            # instance_data["variant"] = publish_clip.subset_name

            # Create the Publisher instance
            instance = CreatedInstance(
                family=self.family,
                subset_name=publish_clip.subset_name,
                data=instance_data,
                creator=self
            )
            instance.transient_data["track_item"] = track_item
            self._add_instance_to_context(instance)

            # self.imprint_instance_node(instance_node,
            #                            data=instance.data_to_store())
            instances.append(instance)
        return instances

    def collect_instances(self):
        """Collect all created instances from current timeline."""
        selected_timeline_items = lib.get_current_timeline_items(
            filter=True, selecting_color=lib.publish_clip_color)

        instances = []
        for timeline_item_data in selected_timeline_items:
            timeline_item = timeline_item_data["clip"]["item"]

            # get openpype tag data
            tag_data = lib.get_timeline_item_pype_tag(timeline_item)
            if not tag_data:
                continue

            instance = CreatedInstance.from_existing(tag_data, self)
            instance.transient_data["track_item"] = timeline_item
            self._add_instance_to_context(instance)

        return instances

    def update_instances(self, update_list):
        """Store changes of existing instances so they can be recollected.

        Args:
            update_list(List[UpdateData]): Gets list of tuples. Each item
                contain changed instance and it's changes.
        """
        for created_inst, _changes in update_list:
            track_item = created_inst.transient_data["track_item"]
            data = created_inst.data_to_store()
            self.log.info(f"Storing data: {data}")

            lib.imprint(track_item, data)

    def remove_instances(self, instances):
        """Remove instance marker from track item.

        Args:
            instance(List[CreatedInstance]): Instance objects which should be
                removed.
        """
        for instance in instances:
            track_item = instance.transient_data["track_item"]

            # removing instance by marker color
            print(f"Removing instance: {track_item.GetName()}")
            track_item.DeleteMarkersByColor(lib.pype_marker_color)

            self._remove_instance_from_context(instance)
