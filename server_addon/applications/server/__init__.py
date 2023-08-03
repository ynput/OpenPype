import os
import json
import copy

from ayon_server.addons import BaseServerAddon, AddonLibrary
from ayon_server.lib.postgres import Postgres

from .version import __version__
from .settings import ApplicationsAddonSettings, DEFAULT_VALUES

try:
    import semver
except ImportError:
    semver = None


def sort_versions(addon_versions, reverse=False):
    if semver is None:
        for addon_version in sorted(addon_versions, reverse=reverse):
            yield addon_version
        return

    version_objs = []
    invalid_versions = []
    for addon_version in addon_versions:
        try:
            version_objs.append(
                (addon_version, semver.VersionInfo.parse(addon_version))
            )
        except ValueError:
            invalid_versions.append(addon_version)

    valid_versions = [
        addon_version
        for addon_version, _ in sorted(version_objs, key=lambda x: x[1])
    ]
    sorted_versions = list(sorted(invalid_versions)) + valid_versions
    if reverse:
        sorted_versions = reversed(sorted_versions)
    for addon_version in sorted_versions:
        yield addon_version


def merge_groups(output, new_groups):
    groups_by_name = {
        o_group["name"]: o_group
        for o_group in output
    }
    extend_groups = []
    for new_group in new_groups:
        group_name = new_group["name"]
        if group_name not in groups_by_name:
            extend_groups.append(new_group)
            continue
        existing_group = groups_by_name[group_name]
        existing_variants = existing_group["variants"]
        existing_variants_by_name = {
            variant["name"]: variant
            for variant in existing_variants
        }
        for new_variant in new_group["variants"]:
            if new_variant["name"] not in existing_variants_by_name:
                existing_variants.append(new_variant)

    output.extend(extend_groups)


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

    return [
        {"value": full_name, "label": label_by_name[full_name]}
        for full_name in sorted(label_by_name)
    ]


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

    async def pre_setup(self):
        """Make sure older version of addon use the new way of attributes."""

        instance = AddonLibrary.getinstance()
        app_defs = instance.data.get(self.name)
        old_addon = app_defs.get("0.1.0")
        if old_addon is not None:
            # Override 'create_applications_attribute' for older versions
            #   - avoid infinite server restart loop
            old_addon.create_applications_attribute = (
                self.create_applications_attribute
            )

    async def setup(self):
        need_restart = await self.create_applications_attribute()
        if need_restart:
            self.request_server_restart()

    async def create_applications_attribute(self) -> bool:
        """Make sure there are required attributes which ftrack addon needs.

        Returns:
            bool: 'True' if an attribute was created or updated.
        """

        instance = AddonLibrary.getinstance()
        app_defs = instance.data.get(self.name)
        all_applications = []
        all_tools = []
        for addon_version in sort_versions(
            app_defs.versions.keys(), reverse=True
        ):
            addon = app_defs.versions[addon_version]
            for variant in ("production", "staging"):
                settings_model = await addon.get_studio_settings(variant)
                studio_settings = settings_model.dict()
                application_settings = studio_settings["applications"]
                app_groups = application_settings.pop("additional_apps")
                for group_name, value in application_settings.items():
                    value["name"] = group_name
                    app_groups.append(value)
                merge_groups(all_applications, app_groups)
                merge_groups(all_tools, studio_settings["tool_groups"])

        query = "SELECT name, position, scope, data from public.attributes"

        apps_attrib_name = "applications"
        tools_attrib_name = "tools"

        apps_enum = get_enum_items_from_groups(all_applications)
        tools_enum = get_enum_items_from_groups(all_tools)
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
