"""Kitsu module."""

import click
import os
import re

from pymongo import DeleteOne, UpdateOne

from avalon.api import AvalonMongoDB
from openpype.api import get_project_settings
from openpype.lib.local_settings import OpenPypeSecureRegistry
from openpype.modules import OpenPypeModule, ModulesManager
from openpype.settings.lib import get_local_settings
from openpype_interfaces import IPluginPaths, ITrayAction
from .utils.listeners import start_listeners
from .utils.openpype import (
    create_op_asset,
    sync_project,
    update_op_assets,
)


class KitsuModule(OpenPypeModule, IPluginPaths, ITrayAction):
    """Kitsu module class."""

    label = "Kitsu"
    name = "kitsu"

    def initialize(self, settings):
        """Initialization of module."""
        module_settings = settings[self.name]

        # Get user registry
        user_registry = OpenPypeSecureRegistry("kitsu_user")

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
                kitsu_url = (
                    f"{kitsu_url}{'' if kitsu_url.endswith('/') else '/'}api"
                )

        self.server_url = kitsu_url

        # Set credentials
        self.kitsu_login = user_registry.get_item("login", None)
        self.kitsu_password = user_registry.get_item("password", None)

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
            "KITSU_LOGIN": self.kitsu_login,
            "KITSU_PWD": self.kitsu_password,
        }

    def _create_dialog(self):
        # Don't recreate dialog if already exists
        if self._dialog is not None:
            return

        from .kitsu_widgets import PasswordDialog

        self._dialog = PasswordDialog()

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
    import gazu

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
        dbcon.Session["AVALON_PROJECT"] = project_name

        # Get all entities from zou
        print(f"Synchronizing {project_name}...")
        zou_project = gazu.project.get_project_by_name(project_name)

        # Create project
        if zou_project is None:
            raise RuntimeError(
                f"Project '{project_name}' doesn't exist in Zou database, please create it in Kitsu and add OpenPype user to it before running synchronization."
            )

        # Update project settings and data
        if op_project["data"]:
            zou_project.update(
                {
                    "code": op_project["data"]["code"],
                    "fps": op_project["data"]["fps"],
                    "resolution": f"{op_project['data']['resolutionWidth']}x{op_project['data']['resolutionHeight']}",
                }
            )
            gazu.project.update_project_data(
                zou_project, data=op_project["data"]
            )
        gazu.project.update_project(zou_project)

        asset_types = gazu.asset.all_asset_types()
        all_assets = gazu.asset.all_assets_for_project(zou_project)
        all_episodes = gazu.shot.all_episodes_for_project(zou_project)
        all_seqs = gazu.shot.all_sequences_for_project(zou_project)
        all_shots = gazu.shot.all_shots_for_project(zou_project)
        all_entities_ids = {
            e["id"] for e in all_episodes + all_seqs + all_shots + all_assets
        }

        # Query all assets of the local project
        project_module_settings = get_project_settings(project_name)["kitsu"]
        project_col = dbcon.database[project_name]
        asset_docs = {
            asset_doc["_id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
        }

        # Create new assets
        new_assets_docs = [
            doc
            for doc in asset_docs.values()
            if doc["data"].get("zou", {}).get("id") not in all_entities_ids
        ]
        naming_pattern = project_module_settings["entities_naming_pattern"]
        regex_ep = re.compile(
            r"(.*{}.*)|(.*{}.*)|(.*{}.*)".format(
                naming_pattern["shot"].replace("#", ""),
                naming_pattern["sequence"].replace("#", ""),
                naming_pattern["episode"].replace("#", ""),
            ),
            re.IGNORECASE,
        )
        for doc in new_assets_docs:
            visual_parent_id = doc["data"]["visualParent"]
            parent_substitutes = []

            # Match asset type by it's name
            match = regex_ep.match(doc["name"])
            if not match:  # Asset
                new_entity = gazu.asset.new_asset(
                    zou_project, asset_types[0], doc["name"]
                )
            # Match case in shot<sequence<episode order to support composed names like 'ep01_sq01_sh01'
            elif match.group(1):  # Shot
                # Match and check parent doc
                parent_doc = asset_docs[visual_parent_id]
                zou_parent_id = parent_doc["data"]["zou"]["id"]
                if parent_doc["data"].get("zou", {}).get("type") != "Sequence":
                    # Substitute name
                    digits_padding = naming_pattern["sequence"].count("#")
                    substitute_sequence_name = (
                        f'{naming_pattern["episode"].replace("#" * digits_padding, "1".zfill(digits_padding))}_'  # Episode
                        f'{naming_pattern["sequence"].replace("#" * digits_padding, "1".zfill(digits_padding))}'  # Sequence
                    )

                    # Warn
                    print(
                        f"Shot {doc['name']} must be parented to a Sequence in Kitsu. "
                        f"Creating automatically one substitute sequence called {substitute_sequence_name} in Kitsu..."
                    )

                    # Create new sequence and set it as substitute
                    created_sequence = gazu.shot.new_sequence(
                        zou_project,
                        substitute_sequence_name,
                        episode=zou_parent_id,
                    )
                    gazu.shot.update_sequence_data(
                        created_sequence, {"is_substitute": True}
                    )
                    parent_substitutes.append(created_sequence)

                    # Update parent ID
                    zou_parent_id = created_sequence["id"]

                # Create shot
                new_entity = gazu.shot.new_shot(
                    zou_project,
                    zou_parent_id,
                    doc["name"],
                    frame_in=doc["data"]["frameStart"],
                    frame_out=doc["data"]["frameEnd"],
                    nb_frames=doc["data"]["frameEnd"]
                    - doc["data"]["frameStart"],
                )

            elif match.group(2):  # Sequence
                parent_doc = asset_docs[visual_parent_id]
                new_entity = gazu.shot.new_sequence(
                    zou_project,
                    doc["name"],
                    episode=parent_doc["data"]["zou"]["id"],
                )

            elif match.group(3):  # Episode
                new_entity = gazu.shot.new_episode(zou_project, doc["name"])

            # Update doc with zou id
            doc["data"].update(
                {
                    "visualParent": visual_parent_id,
                    "zou": new_entity,
                }
            )
            bulk_writes.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "data.visualParent": visual_parent_id,
                            "data.zou": new_entity,
                            "data.parent_substitutes": parent_substitutes,
                        }
                    },
                )
            )

        # Update assets
        all_tasks_types = {t["name"]: t for t in gazu.task.all_task_types()}
        assets_docs_to_update = [
            doc
            for doc in asset_docs.values()
            if doc["data"].get("zou", {}).get("id") in all_entities_ids
        ]
        for doc in assets_docs_to_update:
            zou_id = doc["data"]["zou"]["id"]
            if zou_id:
                # Data
                entity_data = {}
                frame_in = doc["data"].get("frameStart")
                frame_out = doc["data"].get("frameEnd")
                if frame_in or frame_out:
                    entity_data.update(
                        {
                            "data": {
                                "frame_in": frame_in,
                                "frame_out": frame_out,
                            },
                            "nb_frames": frame_out - frame_in,
                        }
                    )
                entity = gazu.raw.update("entities", zou_id, entity_data)

                # Tasks
                all_tasks_func = getattr(
                    gazu.task, f"all_tasks_for_{entity['type'].lower()}"
                )
                entity_tasks = {t["name"] for t in all_tasks_func(entity)}
                for task_name in doc["data"]["tasks"].keys():
                    # Create only if new
                    if task_name not in entity_tasks:
                        task_type = all_tasks_types.get(task_name)

                        # Create non existing task
                        if not task_type:
                            task_type = gazu.task.new_task_type(task_name)
                            all_tasks_types[task_name] = task_type

                        # New task for entity
                        gazu.task.new_task(entity, task_type)

        # Delete
        deleted_entities = all_entities_ids - {
            asset_doc["data"].get("zou", {}).get("id")
            for asset_doc in asset_docs.values()
        }
        for entity_id in deleted_entities:
            gazu.raw.delete(f"data/entities/{entity_id}")

        # Write into DB
        if bulk_writes:
            project_col.bulk_write(bulk_writes)

    dbcon.uninstall()


@cli_main.command()
@click.option(
    "-l",
    "--listen",
    is_flag=True,
    help="Listen Kitsu server after synchronization.",
)
def sync_openpype(listen: bool):
    """Synchronize openpype database from Zou sever database."""
    import gazu

    # Connect to server
    gazu.client.set_host(os.environ["KITSU_SERVER"])

    # Authenticate
    kitsu_login = os.environ.get("KITSU_LOGIN")
    kitsu_pwd = os.environ.get("KITSU_PWD")
    if not kitsu_login or not kitsu_pwd:  # Sentinel to log-in
        log_in_dialog()
        return

    gazu.log_in(kitsu_login, kitsu_pwd)

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

        print(f"Synchronizing {project_name}...")

        # Get all assets from zou
        all_assets = gazu.asset.all_assets_for_project(project)
        all_episodes = gazu.shot.all_episodes_for_project(project)
        all_seqs = gazu.shot.all_sequences_for_project(project)
        all_shots = gazu.shot.all_shots_for_project(project)
        all_entities = [
            e
            for e in all_assets + all_episodes + all_seqs + all_shots
            if e["data"] and not e["data"].get("is_substitute")
        ]

        # Sync project. Create if doesn't exist
        bulk_writes.append(sync_project(project, dbcon))

        # Query all assets of the local project
        project_col = dbcon.database[project_code]
        zou_ids_and_asset_docs = {
            asset_doc["data"]["zou"]["id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou", {}).get("id")
        }
        zou_ids_and_asset_docs[project["id"]] = project_doc

        # Create
        to_insert = []
        to_insert.extend(
            [
                create_op_asset(item)
                for item in all_entities
                if item["id"] not in zou_ids_and_asset_docs.keys()
            ]
        )
        if to_insert:
            # Insert doc in DB
            project_col.insert_many(to_insert)

            # Update existing docs
            zou_ids_and_asset_docs.update(
                {
                    asset_doc["data"]["zou"]["id"]: asset_doc
                    for asset_doc in project_col.find({"type": "asset"})
                    if asset_doc["data"].get("zou")
                }
            )

        # Update
        bulk_writes.extend(
            [
                UpdateOne({"_id": id}, update)
                for id, update in update_op_assets(
                    all_entities, zou_ids_and_asset_docs
                )
            ]
        )

        # Delete
        diff_assets = set(zou_ids_and_asset_docs.keys()) - {
            e["id"] for e in all_entities + [project]
        }
        if diff_assets:
            bulk_writes.extend(
                [
                    DeleteOne(zou_ids_and_asset_docs[asset_id])
                    for asset_id in diff_assets
                ]
            )

        # Write into DB
        if bulk_writes:
            project_col.bulk_write(bulk_writes)

    dbcon.uninstall()

    # Run listening
    if listen:
        start_listeners()


@cli_main.command()
def listen():
    """Listen to Kitsu server."""
    start_listeners()


@cli_main.command()
def sign_in():
    """Sign-in command."""
    log_in_dialog()


def log_in_dialog():
    """Show credentials dialog."""
    from openpype.tools.utils.lib import qt_app_context

    manager = ModulesManager()
    kitsu_addon = manager.modules_by_name[KitsuModule.name]
    with qt_app_context():
        kitsu_addon.show_dialog()
