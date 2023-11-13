import re
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from openpype.hosts.resolve.api import plugin
from openpype.hosts.resolve.api import ProjectManager

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


class CreateBestLengthTimeline(plugin.Creator):
    """Create Timeline from all Items in Timelines"""

    #! wait this gets instantiated everytime again

    label = "Create Best Length Timeline"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    # gui_tracks = get_video_track_names()
    gui_name = "BestLnegth Plate Creator"
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
            ui_settings = self.process_widget_result(widget.result)
            self.create_bestlength_timeline(ui_settings)
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
        r.update(
            {
                "regex_timeline_include": re.compile(r["le_timeline_regex"]["value"]),
                "exclude_videotracks": [
                    vt.strip()
                    for vt in r["le_exclude_tracknames"]["value"].split(",")
                    if vt != ""
                ],
            }
        )
        return r

    def create_bestlength_timeline(self, settings):
        log.info(f"I'm doing the merge")
        pm = ProjectManager()
        cp = pm.current_project
        # cp.log_info(log)

        # filter timelines on regex
        filtered_timelines = [
            tl
            for tl in cp.timelines
            if settings["regex_timeline_include"].search(tl.name)
        ]

        # rondtrip otio to get timewarp info
        for tl in filtered_timelines:
            tl.export_otio()
            tl.import_bestlength_otio()
            # log.debug(f"{dir(tl.otio) = }")
            # for i in tl.otio.each_child():
            #     log.debug(f"{i = }")

        filtered_videotracks = [
            t
            for tl in filtered_timelines
            for t in tl.jotio["tracks"]["children"]
            if t["kind"] == "Video" and t["name"] not in settings["exclude_videotracks"]
        ]
        log.info(f"{filtered_timelines = }")
        log.info(f"{filtered_videotracks = }")


# class TC:
#     """Frames to SMPTE timecode converter and reverse."""

#     # ! everything in here should be classmethods,vars since we don't need to instantiate an object ever

#     __fps = 24.0
#     __is_dropframe = False

#     @classmethod
#     def get_fps(cls) -> float:
#         return cls.__fps

#     @classmethod
#     def set_fps(cls, para: float):
#         if not isinstance(para, (float, int)):
#             raise RuntimeError(f"{para} must be of type bool. {type(para)} != float")
#         cls.__fps = float(para)
#         log.info(f"Set internal FPS to {cls.__fps}")

#     @classmethod
#     def get_is_dropframe(cls) -> bool:
#         return cls.__is_dropframe

#     @classmethod
#     def set_is_dropframe(cls, para):
#         if not isinstance(para, bool):
#             raise RuntimeError(f"{para} must be of type bool. {type(para)} != bool")
#         cls.__is_dropframe = para

#     @classmethod
#     def get_frames(cls, tc: str) -> int:
#         """Converts SMPTE timecode to frame count."""

#         if not tc or tc == "":
#             return None

#         if int(tc[9:]) > cls.__fps:
#             raise ValueError("SMPTE timecode to frame rate mismatch.", tc, cls.__fps)

#         hours = int(tc[:2])
#         minutes = int(tc[3:5])
#         seconds = int(tc[6:8])
#         frames = int(tc[9:])

#         totalMinutes = int(60 * hours + minutes)

#         # Drop frame calculation using the Duncan/Heidelberger method.
#         if cls.__is_dropframe:
#             dropFrames = int(round(cls.__fps * 0.066666))
#             timeBase = int(round(cls.__fps))
#             hourFrames = int(timeBase * 60 * 60)
#             minuteFrames = int(timeBase * 60)
#             frm = int(
#                 (
#                     (hourFrames * hours)
#                     + (minuteFrames * minutes)
#                     + (timeBase * seconds)
#                     + frames
#                 )
#                 - (dropFrames * (totalMinutes - (totalMinutes // 10)))
#             )
#         # Non drop frame calculation.
#         else:
#             __fps = int(round(cls.__fps))
#             frm = int((totalMinutes * 60 + seconds) * __fps + frames)

#         return frm

#     @classmethod
#     def get_tc(cls, frames: int) -> str:
#         """Converts frame count to SMPTE timecode."""

#         frames = abs(frames)

#         # Drop frame calculation using the Duncan/Heidelberger method.
#         if cls.__is_dropframe:
#             spacer = ":"
#             spacer2 = ";"

#             dropFrames = int(round(cls.__fps * 0.066666))
#             framesPerHour = int(round(cls.__fps * 3600))
#             framesPer24Hours = framesPerHour * 24
#             framesPer10Minutes = int(round(cls.__fps * 600))
#             framesPerMinute = int(round(cls.__fps) * 60 - dropFrames)

#             frames = frames % framesPer24Hours

#             d = frames // framesPer10Minutes
#             m = frames % framesPer10Minutes

#             if m > dropFrames:
#                 frames = (
#                     frames
#                     + (dropFrames * 9 * d)
#                     + dropFrames * ((m - dropFrames) // framesPerMinute)
#                 )
#             else:
#                 frames = frames + dropFrames * 9 * d

#             frRound = int(round(cls.__fps))
#             hr = int(frames // frRound // 60 // 60)
#             mn = int((frames // frRound // 60) % 60)
#             sc = int((frames // frRound) % 60)
#             fr = int(frames % frRound)

#         # Non drop frame calculation.
#         else:
#             __fps = int(round(cls.__fps))
#             spacer = ":"
#             spacer2 = spacer

#             frHour = __fps * 3600
#             frMin = __fps * 60

#             hr = int(frames // frHour)
#             mn = int((frames - hr * frHour) // frMin)
#             sc = int((frames - hr * frHour - mn * frMin) // __fps)
#             fr = int(round(frames - hr * frHour - mn * frMin - sc * __fps))

#         # Return SMPTE timecode string.
#         return (
#             str(hr).zfill(2)
#             + spacer
#             + str(mn).zfill(2)
#             + spacer
#             + str(sc).zfill(2)
#             + spacer2
#             + str(fr).zfill(2)
#         )


# class DVR_ProjectManager:
#     def __init__(self) -> None:
#         self.__manager = bmd.scriptapp("Resolve").GetProjectManager()
#         self.__current_project = self.manager.GetCurrentProject()
#         self.__mediapool = self.current_project.GetMediaPool()

#     @property
#     def manager(self):
#         return self.__manager

#     @property
#     def current_project(self):
#         return self.__current_project

#     @property
#     def current_project_name(self):
#         return self.__current_project.GetName()

#     @property
#     def mediapool(self):
#         return self.__mediapool

#     @property
#     def all_timelines(self):
#         # ! resolve saves Timelines with 1-based indices
#         result = []
#         for i in range(1, self.current_project.GetTimelineCount() + 1):
#             dvrtl = self.current_project.GetTimelineByIndex(i)
#             result.append(DVR_Timeline(dvrtl))

#         return result


# class DVR_SourceClip:
#     def __init__(self, dvr_obj) -> None:
#         self.__dvr_obj = dvr_obj

#     def __str__(self) -> str:
#         return self.name

#     def __repr__(self) -> str:
#         return f"{self.name}@{self.id}"

#     @property
#     def id(self) -> str:
#         return self.__dvr_obj.GetUniqueId()

#     @property
#     def name(self):
#         return self.__dvr_obj.GetName()

#     @property
#     def properties(self):
#         result = self.__dvr_obj.GetMetadata()
#         result.update(self.__dvr_obj.GetClipProperty())
#         return dict(sorted(result.items()))

#     @property
#     def pls_work(self):
#         return self.__dvr_obj


# class DVR_Clip:
#     def __init__(self, dvr_obj) -> None:
#         self.__dvr_obj = dvr_obj
#         self.__used_timeline: DVR_Timeline

#     def __str__(self) -> str:
#         return self.name

#     def __repr__(self) -> str:
#         return f"{self.name}@{self.src_in}"

#     @property
#     def id(self):
#         return self.__dvr_obj.GetUniqueId()

#     @property
#     def name(self):
#         return self.__dvr_obj.GetName()

#     @property
#     def source(self):
#         return DVR_SourceClip(self.__dvr_obj.GetMediaPoolItem())

#     @property
#     def used_in_timeline(self):
#         return self.__used_timeline

#     @used_in_timeline.setter
#     def used_in_timeline(self, val):
#         self.__used_timeline = val

#     @property
#     def edit_in(self) -> int:
#         return self.__dvr_obj.GetStart()

#     @property
#     def edit_out(self) -> int:
#         return self.__dvr_obj.GetEnd()

#     @property
#     def head_in(self) -> int:
#         TC.set_fps(float(self.source.properties.get("FPS")))
#         return TC.get_frames(str(self.source.properties.get("Start TC")))

#     @property
#     def tail_out(self) -> int:
#         TC.set_fps(float(self.source.properties.get("FPS")))
#         return TC.get_frames(str(self.source.properties.get("End TC")))

#     @property
#     def left_offset(self) -> int:
#         return int(self.__dvr_obj.GetLeftOffset())

#     @property
#     def right_offset(self) -> int:
#         return int(self.__dvr_obj.GetRightOffset())

#     @property
#     def src_in(self) -> int:
#         return self.head_in + self.left_offset

#     @property
#     def src_out(self) -> int:
#         # ? why doesn't this here work: self.tail_out - self.right_offset
#         return self.src_in + self.duration

#     @property
#     def duration(self):
#         # TODO: support timeremaps
#         return self.__dvr_obj.GetDuration()

#     @property
#     def color(self):
#         return self.__dvr_obj.GetClipColor()

#     @property
#     def properties(self):
#         return dict(self.__dvr_obj.GetProperty())


# class DVR_Timeline:
#     __track_filter: list[str]

#     def __init__(self, dvr_obj) -> None:
#         self.__dvr_obj = dvr_obj

#     def __str__(self) -> str:
#         return self.name

#     @property
#     def start_frame(self) -> int:
#         return int(self.__dvr_obj.GetStartFrame())

#     @property
#     def end_frame(self) -> int:
#         return int(self.__dvr_obj.GetEndFrame())

#     @property
#     def name(self):
#         return str(self.__dvr_obj.GetName())

#     @property
#     def properties(self) -> dict:
#         return self.__dvr_obj.GetSetting()

#     @property
#     def framerate(self) -> float:
#         return float(self.__dvr_obj.GetSetting("timelineFrameRate"))

#     @classmethod
#     def set_track_filter(cls, para):
#         cls.__track_filter = para

#     @property
#     def is_drop_frame(self):
#         result = self.__dvr_obj.GetSetting("timelineDropFrameTimecode")
#         return bool(result)

#     @property
#     def video_tracks(self) -> list[str]:
#         result = []
#         for i in range(0, self.__dvr_obj.GetTrackCount("video")):
#             result.append(self.__dvr_obj.GetTrackName("video", i + 1))
#         return result

#     @property
#     def markers(self):
#         return self.__dvr_obj.GetMarkers()

#     @property
#     def clips(self) -> list[DVR_Clip]:
#         result = []
#         log.debug(f"{self.video_tracks = }")
#         for i in range(len(self.video_tracks)):
#             if self.video_tracks[i] in self.__track_filter:
#                 continue
#             for c in self.__dvr_obj.GetItemListInTrack("video", i + 1):
#                 clip = DVR_Clip(c)
#                 clip.used_in_timeline = self
#                 result.append(clip)
#         return result


# class Merger:
#     def __init__(self, fu) -> None:
#         self.fu = fu
#         self.__mode: str
#         self.__gapsize: int
#         self.__timeline_in: str
#         self.__timeline_out: str
#         self.__color_to_skip: str
#         self.__timeline_filter: re.Pattern

#     @property
#     def timeline_in(self):
#         return self.__timeline_in

#     @timeline_in.setter
#     def timeline_in(self, var):
#         self.__timeline_in = var

#     @property
#     def timeline_out(self):
#         return self.__timeline_out

#     @timeline_out.setter
#     def timeline_out(self, var):
#         self.__timeline_out = var

#     @property
#     def timeline_filter(self) -> re.Pattern:
#         return self.__timeline_filter

#     @timeline_filter.setter
#     def timeline_filter(self, para):
#         res = re.compile(para)
#         log.debug(f"{res = }")
#         self.__timeline_filter = res

#     @property
#     def mode(self):
#         return self.__mode

#     @mode.setter
#     def mode(self, var):
#         self.__mode = var

#     @property
#     def gapsize(self):
#         return self.__gapsize

#     @gapsize.setter
#     def gapsize(self, var):
#         self.__gapsize = var

#     @property
#     def color_to_skip(self):
#         return self.__color_to_skip

#     @color_to_skip.setter
#     def color_to_skip(self, var):
#         self.__color_to_skip = var

#     # ! i don't need sets here, can we just do it with lists?
#     def find_best_ranges(self, sets):
#         # thanks chatGPT
#         sets.sort(key=lambda s: min(s))

#         best_ranges = []
#         current_range = sets[0].copy()

#         for s in sets[1:]:
#             # compare current in with last out, aka. soft gap between 2 ranges
#             if min(s) - max(current_range) <= self.gapsize:
#                 # clip is in gapsize or inside previous clip...
#                 current_range.update(s)
#             else:
#                 # hard gap right here. add current range to best_ranges and update current
#                 best_ranges.append(list(current_range))
#                 current_range = s.copy()

#         best_ranges.append(list(current_range))

#         # Find the best combination of ranges
#         def total_length(ranges):
#             return sum(len(r) for r in ranges)

#         best_combination = []
#         best_length = 0

#         for i in range(len(best_ranges)):
#             for j in range(i, len(best_ranges)):
#                 combined_ranges = best_ranges[i : j + 1]
#                 combined_length = total_length(combined_ranges)

#                 if combined_length > best_length:
#                     best_combination = combined_ranges
#                     best_length = combined_length

#         return best_combination

#     def get_occurences(self, timelines):
#         occs = {}  # occurrences per mediapoolitem
#         for tl in timelines:
#             TC.set_fps(tl.framerate)
#             log.debug("------------------------------------------------")
#             log.debug(f"analyzing timeline: {tl.name}")
#             log.debug(f"{tl.properties}")
#             for tl_clip in tl.clips:
#                 log.debug(f"{tl_clip.properties = }")
#                 log.debug(f"{tl_clip.color} -- {self.color_to_skip}")
#                 if not tl_clip.color == self.color_to_skip:
#                     src_clip = tl_clip.source
#                     # never seen this MPI before... add it
#                     if not src_clip.id in occs.keys():
#                         occs.update(
#                             {
#                                 src_clip.id: {
#                                     "source": src_clip,
#                                     "usages": {
#                                         tl_clip.id: {
#                                             "clip": tl_clip,
#                                             "usage": (tl_clip.src_in, tl_clip.src_out),
#                                         }
#                                     },
#                                 }
#                             }
#                         )
#                     else:
#                         occs[src_clip.id]["usages"].update(
#                             {
#                                 tl_clip.id: {
#                                     "clip": tl_clip,
#                                     "usage": (tl_clip.src_in, tl_clip.src_out),
#                                 }
#                             }
#                         )

#         return occs

#     def merge(self):
#         pmanager = DVR_ProjectManager()

#         # query all timelines that match the given filters
#         # TODO: implement regex exclude
#         all_timelines = [
#             tl for tl in pmanager.all_timelines if self.timeline_filter.search(tl.name)
#         ]

#         log.info("================================================")
#         occs = self.get_occurences(all_timelines)

#         # sort occurrences and remove duplicates
#         clip_map = {}
#         for src_id, src_v in occs.items():
#             clip_set = set([u["usage"] for u in src_v["usages"].values()])
#             clip_map[src_id] = sorted(clip_set, key=lambda k: k[0])
#             log.debug(f"{occs[src_id]['source'].properties = }")
#         log.info(f"{occs = }")
#         log.info(f"{clip_map = }")

#         # framelists = {k: set(range(v[0], v[1] + 1)) for k, v in clip_map.items()}
#         framelists = {}
#         for k, v in clip_map.items():
#             framelists[k] = [set(range(i[0], i[1])) for i in v]
#             log.debug(type(framelists[k]))
#             for i in framelists[k]:
#                 log.debug(type(i))
#         log.info(f"{framelists = }")

#         blis = {}
#         for k, v in framelists.items():
#             foo = self.find_best_ranges(v)
#             for f in foo:
#                 log.debug(f"{f = }")
#                 log.debug(f"{len(f) = }")
#             blis[k] = self.find_best_ranges(v)
#             log.debug(f"{len(blis[k]) = }")
#         log.info(f"{blis = }")

#         result = []
#         for k, v in blis.items():
#             tc_head_in = occs[k]["source"].pls_work.GetClipProperty("Start TC")
#             f_head_in = TC.get_frames(tc_head_in)
#             for i in v:
#                 log.debug(TC.get_tc(min(i)))
#                 log.debug(TC.get_tc(max(i)))
#                 log.debug(f"{tc_head_in = }")
#                 log.debug(f"{f_head_in = }")
#                 start = min(i)
#                 log.debug(f"{start = }")
#                 end = max(i)
#                 # ! resolve frame in MediapoolItems
#                 #   it's actually using relative frames. e.g. start of source 12:42:13:12 -> f0
#                 result.append(
#                     {
#                         "mediaPoolItem": occs[k]["source"].pls_work,
#                         "startFrame": start - f_head_in,
#                         "endFrame": end - f_head_in,
#                         "mediaType": 1,
#                         "trackIndex": 1,
#                     }
#                 )
#         log.info(f"{result = }")

#         # create timeline
#         pmanager.mediapool.CreateEmptyTimeline(self.timeline_out)
#         pmanager.mediapool.AppendToTimeline(result)

#         return


# class UI:
#     def __init__(self, fu) -> None:
#         self.fu = fu
#         self.merger = Merger(fu)
#         self.ui_manager = self.fu.UIManager
#         self.ui_dispatcher = bmd.UIDispatcher(self.ui_manager)

#         # self.load_config()
#         self.create_ui()
#         self.init_ui_defaults()
#         self.init_ui_callbacks()

#     def create_ui(self):
#         self.selection_group = self.ui_manager.HGroup(
#             {"Spacing": 5, "Weight": 0},
#             [
#                 self.ui_manager.VGroup(
#                     {"Spacing": 5, "Weight": 1},
#                     [
#                         self.ui_manager.Label(
#                             {
#                                 "StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"
#                             }
#                         ),
#                         self.ui_manager.HGroup(
#                             {"Spacing": 5, "Weight": 0},
#                             [
#                                 self.ui_manager.Label(
#                                     {
#                                         "Text": "Include Timelines matching regex:",
#                                         "Alignment": {"AlignLeft": True},
#                                         "Weight": 0.1,
#                                     }
#                                 ),
#                                 self.ui_manager.LineEdit(
#                                     {
#                                         "ID": "include_only",
#                                         "Text": "^.+$",
#                                         "Weight": 0.5,
#                                     }
#                                 ),
#                             ],
#                         ),
#                         self.ui_manager.HGroup(
#                             {"Spacing": 5, "Weight": 0},
#                             [
#                                 self.ui_manager.Label(
#                                     {
#                                         "Text": "Merged Timeline Name:",
#                                         "Alignment": {"AlignLeft": True},
#                                         "Weight": 0.1,
#                                     }
#                                 ),
#                                 self.ui_manager.LineEdit(
#                                     {
#                                         "ID": "merged_tl_name",
#                                         "Text": "merged",
#                                         "Weight": 0.5,
#                                     }
#                                 ),
#                             ],
#                         ),
#                         self.ui_manager.HGroup(
#                             {"Spacing": 5, "Weight": 0},
#                             [
#                                 self.ui_manager.CheckBox(
#                                     {
#                                         "ID": "shall_exclude_tracks",
#                                         "Text": "Exclude Track Names:",
#                                         "Checked": False,
#                                         "AutoExclusive": True,
#                                         "Checkable": True,
#                                         "Events": {"Toggled": True},
#                                     }
#                                 ),
#                                 self.ui_manager.LineEdit(
#                                     {
#                                         "ID": "exclude_tracks",
#                                         "Text": "reference,",
#                                         "Weight": 0.8,
#                                     }
#                                 ),
#                             ],
#                         ),
#                         self.ui_manager.HGroup(
#                             {"Spacing": 5, "Weight": 0},
#                             [
#                                 self.ui_manager.CheckBox(
#                                     {
#                                         "ID": "skip_clip_color",
#                                         "Text": "Skip Clip Color:",
#                                         "Checked": False,
#                                         "AutoExclusive": True,
#                                         "Checkable": True,
#                                         "Events": {"Toggled": True},
#                                     }
#                                 ),
#                                 self.ui_manager.ComboBox(
#                                     {
#                                         "ID": "clip_colors",
#                                         "Weight": 0.8,
#                                     }
#                                 ),
#                             ],
#                         ),
#                         self.ui_manager.Label(
#                             {
#                                 "StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"
#                             }
#                         ),
#                         self.ui_manager.HGroup(
#                             {"Spacing": 5, "Weight": 0},
#                             [
#                                 self.ui_manager.Label(
#                                     {"Text": "Merge Gap:", "Weight": 0}
#                                 ),
#                                 self.ui_manager.SpinBox(
#                                     {
#                                         "ID": "merge_gap",
#                                         "Value": 10,
#                                         "Minimum": 0,
#                                         "Maximum": 100000,
#                                         "SingleStep": 1,
#                                     }
#                                 ),
#                             ],
#                         ),
#                         self.ui_manager.HGroup(
#                             {"Spacing": 5, "Weight": 0},
#                             [
#                                 self.ui_manager.Label(
#                                     {
#                                         "Text": "Merge By:",
#                                         "Alignment": {"AlignLeft": True},
#                                         "Weight": 0.1,
#                                     }
#                                 ),
#                                 self.ui_manager.ComboBox(
#                                     {
#                                         "ID": "merge_key",
#                                         "Alignment": {"AlignLeft": True},
#                                         "Weight": 0.5,
#                                     }
#                                 ),
#                             ],
#                         ),
#                         self.ui_manager.Label(
#                             {
#                                 "StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"
#                             }
#                         ),
#                     ],
#                 )
#             ],
#         )
#         self.window_01 = self.ui_manager.VGroup(
#             [
#                 self.ui_manager.HGroup(
#                     {"Spacing": 1},
#                     [
#                         self.ui_manager.VGroup(
#                             {"Spacing": 15, "Weight": 3},
#                             [
#                                 self.selection_group,
#                                 self.ui_manager.Button(
#                                     {
#                                         "ID": "merge_button",
#                                         "Text": "Merge",
#                                         "Weight": 0,
#                                         "Enabled": True,
#                                     }
#                                 ),
#                                 self.ui_manager.Label(
#                                     {
#                                         "ID": "status",
#                                         "Text": "",
#                                         "Alignment": {"AlignCenter": True},
#                                     }
#                                 ),
#                                 self.ui_manager.Label(
#                                     {"StyleSheet": "max-height: 5px;"}
#                                 ),
#                             ],
#                         ),
#                     ],
#                 )
#             ]
#         )
#         self.main_window = self.ui_dispatcher.AddWindow(
#             {
#                 "WindowTitle": "Merge Timelines",
#                 "ID": "ui.main",
#                 "Geometry": [
#                     800,
#                     500,  # position when starting
#                     450,
#                     275,  # width, height
#                 ],
#             },
#             self.window_01,
#         )

#     def init_ui_defaults(self):
#         items = self.main_window.GetItems()
#         items["clip_colors"].AddItems(clipcolor_names)
#         items["merge_key"].AddItems(["Source File"])

#     def init_ui_callbacks(self):
#         self.main_window.On["ui.main"].Close = self.destroy
#         self.main_window.On["merge_button"].Clicked = self.merge
#         self.main_window.On["include_only"].TextChanged = self.update

#     @property
#     # ? should we really call the filter include_only
#     # ? should we combine timeline and color filter into 1 object
#     def filter(self) -> str:
#         return str(self.main_window.Find("include_only").Text)

#     @property
#     def color_to_skip(self) -> str:
#         return str(self.main_window.Find("clip_colors").CurrentText)

#     @property
#     def shall_skip_color(self) -> bool:
#         return bool(self.main_window.Find("skip_clip_color").Checked)

#     @property
#     def tracks_to_skip(self) -> list[str]:
#         res = str(self.main_window.Find("exclude_tracks").Text)
#         log.debug(f"{res = }")
#         if not "," in res:
#             return [res]
#         else:
#             return [i.strip() for i in res.split(",")]

#     @property
#     def shall_skip_tracks(self) -> bool:
#         return bool(self.main_window.Find("shall_exclude_tracks").Checked)

#     @property
#     #! might require getter
#     def timeline_out(self) -> str:
#         return str(self.main_window.Find("merged_tl_name").Text)

#     @property
#     def merge_gap(self) -> int:
#         return int(self.main_window.Find("merge_gap").Value)

#     @property
#     def merge_mode(self) -> str:
#         return str(self.main_window.Find("merge_key").CurrentText)

#     def start(self):
#         self.main_window.Show()
#         self.ui_dispatcher.RunLoop()
#         self.main_window.Hide()

#     def destroy(self, event=None):
#         self.ui_dispatcher.ExitLoop()
#         if event:
#             log.debug(event)

#     def merge(self, event=None):
#         if event:
#             log.debug(event)
#         log.debug(f"{self.merge_gap = }")
#         try:
#             # prepare timeline merger
#             log.debug(self.tracks_to_skip)
#             DVR_Timeline.set_track_filter(self.tracks_to_skip)
#             self.merger.timeline_out = self.timeline_out
#             self.merger.timeline_filter = self.filter
#             self.merger.color_to_skip = (
#                 self.color_to_skip if self.shall_skip_color else ""
#             )
#             self.merger.tracks_to_skip = (
#                 self.tracks_to_skip if self.shall_skip_tracks else []
#             )
#             self.merger.mode = self.merge_mode
#             self.merger.gapsize = self.merge_gap

#             # do the merge
#             self.merger.merge()
#         except Exception as err:
#             log.exception(err, stack_info=True)

#     def update(self, event=None):
#         # TODO: well...
#         if event:
#             log.debug(event)
