import re
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import openpype.hosts.resolve.api as api

clipcolor_names = [
    "Orange",
    "Apricot",
    "Yellow",
    "Lime",
    "Olive",
    "Green",
    "Teal",
    "Navy",
    "Blue",
    "Purple",
    "Violet",
    "Pink",
    "Tan",
    "Beige",
    "Brown",
    "Chocolate",
]


def get_logger() -> logging.Logger:
    log = logging.getLogger(__name__)
    formatter = logging.Formatter(
        "[%(filename)s:%(lineno)d] %(asctime)s %(levelname)-8s %(message)s"
    )

    #
    errhandler = logging.StreamHandler(sys.stderr)
    errhandler.setLevel(logging.ERROR)
    errhandler.setFormatter(formatter)
    log.addHandler(errhandler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    log_path = Path.home() / "logs" / "dvr.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)
    log_handler_paras = {"mode": "a", "maxBytes": 4 * 1024**3, "backupCount": 2}
    filehandler = RotatingFileHandler(log_path, **log_handler_paras)
    filehandler.setLevel(logging.DEBUG)
    filehandler.setFormatter(formatter)
    log.addHandler(filehandler)

    log.setLevel(logging.DEBUG)
    log.debug(f"{log_handler_paras['maxBytes'] = }")
    return log


log = get_logger()


class CreateBestLengthTimeline(api.plugin.Creator):
    """Create Timeline from all Items in Timelines"""

    #! wait this gets instantiated everytime again

    label = "Create Best Length Timeline"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    # gui_tracks = get_video_track_names()
    gui_name = "BestLength Plate Creator"
    gui_info = "Analyzes all Timelines for BestLength Items"

    gui_inputs = {
        "main_section": {
            "type": "section",
            "label": "General Settings",
            "target": "ui",
            "order": 0,
            "value": {
                "le_timeline_out_name": {
                    "value": "wip_bestlength_plates",
                    "type": "QLineEdit",
                    "label": "Timeline Name",
                    "target": "tag",
                    "toolTip": "Name of the timeline to be created",  # noqa
                    "order": 0,
                },
            },
        },
        "filter_section": {
            "type": "section",
            "label": "Filter Settings",
            "target": "ui",
            "order": 1,
            "value": {
                "le_timeline_regex": {
                    "value": r"^.+$",
                    "type": "QLineEdit",
                    "label": "Timeline Include Regex",
                    "target": "tag",
                    "toolTip": "Regex to be used as include filter for timelines",  # noqa
                    "order": 0,
                },
                "le_exclude_tracknames": {
                    "value": "",
                    "type": "QLineEdit",
                    "label": "Exclude Track Names",
                    "target": "tag",
                    "toolTip": "comma-separated list of track names to be excluded",  # noqa
                    "order": 1,
                },
                "cb_exclude_clipcolor": {
                    "value": clipcolor_names,
                    "type": "QComboBox",
                    "label": "Timeline Name",
                    "target": "tag",
                    "toolTip": "Clip Color to be excluded",  # noqa
                    "order": 2,
                },
            },
        },
        "merge_section": {
            "type": "section",
            "label": "Merge Settings",
            "target": "ui",
            "order": 2,
            "value": {
                "sb_gapsize": {
                    "value": 10,
                    "type": "QSpinBox",
                    "label": "Gap Size",
                    "target": "tag",
                    "toolTip": "Name of the timeline to be created",  # noqa
                    "order": 0,
                },
                "cb_mergemode": {
                    "value": ["MediaPoolItem"],
                    "type": "QComboBox",
                    "label": "Merge Mode",
                    "target": "tag",
                    "toolTip": "Name of the timeline to be created",  # noqa
                    "order": 1,
                },
            },
        },
    }

    presets = None

    def process(self):
        widget = self.run_widget()

        if not widget.result:
            log.info("cancelled...")
            return

        try:
            self.process_widget_result(widget.result)
            self.create_bestlength_timeline(self.ui_settings)
        except Exception as err:
            log.exception(err, stack_info=True)

    def run_widget(self):
        # get key pares from presets and match it on ui inputs
        for k, v in self.gui_inputs.items():
            if v["type"] in ("dict", "section"):
                # nested dictionary (only one level allowed
                # for sections and dict)
                for _k, _v in v["value"].items():
                    if self.presets.get(_k) is not None:
                        self.gui_inputs[k]["value"][_k]["value"] = self.presets[_k]
            if self.presets.get(k):
                self.gui_inputs[k]["value"] = self.presets[k]

        # open widget for plugins inputs
        widget = self.widget(self.gui_name, self.gui_info, self.gui_inputs)
        widget.exec_()
        log.info(f"{widget.result}")
        return widget

    def process_widget_result(self, r: dict):
        self.ui_settings = r.copy()
        self.ui_settings.update(
            {
                "regex_timeline_include": re.compile(r["le_timeline_regex"]["value"]),
                "exclude_videotracks": [
                    vt.strip()
                    for vt in r["le_exclude_tracknames"]["value"].split(",")
                    if vt != ""
                ],
            }
        )

    def create_bestlength_timeline(self, settings):
        log.info(f"I'm doing the merge")
        pm = api.ProjectManager()
        cp = pm.current_project
        # cp.log_info(log)

        # filter timelines on regex
        filtered_timelines: list(api.Timeline) = [
            tl
            for tl in cp.timelines
            if settings["regex_timeline_include"].search(tl.name)
        ]
        log.debug(f"{filtered_timelines = }")
        log.debug(f"{len(filtered_timelines) = }")

        # rondtrip otio to get timewarp info
        # also adds otio as json to VideoTrack
        for tl in filtered_timelines:
            tl.export_otio()
            tl.import_bestlength_otio()

        # filter videotracks on exclude_videotracks
        filtered_videotracks: list(api.VideoTrack) = [
            vt
            for tl in filtered_timelines
            for vt in tl.video_tracks
            if vt.name not in settings["exclude_videotracks"]
        ]
        log.debug(f"{filtered_videotracks = }")
        log.debug(f"{len(filtered_videotracks) = }")

        # get occurrences per MediapoolItem in all filtered Timelines/VideoTracks
        occs = self.get_occurrences(filtered_videotracks)
        log.debug(f"{occs = }")

        # sort occurrences and remove duplicates
        sorted_occs = self.sort_occurrences(occs)
        log.debug(f"{sorted_occs = }")

        # get bestlength clips
        blis = self.get_bestlength_clips(sorted_occs)

        clips_to_create = []
        for k, v in blis.items():
            for i in v["best_ranges"]:
                clips_to_create.append(
                    {
                        "mediaPoolItem": v["source"].root,
                        "startFrame": i[0] - v["source"].head_in,
                        "endFrame": i[1] - v["source"].head_in,
                        "mediaType": 1,
                        "trackIndex": 1,
                    }
                )

        # create bestlength timeline
        cp.mediapool.CreateEmptyTimeline("lel")
        cp.mediapool.AppendToTimeline(clips_to_create)

    def get_occurrences(self, video_tracks) -> dict[str : [api.TimelineItem]]:
        occs = {}
        for vt in video_tracks:
            for c in vt.clips:
                if c.color == self.ui_settings["cb_exclude_clipcolor"]["value"]:
                    continue
                if occs.get(c.source.id):
                    occs[c.source.id]["occs"].append(c)
                    continue
                occs.update({c.source.id: {"source": c.source, "occs": [c]}})
        return occs

    def sort_occurrences(self, occs):
        result = {}
        for src_id, v in occs.items():
            src_ranges = set()
            for ti in v["occs"]:
                _range = (min(ti.src_in, ti.src_out), max(ti.src_in, ti.src_out))
                src_ranges.add(_range)  # this autoremoves dupes
            result.update(
                {
                    src_id: {
                        "source": v["source"],
                        "occs": sorted(src_ranges, key=lambda k: k[0]),
                    }
                }
            )
        return result

    def get_bestlength_clips(self, sorted_occs):
        blis = {}
        for k, v in sorted_occs.items():
            blis[k] = {
                "source": v["source"],
                "best_ranges": self.find_best_ranges(v["occs"]),
            }
        log.info(f"best length clips = {blis}")
        return blis

    def find_best_ranges(self, ranges):
        log.info(f"{ranges = }")

        best_ranges = []
        current_range = ranges[0]
        for r in ranges[1:]:
            # compare current in with last out, aka. soft gap between 2 ranges
            if min(r) - max(current_range) <= int(
                self.ui_settings["sb_gapsize"]["value"]
            ):
                # clip is in gapsize or inside previous clip...
                current_range[1] = (
                    max(r) if max(r) > current_range[1] else max(current_range)
                )
            else:
                # hard gap right here. add current range to best_ranges and update current
                best_ranges.append(list(current_range))
                current_range = r
        best_ranges.append(list(current_range))

        # Find the best combination of ranges
        def total_length(ranges):
            return sum(len(r) for r in ranges)

        best_combination = []
        best_length = 0
        for i in range(len(best_ranges)):
            for j in range(i, len(best_ranges)):
                combined_ranges = best_ranges[i : j + 1]
                combined_length = total_length(combined_ranges)

                if combined_length > best_length:
                    best_combination = combined_ranges
                    best_length = combined_length

        return best_combination
