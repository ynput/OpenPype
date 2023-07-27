import os
import json
import copy

from ayon_server.addons import BaseServerAddon
from ayon_server.lib.postgres import Postgres

from .version import __version__
from .settings import ApplicationsAddonSettings, DEFAULT_VALUES


def get_enum_items_from_groups(groups):
    label_by_name = {}
    for group in groups:
        group_name = group["name"]
        group_label = group["label"] or group_name
        for variant in group["variants"]:
            variant_name = variant["name"]
            if not variant_name:
                continue
            variant_label = variant["label"] or variant_name
            full_name = f"{group_name}/{variant_name}"
            full_label = f"{group_label} {variant_label}"
            label_by_name[full_name] = full_label
    enum_items = []
    for full_name in sorted(label_by_name):
        enum_items.append(
            {"value": full_name, "label": label_by_name[full_name]}
        )
    return enum_items


class ApplicationsAddon(BaseServerAddon):
    name = "applications"
    title = "Applications"
    version = __version__
    settings_model = ApplicationsAddonSettings

    async def get_default_settings(self):
        applications_path = os.path.join(self.addon_dir, "applications.json")
        tools_path = os.path.join(self.addon_dir, "tools.json")
        default_values = copy.deepcopy(DEFAULT_VALUES)
        with open(applications_path, "r") as stream:
            default_values.update(json.load(stream))

        with open(tools_path, "r") as stream:
            default_values.update(json.load(stream))

        return self.get_settings_model()(**default_values)

    async def setup(self):
        need_restart = await self.create_applications_attribute()
        if need_restart:
            self.request_server_restart()

    async def create_applications_attribute(self) -> bool:
        """Make sure there are required attributes which ftrack addon needs.

        Returns:
            bool: 'True' if an attribute was created or updated.
        """

        settings_model = await self.get_studio_settings()
        studio_settings = settings_model.dict()
        applications = studio_settings["applications"]
        _applications = applications.pop("additional_apps")
        for name, value in applications.items():
            value["name"] = name
            _applications.append(value)

        query = "SELECT name, position, scope, data from public.attributes"

        apps_attrib_name = "applications"
        tools_attrib_name = "tools"

        apps_enum = get_enum_items_from_groups(_applications)
        tools_enum = get_enum_items_from_groups(studio_settings["tool_groups"])
        apps_attribute_data = {
            "type": "list_of_strings",
            "title": "Applications",
            "enum": apps_enum
        }
        tools_attribute_data = {
            "type": "list_of_strings",
            "title": "Tools",
            "enum": tools_enum
        }
        apps_scope = ["project"]
        tools_scope = ["project", "folder", "task"]

        apps_match_position = None
        apps_matches = False
        tools_match_position = None
        tools_matches = False
        position = 1
        async for row in Postgres.iterate(query):
            position += 1
            if row["name"] == apps_attrib_name:
                # Check if scope is matching ftrack addon requirements
                if (
                    set(row["scope"]) == set(apps_scope)
                    and row["data"].get("enum") == apps_enum
                ):
                    apps_matches = True
                apps_match_position = row["position"]

            elif row["name"] == tools_attrib_name:
                if (
                    set(row["scope"]) == set(tools_scope)
                    and row["data"].get("enum") == tools_enum
                ):
                    tools_matches = True
                tools_match_position = row["position"]

        if apps_matches and tools_matches:
            return False

        postgre_query = "\n".join((
            "INSERT INTO public.attributes",
            "    (name, position, scope, data)",
            "VALUES",
            "    ($1, $2, $3, $4)",
            "ON CONFLICT (name)",
            "DO UPDATE SET",
            "    scope = $3,",
            "    data = $4",
        ))
        if not apps_matches:
            # Reuse position from found attribute
            if apps_match_position is None:
                apps_match_position = position
                position += 1

            await Postgres.execute(
                postgre_query,
                apps_attrib_name,
                apps_match_position,
                apps_scope,
                apps_attribute_data,
            )

        if not tools_matches:
            if tools_match_position is None:
                tools_match_position = position
                position += 1

            await Postgres.execute(
                postgre_query,
                tools_attrib_name,
                tools_match_position,
                tools_scope,
                tools_attribute_data,
            )
        return True
