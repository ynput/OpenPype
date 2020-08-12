"""Utility script for updating database with configuration files

Until assets are created entirely in the database, this script
provides a bridge between the file-based project inventory and configuration.

- Migrating an old project:
    $ python -m avalon.inventory --extract --silo-parent=f02_prod
    $ python -m avalon.inventory --upload

- Managing an existing project:
    1. Run `python -m avalon.inventory --load`
    2. Update the .inventory.toml or .config.toml
    3. Run `python -m avalon.inventory --save`

"""

import os
from Qt import QtGui
from avalon import io, lib, pipeline
from avalon.vendor import qtawesome
from pype.api import resources

ICON_CACHE = {}
NOT_FOUND = type("NotFound", (object, ), {})


def list_project_tasks():
    """List the project task types available in the current project"""
    project = io.find_one({"type": "project"})
    return [task["name"] for task in project["config"]["tasks"]]


def get_application_actions(project):
    """Define dynamic Application classes for project using `.toml` files

    Args:
        project (dict): project document from the database

    Returns:
        list: list of dictionaries
    """

    apps = []
    for app in project["config"]["apps"]:
        try:
            app_name = app["name"]
            app_definition = lib.get_application(app_name)
        except Exception as exc:
            print("Unable to load application: %s - %s" % (app['name'], exc))
            continue

        # Get from app definition, if not there from app in project
        icon = app_definition.get("icon", app.get("icon", "folder-o"))
        color = app_definition.get("color", app.get("color", None))
        order = app_definition.get("order", app.get("order", 0))
        label = app.get("label") or app_definition.get("label") or app["name"]
        group = app.get("group") or app_definition.get("group")

        action = type(
            "app_{}".format(app_name),
            (pipeline.Application,),
            {
                "name": app_name,
                "label": label,
                "group": group,
                "icon": icon,
                "color": color,
                "order": order,
                "config": app_definition.copy()
            }
        )

        apps.append(action)
    return apps


def get_action_icon(action):
    icon_name = action.icon
    if not icon_name:
        return None

    global ICON_CACHE

    icon = ICON_CACHE.get(icon_name)
    if icon is NOT_FOUND:
        return None
    elif icon:
        return icon

    icon_path = resources.get_resource(icon_name)
    if os.path.exists(icon_path):
        icon = QtGui.QIcon(icon_path)
        ICON_CACHE[icon_name] = icon
        return icon

    try:
        icon_color = getattr(action, "color", None) or "white"
        icon = qtawesome.icon(
            "fa.{}".format(icon_name), color=icon_color
        )

    except Exception:
        print("Can't load icon \"{}\"".format(icon_name))

    return icon
