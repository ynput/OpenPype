#!/usr/bin/env python
import os
from openpype.hosts.resolve.otio import davinci_export as otio_export

resolve = bmd.scriptapp("Resolve")  # noqa
fu = resolve.Fusion()

ui = fu.UIManager
disp = bmd.UIDispatcher(fu.UIManager)  # noqa


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
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    otio_timeline = otio_export.create_otio_timeline(project)
    otio_path = os.path.join(
        itm["exportfilebttn"].Text,
        timeline.GetName() + ".otio")
    print(otio_path)
    otio_export.write_to_file(
        otio_timeline,
        otio_path)
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
