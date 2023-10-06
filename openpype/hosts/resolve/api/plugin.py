import re
import uuid

import qargparse

from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline import (
    LoaderPlugin,
    Creator as NewCreator
)
from openpype.lib import BoolDef

from . import lib


class ClipLoader:

    active_bin = None
    data = dict()

    def __init__(self, cls, context, path, **options):
        """ Initialize object

        Arguments:
            cls (openpype.pipeline.load.LoaderPlugin): plugin object
            context (dict): loader plugin context
            options (dict)[optional]: possible keys:
                projectBinPath: "path/to/binItem"

        """
        self.__dict__.update(cls.__dict__)
        self.context = context
        self.active_project = lib.get_current_project()
        self.fname = path

        # try to get value from options or evaluate key value for `handles`
        self.with_handles = options.get("handles") or bool(
            options.get("handles") is True)
        # try to get value from options or evaluate key value for `load_to`
        self.new_timeline = options.get("newTimeline") or bool(
            "New timeline" in options.get("load_to", ""))

        assert self._populate_data(), str(
            "Cannot Load selected data, look into database "
            "or call your supervisor")

        # inject asset data to representation dict
        self._get_asset_data()
        print("__init__ self.data: `{}`".format(self.data))

        # add active components to class
        if self.new_timeline:
            if options.get("timeline"):
                # if multiselection is set then use options sequence
                self.active_timeline = options["timeline"]
            else:
                # create new sequence
                self.active_timeline = (
                    lib.get_current_timeline() or
                    lib.get_new_timeline()
                )
        else:
            self.active_timeline = lib.get_current_timeline()

        cls.timeline = self.active_timeline

    def _populate_data(self):
        """ Gets context and convert it to self.data
        data structure:
            {
                "name": "assetName_subsetName_representationName"
                "path": "path/to/file/created/by/get_repr..",
                "binPath": "projectBinPath",
            }
        """
        # create name
        repr = self.context["representation"]
        repr_cntx = repr["context"]
        asset = str(repr_cntx["asset"])
        subset = str(repr_cntx["subset"])
        representation = str(repr_cntx["representation"])
        self.data["clip_name"] = "_".join([asset, subset, representation])
        self.data["versionData"] = self.context["version"]["data"]
        # gets file path
        file = self.fname
        if not file:
            repr_id = repr["_id"]
            print(
                "Representation id `{}` is failing to load".format(repr_id))
            return None
        self.data["path"] = file.replace("\\", "/")

        # solve project bin structure path
        hierarchy = str("/".join((
            "Loader",
            repr_cntx["hierarchy"].replace("\\", "/"),
            asset
        )))

        self.data["binPath"] = hierarchy

        return True

    def _get_asset_data(self):
        """ Get all available asset data

        joint `data` key with asset.data dict into the representation

        """
        asset_name = self.context["representation"]["context"]["asset"]
        self.data["assetData"] = get_current_project_asset(asset_name)["data"]

    def load(self):
        # create project bin for the media to be imported into
        self.active_bin = lib.create_bin(self.data["binPath"])

        # create mediaItem in active project bin
        # create clip media

        media_pool_item = lib.create_media_pool_item(
            self.data["path"], self.active_bin)
        _clip_property = media_pool_item.GetClipProperty

        # get handles
        handle_start = self.data["versionData"].get("handleStart")
        handle_end = self.data["versionData"].get("handleEnd")
        if handle_start is None:
            handle_start = int(self.data["assetData"]["handleStart"])
        if handle_end is None:
            handle_end = int(self.data["assetData"]["handleEnd"])

        source_in = int(_clip_property("Start"))
        source_out = int(_clip_property("End"))

        if _clip_property("Type") == "Video":
            source_in += handle_start
            source_out -= handle_end

        # include handles
        if self.with_handles:
            source_in -= handle_start
            source_out += handle_end

        # make track item from source in bin as item
        timeline_item = lib.create_timeline_item(
            media_pool_item, self.active_timeline, source_in, source_out)

        print("Loading clips: `{}`".format(self.data["clip_name"]))
        return timeline_item

    def update(self, timeline_item):
        # create project bin for the media to be imported into
        self.active_bin = lib.create_bin(self.data["binPath"])

        # create mediaItem in active project bin
        # create clip media
        media_pool_item = lib.create_media_pool_item(
            self.data["path"], self.active_bin)
        _clip_property = media_pool_item.GetClipProperty

        source_in = int(_clip_property("Start"))
        source_out = int(_clip_property("End"))

        lib.swap_clips(
            timeline_item,
            media_pool_item,
            source_in,
            source_out
        )

        print("Loading clips: `{}`".format(self.data["clip_name"]))
        return timeline_item


class TimelineItemLoader(LoaderPlugin):
    """A basic SequenceLoader for Resolve

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    options = [
        qargparse.Toggle(
            "handles",
            label="Include handles",
            default=0,
            help="Load with handles or without?"
        ),
        qargparse.Choice(
            "load_to",
            label="Where to load clips",
            items=[
                "Current timeline",
                "New timeline"
            ],
            default=0,
            help="Where do you want clips to be loaded?"
        )
    ]

    def load(
        self,
        context,
        name=None,
        namespace=None,
        options=None
    ):
        pass

    def update(self, container, representation):
        """Update an existing `container`
        """
        pass

    def remove(self, container):
        """Remove an existing `container`
        """
        pass


class Creator(NewCreator):
    """Creator class wrapper"""

    marker_color = "Purple"
    presets = {}

    def apply_settings(self, project_settings):
        resolve_create_settings = (
            project_settings.get("resolve", {}).get("create")
        )
        self.presets = resolve_create_settings.get(
            self.__class__.__name__, {}
        )

    def create(self, subset_name, instance_data, pre_create_data):
        # adding basic current context resolve objects
        self.project = lib.get_current_project()
        self.timeline = lib.get_current_timeline()

        if pre_create_data.get("use_selection", False):
            self.selected = lib.get_current_timeline_items(filter=True)
        else:
            self.selected = lib.get_current_timeline_items(filter=False)

        # TODO: Add a way to store/imprint data

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection",
                    label="Use selection",
                    default=True)
        ]


class PublishClip:
    """
    Convert a track item to publishable instance

    Args:
        timeline_item (hiero.core.TrackItem): hiero track item object
        kwargs (optional): additional data needed for rename=True (presets)

    Returns:
        hiero.core.TrackItem: hiero track item object with openpype tag
    """
    types = {
        "shot": "shot",
        "folder": "folder",
        "episode": "episode",
        "sequence": "sequence",
        "track": "sequence",
    }

    # parents search pattern
    parents_search_pattern = r"\{([a-z]*?)\}"

    # default templates for non-ui use
    rename_default = False
    hierarchy_default = "{_folder_}/{_sequence_}/{_track_}"
    clip_name_default = "shot_{_trackIndex_:0>3}_{_clipIndex_:0>4}"
    subset_name_default = "<track_name>"
    review_track_default = "< none >"
    subset_family_default = "plate"
    count_from_default = 10
    count_steps_default = 10
    vertical_sync_default = False
    driving_layer_default = ""

    # Define which keys of the pre create data should also be 'tag data'
    tag_keys = {
        # renameHierarchy
        "hierarchy",
        # hierarchyData
        "folder", "episode", "sequence", "track", "shot",
        # publish settings
        "audio", "sourceResolution",
        # shot attributes
        "workfileFrameStart", "handleStart", "handleEnd"
    }

    def __init__(self,
                 timeline_item_data,
                 pre_create_data=None,
                 media_pool_folder=None,
                 rename_index=0,
                 avalon=None):

        self.rename_index = rename_index
        self.vertical_clip_match = dict()
        self.tag_data = dict()

        # get main parent objects
        self.timeline_item_data = timeline_item_data
        self.timeline_item = timeline_item_data["clip"]["item"]
        timeline_name = timeline_item_data["timeline"].GetName()
        self.timeline_name = str(timeline_name).replace(" ", "_")

        # track item (clip) main attributes
        self.ti_name = self.timeline_item.GetName()
        self.ti_index = int(timeline_item_data["clip"]["index"])

        # get track name and index
        track_name = timeline_item_data["track"]["name"]
        self.track_name = str(track_name).replace(" ", "_")
        self.track_index = int(timeline_item_data["track"]["index"])

        # adding tag.family into tag
        if avalon:
            self.tag_data.update(avalon)

        # adding ui inputs if any
        self.pre_create_data = pre_create_data or {}

        # adding media pool folder if any
        self.media_pool_folder = media_pool_folder

        # populate default data before we get other attributes
        self._populate_timeline_item_default_data()

        # use all populated default data to create all important attributes
        self._populate_attributes()

        # create parents with correct types
        self._create_parents()

    def convert(self):
        # solve track item data and add them to tag data
        self._convert_to_tag_data()

        # if track name is in review track name and also if driving track name
        # is not in review track name: skip tag creation
        if (
            self.track_name in self.review_layer and
            self.driving_layer not in self.review_layer
        ):
            return

        # deal with clip name
        new_name = self.tag_data.pop("newClipName")

        if self.rename:
            self.tag_data["asset"] = new_name
        else:
            self.tag_data["asset"] = self.ti_name

        if not lib.pype_marker_workflow:
            # create compound clip workflow
            lib.create_compound_clip(
                self.timeline_item_data,
                self.tag_data["asset"],
                self.media_pool_folder
            )

            # add timeline_item_data selection to tag
            self.tag_data.update({
                "track_data": self.timeline_item_data["track"]
            })

        # create openpype tag on timeline_item and add data
        lib.imprint(self.timeline_item, self.tag_data)

        return self.timeline_item

    def _populate_timeline_item_default_data(self):
        """ Populate default formatting data from track item. """

        self.timeline_item_default_data = {
            "_folder_": "shots",
            "_sequence_": self.timeline_name,
            "_track_": self.track_name,
            "_clip_": self.ti_name,
            "_trackIndex_": self.track_index,
            "_clipIndex_": self.ti_index
        }

    def _populate_attributes(self):
        """ Populate main object attributes. """
        # track item frame range and parent track name for vertical sync check
        self.clip_in = int(self.timeline_item.GetStart())
        self.clip_out = int(self.timeline_item.GetEnd())

        # define ui inputs if non gui mode was used
        self.shot_num = self.ti_index
        print(
            "____ self.shot_num: {}".format(self.shot_num)
        )

        # publisher ui attribute inputs or default values if gui was not used
        def get(key):
            """Shorthand access for code readability"""
            return self.pre_create_data.get(key)

        self.rename = get("clipRename") or self.rename_default
        self.clip_name = get("clipName") or self.clip_name_default
        self.hierarchy = get("hierarchy") or self.hierarchy_default
        self.count_from = get("countFrom") or self.count_from_default
        self.count_steps = get("countSteps") or self.count_steps_default
        self.subset_name = get("subsetName") or self.subset_name_default
        self.subset_family = get("subsetFamily") or self.subset_family_default
        self.vertical_sync = get("vSyncOn") or self.vertical_sync_default
        self.driving_layer = get("vSyncTrack") or self.driving_layer_default
        self.review_track = get("reviewTrack") or self.review_track_default

        self.hierarchy_data = {
            key: get(key) or self.timeline_item_default_data[key]
            for key in ["folder", "episode", "sequence", "track", "shot"]
        }

        # build subset name from layer name
        if self.subset_name == "<track_name>":
            self.subset_name = self.track_name

        # create subset for publishing
        # TODO: Use creator `get_subset_name` to correctly define name
        self.subset = self.subset_family + self.subset_name.capitalize()

    def _replace_hash_to_expression(self, name, text):
        """ Replace hash with number in correct padding. """
        _spl = text.split("#")
        _len = (len(_spl) - 1)
        _repl = "{{{0}:0>{1}}}".format(name, _len)
        new_text = text.replace(("#" * _len), _repl)
        return new_text

    def _convert_to_tag_data(self):
        """ Convert internal data to tag data.

        Populating the tag data into internal variable self.tag_data
        """
        # define vertical sync attributes
        hero_track = True
        self.review_layer = ""
        if self.vertical_sync:
            # check if track name is not in driving layer
            if self.track_name not in self.driving_layer:
                # if it is not then define vertical sync as None
                hero_track = False

        # increasing steps by index of rename iteration
        self.count_steps *= self.rename_index

        hierarchy_formatting_data = dict()
        _data = self.timeline_item_default_data.copy()
        if self.pre_create_data:

            # adding tag metadata from ui
            for _key, _value in self.pre_create_data.items():
                if _key in self.tag_keys:
                    self.tag_data[_key] = _value

            # driving layer is set as positive match
            if hero_track or self.vertical_sync:
                # mark review layer
                if self.review_track and (
                        self.review_track not in self.review_track_default):
                    # if review layer is defined and not the same as default
                    self.review_layer = self.review_track
                # shot num calculate
                if self.rename_index == 0:
                    self.shot_num = self.count_from
                else:
                    self.shot_num = self.count_from + self.count_steps

            # clip name sequence number
            _data.update({"shot": self.shot_num})

            # solve # in test to pythonic expression
            for _key, _value in self.hierarchy_data.items():
                if "#" not in _value:
                    continue
                self.hierarchy_data[_key] = self._replace_hash_to_expression(
                    _key, _value
                )

            # fill up pythonic expresisons in hierarchy data
            for _key, _value in self.hierarchy_data.items():
                hierarchy_formatting_data[_key] = _value.format(**_data)
        else:
            # if no gui mode then just pass default data
            hierarchy_formatting_data = self.hierarchy_data

        tag_hierarchy_data = self._solve_tag_hierarchy_data(
            hierarchy_formatting_data
        )

        tag_hierarchy_data.update({"heroTrack": True})
        if hero_track and self.vertical_sync:
            self.vertical_clip_match.update({
                (self.clip_in, self.clip_out): tag_hierarchy_data
            })

        if not hero_track and self.vertical_sync:
            # driving layer is set as negative match
            for (_in, _out), hero_data in self.vertical_clip_match.items():
                hero_data.update({"heroTrack": False})
                if _in == self.clip_in and _out == self.clip_out:
                    data_subset = hero_data["subset"]
                    # add track index in case duplicity of names in hero data
                    if self.subset in data_subset:
                        hero_data["subset"] = self.subset + str(
                            self.track_index)
                    # in case track name and subset name is the same then add
                    if self.subset_name == self.track_name:
                        hero_data["subset"] = self.subset
                    # assign data to return hierarchy data to tag
                    tag_hierarchy_data = hero_data

        # add data to return data dict
        self.tag_data.update(tag_hierarchy_data)

        # add uuid to tag data
        self.tag_data["uuid"] = str(uuid.uuid4())

        # add review track only to hero track
        if hero_track and self.review_layer:
            self.tag_data.update({"reviewTrack": self.review_layer})
        else:
            self.tag_data.update({"reviewTrack": None})

    def _solve_tag_hierarchy_data(self, hierarchy_formatting_data):
        """ Solve tag data from hierarchy data and templates. """
        # fill up clip name and hierarchy keys
        hierarchy_filled = self.hierarchy.format(**hierarchy_formatting_data)
        clip_name_filled = self.clip_name.format(**hierarchy_formatting_data)

        return {
            "newClipName": clip_name_filled,
            "hierarchy": hierarchy_filled,
            "parents": self.parents,
            "hierarchyData": hierarchy_formatting_data,
            "subset": self.subset,
            "family": self.subset_family,
            "families": ["clip"]
        }

    def _convert_to_entity(self, key):
        """ Converting input key to key with type. """
        # convert to entity type
        entity_type = self.types.get(key, None)

        assert entity_type, "Missing entity type for `{}`".format(
            key
        )

        return {
            "entity_type": entity_type,
            "entity_name": self.hierarchy_data[key].format(
                **self.timeline_item_default_data
            )
        }

    def _create_parents(self):
        """ Create parents and return it in list. """
        self.parents = []

        pattern = re.compile(self.parents_search_pattern)
        par_split = [pattern.findall(t).pop()
                     for t in self.hierarchy.split("/")]

        for key in par_split:
            parent = self._convert_to_entity(key)
            self.parents.append(parent)
