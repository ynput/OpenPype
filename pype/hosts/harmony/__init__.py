import os
import sys

from avalon import api, harmony
from avalon.vendor import Qt
import pyblish.api
from pype import lib


def set_scene_settings(settings):
    func = """function func(args)
    {
        if (args[0]["fps"])
        {
            scene.setFrameRate(args[0]["fps"]);
        }
        if (args[0]["frameStart"] && args[0]["frameEnd"])
        {
            var duration = args[0]["frameEnd"] - args[0]["frameStart"] + 1
            if (frame.numberOf() > duration)
            {
                frame.remove(
                    duration, frame.numberOf() - duration
                );
            }
            if (frame.numberOf() < duration)
            {
                frame.insert(
                    duration, duration - frame.numberOf()
                );
            }

            scene.setStartFrame(1);
            scene.setStopFrame(duration);
        }
        if (args[0]["resolutionWidth"] && args[0]["resolutionHeight"])
        {
            scene.setDefaultResolution(
                args[0]["resolutionWidth"], args[0]["resolutionHeight"], 41.112
            )
        }
    }
    func
    """
    harmony.send({"function": func, "args": [settings]})


def get_asset_settings():
    asset_data = lib.get_asset()["data"]
    fps = asset_data.get("fps")
    frame_start = asset_data.get("frameStart")
    frame_end = asset_data.get("frameEnd")
    resolution_width = asset_data.get("resolutionWidth")
    resolution_height = asset_data.get("resolutionHeight")

    return {
        "fps": fps,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "resolutionWidth": resolution_width,
        "resolutionHeight": resolution_height
    }


def ensure_scene_settings():
    settings = get_asset_settings()

    invalid_settings = []
    valid_settings = {}
    for key, value in settings.items():
        if value is None:
            invalid_settings.append(key)
        else:
            valid_settings[key] = value

    # Warn about missing attributes.
    print("Starting new QApplication..")
    app = Qt.QtWidgets.QApplication(sys.argv)

    message_box = Qt.QtWidgets.QMessageBox()
    message_box.setIcon(Qt.QtWidgets.QMessageBox.Warning)
    msg = "Missing attributes:"
    if invalid_settings:
        for item in invalid_settings:
            msg += f"\n{item}"
        message_box.setText(msg)
        message_box.exec_()

    # Garbage collect QApplication.
    del app

    set_scene_settings(valid_settings)


def export_template(backdrops, nodes, filepath):
    func = """function func(args)
    {
        // Add an extra node just so a new group can be created.
        var temp_node = node.add("Top", "temp_note", "NOTE", 0, 0, 0);
        var template_group = node.createGroup(temp_node, "temp_group");
        node.deleteNode( template_group + "/temp_note" );

        // This will make Node View to focus on the new group.
        selection.clearSelection();
        selection.addNodeToSelection(template_group);
        Action.perform("onActionEnterGroup()", "Node View");

        // Recreate backdrops in group.
        for (var i = 0 ; i < args[0].length; i++)
        {
            Backdrop.addBackdrop(template_group, args[0][i]);
        };

        // Copy-paste the selected nodes into the new group.
        var drag_object = copyPaste.copy(args[1], 1, frame.numberOf, "");
        copyPaste.pasteNewNodes(drag_object, template_group, "");

        // Select all nodes within group and export as template.
        Action.perform( "selectAll()", "Node View" );
        copyPaste.createTemplateFromSelection(args[2], args[3]);

        // Unfocus the group in Node view, delete all nodes and backdrops
        // created during the process.
        Action.perform("onActionUpToParent()", "Node View");
        node.deleteNode(template_group, true, true);
    }
    func
    """
    harmony.send({
        "function": func,
        "args": [
            backdrops,
            nodes,
            os.path.basename(filepath),
            os.path.dirname(filepath)
        ]
    })


def install():
    print("Installing Pype config...")

    plugins_directory = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "plugins",
        "harmony"
    )

    pyblish.api.register_plugin_path(
        os.path.join(plugins_directory, "publish")
    )
    api.register_plugin_path(
        api.Loader, os.path.join(plugins_directory, "load")
    )
    api.register_plugin_path(
        api.Creator, os.path.join(plugins_directory, "create")
    )

    # Register callbacks.
    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    api.on("application.launched", ensure_scene_settings)


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node enabling on instance toggles."""
    func = """function func(args)
    {
        node.setEnable(args[0], args[1])
    }
    func
    """
    harmony.send(
        {"function": func, "args": [instance[0], new_value]}
    )
