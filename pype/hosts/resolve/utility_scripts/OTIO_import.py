#!/usr/bin/env python
import os
from openpype.hosts.resolve.otio import davinci_import as otio_import

resolve = bmd.scriptapp("Resolve")  # noqa
fu = resolve.Fusion()
ui = fu.UIManager
disp = bmd.UIDispatcher(fu.UIManager)  # noqa


title_font = ui.Font({"PixelSize": 18})
dlg = disp.AddWindow(
    {
        "WindowTitle": "Import OTIO",
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
                        "ID": "importOTIOfileButton",
                        "Text": "Select OTIO File Path",
                        "Weight": 1.25,
                        "ToolTip": "Choose otio file to import from",
                        "Flat": False
                    }
                ),
                ui.VGap(),
                ui.Button(
                    {
                        "ID": "importButton",
                        "Text": "Import",
                        "Weight": 2,
                        "ToolTip": "Import otio to new timeline",
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


def _import_button(event):
    otio_import.read_from_file(itm["importOTIOfileButton"].Text)
    _close_window(None)


def _import_file_pressed(event):
    selected_path = fu.RequestFile(os.path.expanduser("~/Documents"))
    itm["importOTIOfileButton"].Text = selected_path


dlg.On.OTIOwin.Close = _close_window
dlg.On.importOTIOfileButton.Clicked = _import_file_pressed
dlg.On.importButton.Clicked = _import_button
dlg.Show()
disp.RunLoop()
dlg.Hide()
