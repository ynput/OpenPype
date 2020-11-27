#!/usr/bin/env python
import os
import sys
import opentimelineio as otio
print(otio)
resolve = bmd.scriptapp("Resolve")
fu = resolve.Fusion()

ui = fu.UIManager
disp = bmd.UIDispatcher(fu.UIManager)

TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}

print(resolve)

def _create_rational_time(frame, fps):
    return otio.opentime.RationalTime(
        float(frame),
        float(fps)
    )


def _create_time_range(start, duration, fps):
    return otio.opentime.TimeRange(
        start_time=_create_rational_time(start, fps),
        duration=_create_rational_time(duration, fps)
    )


def _create_reference(mp_item):
    return otio.schema.ExternalReference(
        target_url=mp_item.GetClipProperty("File Path").get("File Path"),
        available_range=_create_time_range(
            mp_item.GetClipProperty("Start").get("Start"),
            mp_item.GetClipProperty("Frames").get("Frames"),
            mp_item.GetClipProperty("FPS").get("FPS")
        )
    )


def _create_markers(tl_item, frame_rate):
    tl_markers = tl_item.GetMarkers()
    markers = []
    for m_frame in tl_markers:
        markers.append(
            otio.schema.Marker(
                name=tl_markers[m_frame]["name"],
                marked_range=_create_time_range(
                    m_frame,
                    tl_markers[m_frame]["duration"],
                    frame_rate
                ),
                color=tl_markers[m_frame]["color"].upper(),
                metadata={"Resolve": {"note": tl_markers[m_frame]["note"]}}
            )
        )
    return markers


def _create_clip(tl_item):
    mp_item = tl_item.GetMediaPoolItem()
    frame_rate = mp_item.GetClipProperty("FPS").get("FPS")
    clip = otio.schema.Clip(
        name=tl_item.GetName(),
        source_range=_create_time_range(
            tl_item.GetLeftOffset(),
            tl_item.GetDuration(),
            frame_rate
        ),
        media_reference=_create_reference(mp_item)
    )
    for marker in _create_markers(tl_item, frame_rate):
        clip.markers.append(marker)
    return clip


def _create_gap(gap_start, clip_start, tl_start_frame, frame_rate):
    return otio.schema.Gap(
        source_range=_create_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            frame_rate
        )
    )


def _create_ot_timeline(output_path):
    if not output_path:
        return
    project_manager = resolve.GetProjectManager()
    current_project = project_manager.GetCurrentProject()
    dr_timeline = current_project.GetCurrentTimeline()
    ot_timeline = otio.schema.Timeline(name=dr_timeline.GetName())
    for track_type in list(TRACK_TYPES.keys()):
        track_count = dr_timeline.GetTrackCount(track_type)
        for track_index in range(1, int(track_count) + 1):
            ot_track = otio.schema.Track(
                name="{}{}".format(track_type[0].upper(), track_index),
                kind=TRACK_TYPES[track_type]
            )
            tl_items = dr_timeline.GetItemListInTrack(track_type, track_index)
            for tl_item in tl_items:
                if tl_item.GetMediaPoolItem() is None:
                    continue
                clip_start = tl_item.GetStart() - dr_timeline.GetStartFrame()
                if clip_start > ot_track.available_range().duration.value:
                    ot_track.append(
                        _create_gap(
                            ot_track.available_range().duration.value,
                            tl_item.GetStart(),
                            dr_timeline.GetStartFrame(),
                            current_project.GetSetting("timelineFrameRate")
                        )
                    )
                ot_track.append(_create_clip(tl_item))
            ot_timeline.tracks.append(ot_track)
    otio.adapters.write_to_file(
        ot_timeline, "{}/{}.otio".format(output_path, dr_timeline.GetName()))


title_font = ui.Font({"PixelSize": 18})
dlg = disp.AddWindow(
  {
    "WindowTitle": "Export OTIO",
    "ID": "OTIOwin",
    "Geometry": [250, 250, 250, 100],
    "Spacing": 0,
    "Margin": 10
  },
  [
    ui.VGroup(
      {
        "Spacing": 2
      },
      [
        ui.Button(
            {
                "ID": "exportfilebttn",
                "Text": "Select Destination",
                "Weight": 1.25,
                "ToolTip": "Choose where to save the otio",
                "Flat": False
            }
        ),
        ui.VGap(),
        ui.Button(
            {
                "ID": "exportbttn",
                "Text": "Export",
                "Weight": 2,
                "ToolTip": "Export the current timeline",
                "Flat": False
            }
        )
      ]
    )
  ]
)

itm = dlg.GetItems()


def _close_window(event):
    disp.ExitLoop()


def _export_button(event):
    _create_ot_timeline(itm["exportfilebttn"].Text)
    _close_window(None)


def _export_file_pressed(event):
    selectedPath = fu.RequestDir(os.path.expanduser("~/Documents"))
    itm["exportfilebttn"].Text = selectedPath


dlg.On.OTIOwin.Close = _close_window
dlg.On.exportfilebttn.Clicked = _export_file_pressed
dlg.On.exportbttn.Clicked = _export_button
dlg.Show()
disp.RunLoop()
dlg.Hide()
