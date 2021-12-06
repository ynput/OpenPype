import os
import nuke
from avalon.nuke.pipeline import get_main_window

from .lib import WorkfileSettings
from openpype.api import Logger, BuildWorkfile, get_current_project_settings
from openpype.tools.utils import host_tools


log = Logger().get_logger(__name__)

menu_label = os.environ["AVALON_LABEL"]
context_label = None


def change_context_label(*args):
    global context_label
    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(menu_label)

    label = "{0}, {1}".format(
        os.environ["AVALON_ASSET"], os.environ["AVALON_TASK"]
    )

    rm_item = [
        (i, item) for i, item in enumerate(menu.items())
        if context_label in item.name()
    ][0]

    menu.removeItem(rm_item[1].name())

    context_action = menu.addCommand(
        label,
        index=(rm_item[0])
    )
    context_action.setEnabled(False)

    log.info("Task label changed from `{}` to `{}`".format(
        context_label, label))

    context_label = label



def install():
    from openpype.hosts.nuke.api import reload_config

    global context_label

    # uninstall original avalon menu
    uninstall()

    main_window = get_main_window()
    menubar = nuke.menu("Nuke")
    menu = menubar.addMenu(menu_label)

    label = "{0}, {1}".format(
        os.environ["AVALON_ASSET"], os.environ["AVALON_TASK"]
    )
    context_label = label
    context_action = menu.addCommand(label)
    context_action.setEnabled(False)

    menu.addSeparator()
    menu.addCommand(
        "Work Files...",
        lambda: host_tools.show_workfiles(parent=main_window)
    )

    menu.addSeparator()
    menu.addCommand(
        "Create...",
        lambda: host_tools.show_creator(parent=main_window)
    )
    menu.addCommand(
        "Load...",
        lambda: host_tools.show_loader(
            parent=main_window,
            use_context=True
        )
    )
    menu.addCommand(
        "Publish...",
        lambda: host_tools.show_publish(parent=main_window)
    )
    menu.addCommand(
        "Manage...",
        lambda: host_tools.show_scene_inventory(parent=main_window)
    )

    menu.addSeparator()
    menu.addCommand(
        "Set Resolution",
        lambda: WorkfileSettings().reset_resolution()
    )
    menu.addCommand(
        "Set Frame Range",
        lambda: WorkfileSettings().reset_frame_range_handles()
    )
    menu.addCommand(
        "Set Colorspace",
        lambda: WorkfileSettings().set_colorspace()
    )
    menu.addCommand(
        "Apply All Settings",
        lambda: WorkfileSettings().set_context_settings()
    )

    menu.addSeparator()
    menu.addCommand(
        "Build Workfile",
        lambda: BuildWorkfile().process()
    )

    menu.addSeparator()
    menu.addCommand(
        "Experimental tools...",
        lambda: host_tools.show_experimental_tools_dialog(parent=main_window)
    )

    # add reload pipeline only in debug mode
    if bool(os.getenv("NUKE_DEBUG")):
        menu.addSeparator()
        menu.addCommand("Reload Pipeline", reload_config)

    # adding shortcuts
    add_shortcuts_from_presets()


def uninstall():

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(menu_label)

    for item in menu.items():
        log.info("Removing menu item: {}".format(item.name()))
        menu.removeItem(item.name())


def add_shortcuts_from_presets():
    menubar = nuke.menu("Nuke")
    nuke_presets = get_current_project_settings()["nuke"]["general"]

    if nuke_presets.get("menu"):
        menu_label_mapping = {
            "manage": "Manage...",
            "create": "Create...",
            "load": "Load...",
            "build_workfile": "Build Workfile",
            "publish": "Publish..."
        }

        for command_name, shortcut_str in nuke_presets.get("menu").items():
            log.info("menu_name `{}` | menu_label `{}`".format(
                command_name, menu_label
            ))
            log.info("Adding Shortcut `{}` to `{}`".format(
                shortcut_str, command_name
            ))
            try:
                menu = menubar.findItem(menu_label)
                item_label = menu_label_mapping[command_name]
                menuitem = menu.findItem(item_label)
                menuitem.setShortcut(shortcut_str)
            except AttributeError as e:
                log.error(e)
