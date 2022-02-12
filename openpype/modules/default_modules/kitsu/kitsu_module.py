"""Addon definition is located here.

Import of python packages that may not be available should not be imported
in global space here until are required or used.
- Qt related imports
- imports of Python 3 packages
    - we still support Python 2 hosts where addon definition should available
"""
import click
import os
import re
from typing import Dict, List

from avalon.api import AvalonMongoDB
import gazu
from openpype.api import get_project_settings
from openpype.lib import create_project
from openpype.modules import JsonFilesSettingsDef, OpenPypeModule, ModulesManager
from pymongo import DeleteOne, UpdateOne
from openpype_interfaces import IPluginPaths, ITrayAction


# Settings definition of this addon using `JsonFilesSettingsDef`
# - JsonFilesSettingsDef is prepared settings definition using json files
#   to define settings and store default values
class AddonSettingsDef(JsonFilesSettingsDef):
    # This will add prefixes to every schema and template from `schemas`
    #   subfolder.
    # - it is not required to fill the prefix but it is highly
    #   recommended as schemas and templates may have name clashes across
    #   multiple addons
    # - it is also recommended that prefix has addon name in it
    schema_prefix = "kitsu"

    def get_settings_root_path(self):
        """Implemented abstract class of JsonFilesSettingsDef.

        Return directory path where json files defying addon settings are
        located.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")


class KitsuModule(OpenPypeModule, IPluginPaths, ITrayAction):
    """This Addon has defined it's settings and interface.

    This example has system settings with an enabled option. And use
    few other interfaces:
    - `IPluginPaths` to define custom plugin paths
    - `ITrayAction` to be shown in tray tool
    """

    label = "Kitsu"
    name = "kitsu"

    def initialize(self, settings):
        """Initialization of addon."""
        module_settings = settings[self.name]

        # Enabled by settings
        self.enabled = module_settings.get("enabled", False)

        # Add API URL schema
        kitsu_url = module_settings["server"].strip()
        if kitsu_url:
            # Ensure web url
            if not kitsu_url.startswith("http"):
                kitsu_url = "https://" + kitsu_url

            # Check for "/api" url validity
            if not kitsu_url.endswith("api"):
                kitsu_url = f"{kitsu_url}{'' if kitsu_url.endswith('/') else '/'}api"

        self.server_url = kitsu_url

        # Set credentials
        self.script_login = module_settings["script_login"]
        self.script_pwd = module_settings["script_pwd"]

        # Prepare variables that can be used or set afterwards
        self._connected_modules = None
        # UI which must not be created at this time
        self._dialog = None

    def tray_init(self):
        """Implementation of abstract method for `ITrayAction`.

        We're definitely  in tray tool so we can pre create dialog.
        """

        self._create_dialog()

    def get_global_environments(self):
        """Kitsu's global environments."""
        return {
            "KITSU_SERVER": self.server_url,
            "KITSU_LOGIN": self.script_login,
            "KITSU_PWD": self.script_pwd,
        }

    def _create_dialog(self):
        # Don't recreate dialog if already exists
        if self._dialog is not None:
            return

        from .widgets import MyExampleDialog

        self._dialog = MyExampleDialog()

    def show_dialog(self):
        """Show dialog with connected modules.

        This can be called from anywhere but can also crash in headless mode.
        There is no way to prevent addon to do invalid operations if he's
        not handling them.
        """
        # Make sure dialog is created
        self._create_dialog()
        # Show dialog
        self._dialog.open()

    def get_connected_modules(self):
        """Custom implementation of addon."""
        names = set()
        if self._connected_modules is not None:
            for module in self._connected_modules:
                names.add(module.name)
        return names

    def on_action_trigger(self):
        """Implementation of abstract method for `ITrayAction`."""
        self.show_dialog()

    def get_plugin_paths(self):
        """Implementation of abstract method for `IPluginPaths`."""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        return {"publish": [os.path.join(current_dir, "plugins", "publish")]}

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(KitsuModule.name, help="Kitsu dynamic cli commands.")
def cli_main():
    pass


@cli_main.command()
def sync_zou():
    """Synchronize Zou server database (Kitsu backend) with openpype database."""

    # Connect to server
    gazu.client.set_host(os.environ["KITSU_SERVER"])

    # Authenticate
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

    # Iterate projects
    dbcon = AvalonMongoDB()
    dbcon.install()

    op_projects = [p for p in dbcon.projects()]
    bulk_writes = []
    for op_project in op_projects:
        # Create project locally
        # Try to find project document
        project_name = op_project["name"]
        project_code = op_project["data"]["code"]
        dbcon.Session["AVALON_PROJECT"] = project_name

        # Get all entities from zou
        zou_project = gazu.project.get_project_by_name(project_name)

        # Create project
        if zou_project is None:
            raise RuntimeError(
                f"Project '{project_name}' doesn't exist in Zou database, please create it in Kitsu and add logged user to it before running synchronization."
            )

        # Update project settings and data
        zou_project.update(
            {
                "code": op_project["data"]["code"],
                "fps": op_project["data"]["fps"],
                "resolution": f"{op_project['data']['resolutionWidth']}x{op_project['data']['resolutionHeight']}",
            }
        )
        gazu.project.update_project(zou_project)
        gazu.project.update_project_data(zou_project, data=op_project["data"])

        all_assets = gazu.asset.all_assets_for_project(zou_project)
        all_episodes = gazu.shot.all_episodes_for_project(zou_project)
        all_seqs = gazu.shot.all_sequences_for_project(zou_project)
        all_shots = gazu.shot.all_shots_for_project(zou_project)
        print(zou_project["name"])
        all_entities_ids = {
            e["id"] for e in all_episodes + all_seqs + all_shots + all_assets
        }

        project_module_settings = get_project_settings(project_name)["kitsu"]

        # Create new assets
        # Query all assets of the local project
        project_col = dbcon.database[project_name]
        asset_docs = [asset_doc for asset_doc in project_col.find({"type": "asset"})]

        new_assets_docs = [
            doc
            for doc in asset_docs
            if doc["data"].get("zou_id") not in all_entities_ids
        ]
        naming_pattern = project_module_settings["entities_naming_pattern"]
        regex_ep = re.compile(
            r"({})|({})|({})".format(
                naming_pattern["episode"].replace("#", "\d"),
                naming_pattern["sequence"].replace("#", "\d"),
                naming_pattern["shot"].replace("#", "\d"),
            ),
            re.IGNORECASE,
        )
        for doc in new_assets_docs:
            match = regex_ep.match(doc["name"])
            if not match:
                # TODO asset
                continue

            print(doc)
            if match.group(1):  # Episode
                new_episode = gazu.shot.new_episode(zou_project, doc["name"])

                # Update doc with zou id
                bulk_writes.append(
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {"$set": {"data.zou_id": new_episode["id"]}},
                    )
                )
            elif match.group(2):  # Sequence
                # TODO match zou episode
                new_sequence = gazu.shot.new_sequence(zou_project, doc["name"])

                # Update doc with zou id
                bulk_writes.append(
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {"$set": {"data.zou_id": new_sequence["id"]}},
                    )
                )
            elif match.group(3):  # Shot
                pass

        # Delete
        # if gazu.

        # Write into DB
        if bulk_writes:
            project_col.bulk_write(bulk_writes)

    dbcon.uninstall()

    return

    for project in all_projects:
        # Create project locally
        # Try to find project document
        project_name = project["name"]
        project_code = project_name
        dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = dbcon.find_one({"type": "project"})

        # Get all assets from zou
        all_assets = gazu.asset.all_assets_for_project(project)
        all_episodes = gazu.shot.all_episodes_for_project(project)
        all_seqs = gazu.shot.all_sequences_for_project(project)
        all_shots = gazu.shot.all_shots_for_project(project)

        # Create project if is not available
        # - creation is required to be able set project anatomy and attributes
        to_insert = []
        if not project_doc:
            print(f"Creating project '{project_name}'")
            project_doc = create_project(project_name, project_code, dbcon=dbcon)

            # Project tasks
            bulk_writes.append(
                UpdateOne(
                    {"_id": project_doc["_id"]},
                    {
                        "$set": {
                            "config.tasks": {
                                t["name"]: {
                                    "short_name": t.get("short_name", t["name"])
                                }
                                for t in gazu.task.all_task_types_for_project(project)
                            }
                        }
                    },
                )
            )

        # Query all assets of the local project
        project_col = dbcon.database[project_code]
        asset_doc_ids = {
            asset_doc["data"]["zou_id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou_id")
        }
        asset_doc_ids[project["id"]] = project_doc

        # Create
        to_insert.extend(
            [
                {
                    "name": item["name"],
                    "type": "asset",
                    "schema": "openpype:asset-3.0",
                    "data": {"zou_id": item["id"], "tasks": {}},
                }
                for item in all_episodes + all_assets + all_seqs + all_shots
                if item["id"] not in asset_doc_ids.keys()
            ]
        )
        if to_insert:
            # Insert in doc
            project_col.insert_many(to_insert)

            # Update existing docs
            asset_doc_ids.update(
                {
                    asset_doc["data"]["zou_id"]: asset_doc
                    for asset_doc in project_col.find({"type": "asset"})
                    if asset_doc["data"].get("zou_id")
                }
            )

        # Update
        all_entities = all_assets + all_episodes + all_seqs + all_shots
        bulk_writes.extend(update_op_assets(all_entities, asset_doc_ids))

        # Delete
        diff_assets = set(asset_doc_ids.keys()) - {
            e["id"] for e in all_entities + [project]
        }
        if diff_assets:
            bulk_writes.extend(
                [DeleteOne(asset_doc_ids[asset_id]) for asset_id in diff_assets]
            )


@cli_main.command()
def sync_openpype():
    """Synchronize openpype database from Zou sever database."""

    # Connect to server
    gazu.client.set_host(os.environ["KITSU_SERVER"])

    # Authenticate
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

    # Iterate projects
    dbcon = AvalonMongoDB()
    dbcon.install()
    all_projects = gazu.project.all_projects()
    bulk_writes = []
    for project in all_projects:
        # Create project locally
        # Try to find project document
        project_name = project["name"]
        project_code = project_name
        dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = dbcon.find_one({"type": "project"})

        # Get all assets from zou
        all_assets = gazu.asset.all_assets_for_project(project)
        all_episodes = gazu.shot.all_episodes_for_project(project)
        all_seqs = gazu.shot.all_sequences_for_project(project)
        all_shots = gazu.shot.all_shots_for_project(project)

        # Create project if is not available
        # - creation is required to be able set project anatomy and attributes
        to_insert = []
        if not project_doc:
            print(f"Creating project '{project_name}'")
            project_doc = create_project(project_name, project_code, dbcon=dbcon)

        # Project data and tasks
        bulk_writes.append(
            UpdateOne(
                {"_id": project_doc["_id"]},
                {
                    "$set": {
                        "config.tasks": {
                            t["name"]: {"short_name": t.get("short_name", t["name"])}
                            for t in gazu.task.all_task_types_for_project(project)
                        },
                        "data": project["data"].update(
                            {
                                "code": project["code"],
                                "fps": project_code["fps"],
                                "resolutionWidth": project["resolution"].split("x")[0],
                                "resolutionHeight": project["resolution"].split("x")[1],
                            }
                        ),
                    }
                },
            )
        )

        # Query all assets of the local project
        project_col = dbcon.database[project_code]
        asset_doc_ids = {
            asset_doc["data"]["zou_id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou_id")
        }
        asset_doc_ids[project["id"]] = project_doc

        # Create
        to_insert.extend(
            [
                {
                    "name": item["name"],
                    "type": "asset",
                    "schema": "openpype:asset-3.0",
                    "data": {"zou_id": item["id"], "tasks": {}},
                }
                for item in all_episodes + all_assets + all_seqs + all_shots
                if item["id"] not in asset_doc_ids.keys()
            ]
        )
        if to_insert:
            # Insert in doc
            project_col.insert_many(to_insert)

            # Update existing docs
            asset_doc_ids.update(
                {
                    asset_doc["data"]["zou_id"]: asset_doc
                    for asset_doc in project_col.find({"type": "asset"})
                    if asset_doc["data"].get("zou_id")
                }
            )

        # Update
        all_entities = all_assets + all_episodes + all_seqs + all_shots
        bulk_writes.extend(update_op_assets(all_entities, asset_doc_ids))

        # Delete
        diff_assets = set(asset_doc_ids.keys()) - {
            e["id"] for e in all_entities + [project]
        }
        if diff_assets:
            bulk_writes.extend(
                [DeleteOne(asset_doc_ids[asset_id]) for asset_id in diff_assets]
            )

        # Write into DB
        if bulk_writes:
            project_col.bulk_write(bulk_writes)

    dbcon.uninstall()


def update_op_assets(
    items_list: List[dict], asset_doc_ids: Dict[str, dict]
) -> List[UpdateOne]:
    """Update OpenPype assets.
    Set 'data' and 'parent' fields.

    :param items_list: List of zou items to update
    :param asset_doc_ids: Dicts of [{zou_id: asset_doc}, ...]
    :return: List of UpdateOne objects
    """
    bulk_writes = []
    for item in items_list:
        # Update asset
        item_doc = asset_doc_ids[item["id"]]
        item_data = item_doc["data"].copy()

        # Tasks
        tasks_list = None
        if item["type"] == "Asset":
            tasks_list = gazu.task.all_tasks_for_asset(item)
        elif item["type"] == "Shot":
            tasks_list = gazu.task.all_tasks_for_shot(item)
        if tasks_list:
            item_data["tasks"] = {
                t["task_type_name"]: {"type": t["task_type_name"]} for t in tasks_list
            }

        # Visual parent for hierarchy
        direct_parent_id = item["parent_id"] or item["source_id"]
        if direct_parent_id:
            visual_parent_doc = asset_doc_ids[direct_parent_id]
            item_data["visualParent"] = visual_parent_doc["_id"]

        # Add parents for hierarchy
        parent_zou_id = item["parent_id"]
        item_data["parents"] = []
        while parent_zou_id is not None:
            parent_doc = asset_doc_ids[parent_zou_id]
            item_data["parents"].insert(0, parent_doc["name"])

            parent_zou_id = next(
                i for i in items_list if i["id"] == parent_doc["data"]["zou_id"]
            )["parent_id"]

        # Update 'data' different in zou DB
        updated_data = {
            k: item_data[k]
            for k in item_data.keys()
            if item_doc["data"].get(k) != item_data[k]
        }
        if updated_data or not item_doc.get("parent"):
            bulk_writes.append(
                UpdateOne(
                    {"_id": item_doc["_id"]},
                    {
                        "$set": {
                            "data": item_data,
                            "parent": asset_doc_ids[item["project_id"]]["_id"],
                        }
                    },
                )
            )

    return bulk_writes


@cli_main.command()
def show_dialog():
    """Show ExampleAddon dialog.

    We don't have access to addon directly through cli so we have to create
    it again.
    """
    from openpype.tools.utils.lib import qt_app_context

    manager = ModulesManager()
    example_addon = manager.modules_by_name[KitsuModule.name]
    with qt_app_context():
        example_addon.show_dialog()
