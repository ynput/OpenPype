import bpy

from Qt import QtWidgets

from openpype.tools.utils.lib import format_version
from openpype.client import (
    get_version_by_id,
    get_versions,
    get_representation_by_id,
)
from openpype.pipeline import (
    InventoryAction,
    HeroVersionType,
    legacy_io,
    update_container,
)
from openpype.hosts.blender.api.ops import _process_app_events
from openpype.hosts.blender.api.plugin import (
    ContainerMaintainer,
    get_children_recursive,
)


class UpdateTransfertData(InventoryAction):

    label = "Update with local data transfert"
    icon = "angle-double-up"
    color = "#bbdd00"
    order = 0

    update_version = -1

    @staticmethod
    def is_compatible(container):
        return (
            container.get("loader") in ("LinkModelLoader", "AppendModelLoader")
        )

    def process(self, containers):

        current_task = legacy_io.Session.get("AVALON_TASK")
        collections = get_children_recursive(bpy.context.scene.collection)

        maintained_params = []
        if current_task == "Rigging":
            maintained_params.append(
                ["local_data", {"data_types": ["VGROUP_WEIGHTS"]}]
            )

        for container in containers:

            object_name = container["objectName"]
            container_collection = None
            for collection in collections:
                if collection.name == object_name:
                    container_collection = collection
                    break
            else:
                container_collection = bpy.data.collections.get(object_name)

            if not container_collection:
                continue

            with ContainerMaintainer(container_collection, maintained_params):
                mti = update_container(container, self.update_version)
                # NOTE (kaamaurice): I try mti.wait() but seems to stop the
                # bpy.app.timers
                while not mti.done:
                    _process_app_events()


class VersionTransfertData(UpdateTransfertData):

    label = "Set Version with local data transfert"
    icon = "hashtag"
    order = 1

    def _show_version_dialog(self, containers):
        """Create a dialog with the available versions for containers.

        Args:
            containers (list): list of containers to run the "set_version".

        Returns:
            bool: Return True if a valid version is picked.
        """

        active = containers[-1]

        project_name = legacy_io.active_project()
        # Get available versions for active representation
        repre_doc = get_representation_by_id(
            project_name,
            active["representation"],
            fields=["parent"]
        )

        repre_version_doc = get_version_by_id(
            project_name,
            repre_doc["parent"],
            fields=["parent"]
        )

        version_docs = list(get_versions(
            project_name,
            subset_ids=[repre_version_doc["parent"]],
            hero=True
        ))
        hero_version = None
        standard_versions = []
        for version_doc in version_docs:
            if version_doc["type"] == "hero_version":
                hero_version = version_doc
            else:
                standard_versions.append(version_doc)
        versions = list(reversed(
            sorted(standard_versions, key=lambda item: item["name"])
        ))
        if hero_version:
            _version_id = hero_version["version_id"]
            for _version in versions:
                if _version["_id"] != _version_id:
                    continue

                hero_version["name"] = HeroVersionType(
                    _version["name"]
                )
                hero_version["data"] = _version["data"]
                break

        # Get index among the listed versions
        current_item = None
        current_version = active["version"]
        if isinstance(current_version, HeroVersionType):
            current_item = hero_version
        else:
            for version in versions:
                if version["name"] == current_version:
                    current_item = version
                    break

        all_versions = []
        if hero_version:
            all_versions.append(hero_version)
        all_versions.extend(versions)

        if current_item:
            index = all_versions.index(current_item)
        else:
            index = 0

        versions_by_label = dict()
        labels = []
        for version in all_versions:
            is_hero = version["type"] == "hero_version"
            label = format_version(version["name"], is_hero)
            labels.append(label)
            versions_by_label[label] = version["name"]

        label, state = QtWidgets.QInputDialog.getItem(
            None,
            "Set version..",
            "Set version number to",
            labels,
            current=index,
            editable=False
        )
        if not state:
            return

        if label:
            self.update_version = versions_by_label[label]
            return True

    def process(self, containers):

        if self._show_version_dialog(containers):
            super().process(containers)
