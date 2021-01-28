#! python3
import os
resolve = bmd.scriptapp("Resolve")  # noqa
fu = resolve.Fusion()
ui = fu.UIManager
disp = bmd.UIDispatcher(fu.UIManager)  # noqa



title_font = ui.Font({"PixelSize": 18})
dlg = disp.AddWindow(
    {
        "WindowTitle": "Get Testing folder",
        "ID": "TestingWin",
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
                        "ID": "inputTestSourcesFolder",
                        "Text": "Select folder with testing medias",
                        "Weight": 1.25,
                        "ToolTip": "Chose folder with videos, sequences, single images, nested folders with medias",
                        "Flat": False
                    }
                ),
                ui.VGap(),
                ui.Button(
                    {
                        "ID": "openButton",
                        "Text": "Open",
                        "Weight": 2,
                        "ToolTip": "Open and run test on the folder",
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
    otio_import.read_from_file(itm["inputTestSourcesFolder"].Text)
    _close_window(None)


def _import_file_pressed(event):
    selected_path = fu.RequestFile(os.path.expanduser("~"))
    itm["inputTestSourcesFolder"].Text = selected_path


dlg.On.TestingWin.Close = _close_window
dlg.On.inputTestSourcesFolder.Clicked = _import_file_pressed
dlg.On.openButton.Clicked = _import_button
dlg.Show()
disp.RunLoop()
dlg.Hide()
