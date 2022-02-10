import json

from avalon.api import AvalonMongoDB
from openpype.api import ProjectSettings
from openpype.lib import create_project
from openpype.settings import SaveWarningExc

from openpype_modules.ftrack.lib import (
    ServerAction,
    get_openpype_attr,
    CUST_ATTR_AUTO_SYNC
)


class PrepareProjectServer(ServerAction):
    """Prepare project attributes in Anatomy."""

    identifier = "prepare.project.server"
    label = "OpenPype Admin"
    variant = "- Prepare Project (Server)"
    description = "Set basic attributes on the project"

    settings_key = "prepare_project"

    role_list = ["Pypeclub", "Administrator", "Project Manager"]

    settings_key = "prepare_project"

    item_splitter = {"type": "label", "value": "---"}
    _keys_order = (
        "fps",
        "frameStart",
        "frameEnd",
        "handleStart",
        "handleEnd",
        "clipIn",
        "clipOut",
        "resolutionHeight",
        "resolutionWidth",
        "pixelAspect",
        "applications",
        "tools_env",
        "library_project",
    )

    def discover(self, session, entities, event):
        """Show only on project."""
        if (
            len(entities) != 1
            or entities[0].entity_type.lower() != "project"
        ):
            return False

        return self.valid_roles(session, entities, event)

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        # Inform user that this may take a while
        self.show_message(event, "Preparing data... Please wait", True)
        self.log.debug("Preparing data which will be shown")

        self.log.debug("Loading custom attributes")

        project_entity = entities[0]
        project_name = project_entity["full_name"]

        project_settings = ProjectSettings(project_name)

        project_anatom_settings = project_settings["project_anatomy"]
        root_items = self.prepare_root_items(project_anatom_settings)

        ca_items, multiselect_enumerators = (
            self.prepare_custom_attribute_items(project_anatom_settings)
        )

        self.log.debug("Heavy items are ready. Preparing last items group.")

        title = "Prepare Project"
        items = []

        # Add root items
        items.extend(root_items)

        items.append(self.item_splitter)
        items.append({
            "type": "label",
            "value": "<h3>Set basic Attributes:</h3>"
        })

        items.extend(ca_items)

        # This item will be last before enumerators
        # Set value of auto synchronization
        auto_sync_value = project_entity["custom_attributes"].get(
            CUST_ATTR_AUTO_SYNC, False
        )
        auto_sync_item = {
            "name": CUST_ATTR_AUTO_SYNC,
            "type": "boolean",
            "value": auto_sync_value,
            "label": "AutoSync to Avalon"
        }
        # Add autosync attribute
        items.append(auto_sync_item)

        # Add enumerator items at the end
        for item in multiselect_enumerators:
            items.append(item)

        return {
            "items": items,
            "title": title
        }

    def prepare_root_items(self, project_anatom_settings):
        self.log.debug("Root items preparation begins.")

        root_items = []
        root_items.append({
            "type": "label",
            "value": "<h3>Check your Project root settings</h3>"
        })
        root_items.append({
            "type": "label",
            "value": (
                "<p><i>NOTE: Roots are <b>crutial</b> for path filling"
                " (and creating folder structure).</i></p>"
            )
        })
        root_items.append({
            "type": "label",
            "value": (
                "<p><i>WARNING: Do not change roots on running project,"
                " that <b>will cause workflow issues</b>.</i></p>"
            )
        })

        empty_text = "Enter root path here..."

        roots_entity = project_anatom_settings["roots"]
        for root_name, root_entity in roots_entity.items():
            root_items.append(self.item_splitter)
            root_items.append({
                "type": "label",
                "value": "Root: \"{}\"".format(root_name)
            })
            for platform_name, value_entity in root_entity.items():
                root_items.append({
                    "label": platform_name,
                    "name": "__root__{}__{}".format(root_name, platform_name),
                    "type": "text",
                    "value": value_entity.value,
                    "empty_text": empty_text
                })

        root_items.append({
            "type": "hidden",
            "name": "__rootnames__",
            "value": json.dumps(list(roots_entity.keys()))
        })

        self.log.debug("Root items preparation ended.")
        return root_items

    def _attributes_to_set(self, project_anatom_settings):
        attributes_to_set = {}

        attribute_values_by_key = {}
        for key, entity in project_anatom_settings["attributes"].items():
            attribute_values_by_key[key] = entity.value

        cust_attrs, hier_cust_attrs = get_openpype_attr(self.session, True)

        for attr in hier_cust_attrs:
            key = attr["key"]
            if key.startswith("avalon_"):
                continue
            attributes_to_set[key] = {
                "label": attr["label"],
                "object": attr,
                "default": attribute_values_by_key.get(key)
            }

        for attr in cust_attrs:
            if attr["entity_type"].lower() != "show":
                continue
            key = attr["key"]
            if key.startswith("avalon_"):
                continue
            attributes_to_set[key] = {
                "label": attr["label"],
                "object": attr,
                "default": attribute_values_by_key.get(key)
            }

        # Sort by label
        attributes_to_set = dict(sorted(
            attributes_to_set.items(),
            key=lambda x: x[1]["label"]
        ))
        return attributes_to_set

    def prepare_custom_attribute_items(self, project_anatom_settings):
        items = []
        multiselect_enumerators = []
        attributes_to_set = self._attributes_to_set(project_anatom_settings)

        self.log.debug("Preparing interface for keys: \"{}\"".format(
            str([key for key in attributes_to_set])
        ))

        attribute_keys = set(attributes_to_set.keys())
        keys_order = []
        for key in self._keys_order:
            if key in attribute_keys:
                keys_order.append(key)

        attribute_keys = attribute_keys - set(keys_order)
        for key in sorted(attribute_keys):
            keys_order.append(key)

        for key in keys_order:
            in_data = attributes_to_set[key]
            attr = in_data["object"]

            # initial item definition
            item = {
                "name": key,
                "label": in_data["label"]
            }

            # cust attr type - may have different visualization
            type_name = attr["type"]["name"].lower()
            easy_types = ["text", "boolean", "date", "number"]

            easy_type = False
            if type_name in easy_types:
                easy_type = True

            elif type_name == "enumerator":

                attr_config = json.loads(attr["config"])
                attr_config_data = json.loads(attr_config["data"])

                if attr_config["multiSelect"] is True:
                    multiselect_enumerators.append(self.item_splitter)
                    multiselect_enumerators.append({
                        "type": "label",
                        "value": "<h3>{}</h3>".format(in_data["label"])
                    })

                    default = in_data["default"]
                    names = []
                    for option in sorted(
                        attr_config_data, key=lambda x: x["menu"]
                    ):
                        name = option["value"]
                        new_name = "__{}__{}".format(key, name)
                        names.append(new_name)
                        item = {
                            "name": new_name,
                            "type": "boolean",
                            "label": "- {}".format(option["menu"])
                        }
                        if default:
                            if isinstance(default, (list, tuple)):
                                if name in default:
                                    item["value"] = True
                            else:
                                if name == default:
                                    item["value"] = True

                        multiselect_enumerators.append(item)

                    multiselect_enumerators.append({
                        "type": "hidden",
                        "name": "__hidden__{}".format(key),
                        "value": json.dumps(names)
                    })
                else:
                    easy_type = True
                    item["data"] = attr_config_data

            else:
                self.log.warning((
                    "Custom attribute \"{}\" has type \"{}\"."
                    " I don't know how to handle"
                ).format(key, type_name))
                items.append({
                    "type": "label",
                    "value": (
                        "!!! Can't handle Custom attritubte type \"{}\""
                        " (key: \"{}\")"
                    ).format(type_name, key)
                })

            if easy_type:
                item["type"] = type_name

                # default value in interface
                default = in_data["default"]
                if default is not None:
                    item["value"] = default

                items.append(item)

        return items, multiselect_enumerators

    def launch(self, session, entities, event):
        in_data = event["data"].get("values")
        if not in_data:
            return

        root_values = {}
        root_key = "__root__"
        for key in tuple(in_data.keys()):
            if key.startswith(root_key):
                _key = key[len(root_key):]
                root_values[_key] = in_data.pop(key)

        root_names = in_data.pop("__rootnames__", None)
        root_data = {}
        for root_name in json.loads(root_names):
            root_data[root_name] = {}
            for key, value in tuple(root_values.items()):
                prefix = "{}__".format(root_name)
                if not key.startswith(prefix):
                    continue

                _key = key[len(prefix):]
                root_data[root_name][_key] = value

        # Find hidden items for multiselect enumerators
        keys_to_process = []
        for key in in_data:
            if key.startswith("__hidden__"):
                keys_to_process.append(key)

        self.log.debug("Preparing data for Multiselect Enumerators")
        enumerators = {}
        for key in keys_to_process:
            new_key = key.replace("__hidden__", "")
            enumerator_items = in_data.pop(key)
            enumerators[new_key] = json.loads(enumerator_items)

        # find values set for multiselect enumerator
        for key, enumerator_items in enumerators.items():
            in_data[key] = []

            name = "__{}__".format(key)

            for item in enumerator_items:
                value = in_data.pop(item)
                if value is True:
                    new_key = item.replace(name, "")
                    in_data[key].append(new_key)

        self.log.debug("Setting Custom Attribute values")

        project_entity = entities[0]
        project_name = project_entity["full_name"]

        # Try to find project document
        dbcon = AvalonMongoDB()
        dbcon.install()
        dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = dbcon.find_one({
            "type": "project"
        })
        # Create project if is not available
        # - creation is required to be able set project anatomy and attributes
        if not project_doc:
            project_code = project_entity["name"]
            self.log.info("Creating project \"{} [{}]\"".format(
                project_name, project_code
            ))
            create_project(project_name, project_code, dbcon=dbcon)

        dbcon.uninstall()

        project_settings = ProjectSettings(project_name)
        project_anatomy_settings = project_settings["project_anatomy"]
        project_anatomy_settings["roots"] = root_data

        custom_attribute_values = {}
        attributes_entity = project_anatomy_settings["attributes"]
        for key, value in in_data.items():
            if key not in attributes_entity:
                custom_attribute_values[key] = value
            else:
                attributes_entity[key] = value

        try:
            project_settings.save()
        except SaveWarningExc as exc:
            self.log.info("Few warnings happened during settings save:")
            for warning in exc.warnings:
                self.log.info(str(warning))

        # Change custom attributes on project
        if custom_attribute_values:
            for key, value in custom_attribute_values.items():
                project_entity["custom_attributes"][key] = value
                self.log.debug("- Key \"{}\" set to \"{}\"".format(key, value))
            session.commit()

        return True


def register(session):
    '''Register plugin. Called when used as an plugin.'''
    PrepareProjectServer(session).register()
