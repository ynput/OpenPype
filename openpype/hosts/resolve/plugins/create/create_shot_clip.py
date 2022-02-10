# from pprint import pformat
from openpype.hosts import resolve
from openpype.hosts.resolve.api import lib


class CreateShotClip(resolve.Creator):
    """Publishable clip"""

    label = "Create Publishable Clip"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    gui_tracks = resolve.get_video_track_names()
    gui_name = "OpenPype publish attributes creator"
    gui_info = "Define sequential rename and fill hierarchy data."
    gui_inputs = {
        "renameHierarchy": {
            "type": "section",
            "label": "Shot Hierarchy And Rename Settings",
            "target": "ui",
            "order": 0,
            "value": {
                "hierarchy": {
                    "value": "{folder}/{sequence}",
                    "type": "QLineEdit",
                    "label": "Shot Parent Hierarchy",
                    "target": "tag",
                    "toolTip": "Parents folder for shot root folder, Template filled with `Hierarchy Data` section",  # noqa
                    "order": 0},
                "clipRename": {
                    "value": False,
                    "type": "QCheckBox",
                    "label": "Rename clips",
                    "target": "ui",
                    "toolTip": "Renaming selected clips on fly",  # noqa
                    "order": 1},
                "clipName": {
                    "value": "{sequence}{shot}",
                    "type": "QLineEdit",
                    "label": "Clip Name Template",
                    "target": "ui",
                    "toolTip": "template for creating shot namespaused for renaming (use rename: on)",  # noqa
                    "order": 2},
                "countFrom": {
                    "value": 10,
                    "type": "QSpinBox",
                    "label": "Count sequence from",
                    "target": "ui",
                    "toolTip": "Set when the sequence number stafrom",  # noqa
                    "order": 3},
                "countSteps": {
                    "value": 10,
                    "type": "QSpinBox",
                    "label": "Stepping number",
                    "target": "ui",
                    "toolTip": "What number is adding every new step",  # noqa
                    "order": 4},
            }
        },
        "hierarchyData": {
            "type": "dict",
            "label": "Shot Template Keywords",
            "target": "tag",
            "order": 1,
            "value": {
                "folder": {
                    "value": "shots",
                    "type": "QLineEdit",
                    "label": "{folder}",
                    "target": "tag",
                    "toolTip": "Name of folder used for root of generated shots.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                    "order": 0},
                "episode": {
                    "value": "ep01",
                    "type": "QLineEdit",
                    "label": "{episode}",
                    "target": "tag",
                    "toolTip": "Name of episode.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                    "order": 1},
                "sequence": {
                    "value": "sq01",
                    "type": "QLineEdit",
                    "label": "{sequence}",
                    "target": "tag",
                    "toolTip": "Name of sequence of shots.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                    "order": 2},
                "track": {
                    "value": "{_track_}",
                    "type": "QLineEdit",
                    "label": "{track}",
                    "target": "tag",
                    "toolTip": "Name of sequence of shots.\nUsable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                    "order": 3},
                "shot": {
                    "value": "sh###",
                    "type": "QLineEdit",
                    "label": "{shot}",
                    "target": "tag",
                    "toolTip": "Name of shot. `#` is converted to paded number. \nAlso could be used with usable tokens:\n\t{_clip_}: name of used clip\n\t{_track_}: name of parent track layer\n\t{_sequence_}: name of parent sequence (timeline)",  # noqa
                    "order": 4}
            }
        },
        "verticalSync": {
            "type": "section",
            "label": "Vertical Synchronization Of Attributes",
            "target": "ui",
            "order": 2,
            "value": {
                "vSyncOn": {
                    "value": True,
                    "type": "QCheckBox",
                    "label": "Enable Vertical Sync",
                    "target": "ui",
                    "toolTip": "Switch on if you want clips above each other to share its attributes",  # noqa
                    "order": 0},
                "vSyncTrack": {
                    "value": gui_tracks,  # noqa
                   "type": "QComboBox",
                   "label": "Hero track",
                   "target": "ui",
                   "toolTip": "Select driving track name which should be mastering all others",  # noqa
                "order": 1}
                }
        },
        "publishSettings": {
            "type": "section",
            "label": "Publish Settings",
            "target": "ui",
            "order": 3,
            "value": {
                "subsetName": {
                    "value": ["<track_name>", "main", "bg", "fg", "bg",
                              "animatic"],
                    "type": "QComboBox",
                    "label": "Subset Name",
                    "target": "ui",
                    "toolTip": "chose subset name pattern, if <track_name> is selected, name of track layer will be used",  # noqa
                    "order": 0},
                "subsetFamily": {
                    "value": ["plate", "take"],
                    "type": "QComboBox",
                    "label": "Subset Family",
                    "target": "ui", "toolTip": "What use of this subset is for",  # noqa
                    "order": 1},
                "reviewTrack": {
                    "value": ["< none >"] + gui_tracks,
                    "type": "QComboBox",
                    "label": "Use Review Track",
                    "target": "ui",
                    "toolTip": "Generate preview videos on fly, if `< none >` is defined nothing will be generated.",  # noqa
                    "order": 2},
                "audio": {
                    "value": False,
                    "type": "QCheckBox",
                    "label": "Include audio",
                    "target": "tag",
                    "toolTip": "Process subsets with corresponding audio",  # noqa
                    "order": 3},
                "sourceResolution": {
                    "value": False,
                    "type": "QCheckBox",
                    "label": "Source resolution",
                    "target": "tag",
                    "toolTip": "Is resloution taken from timeline or source?",  # noqa
                    "order": 4},
            }
        },
        "shotAttr": {
            "type": "section",
            "label": "Shot Attributes",
            "target": "ui",
            "order": 4,
            "value": {
               "workfileFrameStart": {
                   "value": 1001,
                   "type": "QSpinBox",
                   "label": "Workfiles Start Frame",
                   "target": "tag",
                   "toolTip": "Set workfile starting frame number",  # noqa
                   "order": 0},
               "handleStart": {
                   "value": 0,
                   "type": "QSpinBox",
                   "label": "Handle start (head)",
                   "target": "tag",
                   "toolTip": "Handle at start of clip",  # noqa
                   "order": 1},
               "handleEnd": {
                   "value": 0,
                   "type": "QSpinBox",
                   "label": "Handle end (tail)",
                   "target": "tag",
                   "toolTip": "Handle at end of clip",  # noqa
                   "order": 2},
           }
        }
    }

    presets = None

    def process(self):
        # get key pares from presets and match it on ui inputs
        for k, v in self.gui_inputs.items():
            if v["type"] in ("dict", "section"):
                # nested dictionary (only one level allowed
                # for sections and dict)
                for _k, _v in v["value"].items():
                    if self.presets.get(_k) is not None:
                        self.gui_inputs[k][
                            "value"][_k]["value"] = self.presets[_k]
            if self.presets.get(k):
                self.gui_inputs[k]["value"] = self.presets[k]

        # open widget for plugins inputs
        widget = self.widget(self.gui_name, self.gui_info, self.gui_inputs)
        widget.exec_()

        if len(self.selected) < 1:
            return

        if not widget.result:
            print("Operation aborted")
            return

        self.rename_add = 0

        # get ui output for track name for vertical sync
        v_sync_track = widget.result["vSyncTrack"]["value"]

        # sort selected trackItems by
        sorted_selected_track_items = list()
        unsorted_selected_track_items = list()
        for track_item_data in self.selected:
            if track_item_data["track"]["name"] in v_sync_track:
                sorted_selected_track_items.append(track_item_data)
            else:
                unsorted_selected_track_items.append(track_item_data)

        sorted_selected_track_items.extend(unsorted_selected_track_items)

        # sequence attrs
        sq_frame_start = self.timeline.GetStartFrame()
        sq_markers = self.timeline.GetMarkers()

        # create media bin for compound clips (trackItems)
        mp_folder = resolve.create_bin(self.timeline.GetName())

        kwargs = {
            "ui_inputs": widget.result,
            "avalon": self.data,
            "mp_folder": mp_folder,
            "sq_frame_start": sq_frame_start,
            "sq_markers": sq_markers
        }

        for i, track_item_data in enumerate(sorted_selected_track_items):
            self.rename_index = i

            # convert track item to timeline media pool item
            track_item = resolve.PublishClip(
                self, track_item_data, **kwargs).convert()
            track_item.SetClipColor(lib.publish_clip_color)
