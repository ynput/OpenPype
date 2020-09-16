import os
import json

from pype.modules.ftrack.lib import BaseAction, statics_icon
from pype.api import config, Anatomy, project_overrides_dir_path
from pype.modules.ftrack.lib.avalon_sync import get_pype_attr


class PrepareProject(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'prepare.project'
    #: Action label.
    label = 'Prepare Project'
    #: Action description.
    description = 'Set basic attributes on the project'
    #: roles that are allowed to register this action
    role_list = ["Pypeclub", "Administrator", "Project manager"]
    icon = statics_icon("ftrack", "action_icons", "PrepareProject.svg")

    # Key to store info about trigerring create folder structure
    create_project_structure_key = "create_folder_structure"
    item_splitter = {'type': 'label', 'value': '---'}

    def discover(self, session, entities, event):
        ''' Validation '''
        if len(entities) != 1:
            return False

        if entities[0].entity_type.lower() != "project":
            return False

        return True

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        # Inform user that this may take a while
        self.show_message(event, "Preparing data... Please wait", True)
        self.log.debug("Preparing data which will be shown")

        self.log.debug("Loading custom attributes")

        project_name = entities[0]["full_name"]

        project_defaults = (
            config.get_presets(project_name)
            .get("ftrack", {})
            .get("project_defaults", {})
        )

        anatomy = Anatomy(project_name)
        if not anatomy.roots:
            return {
                "success": False,
                "message": (
                    "Have issues with loading Roots for project \"{}\"."
                ).format(anatomy.project_name)
            }

        root_items = self.prepare_root_items(anatomy)

        ca_items, multiselect_enumerators = (
            self.prepare_custom_attribute_items(project_defaults)
        )

        self.log.debug("Heavy items are ready. Preparing last items group.")

        title = "Prepare Project"
        items = []

        # Add root items
        items.extend(root_items)
        items.append(self.item_splitter)

        # Ask if want to trigger Action Create Folder Structure
        items.append({
            "type": "label",
            "value": "<h3>Want to create basic Folder Structure?</h3>"
        })
        items.append({
            "name": self.create_project_structure_key,
            "type": "boolean",
            "value": False,
            "label": "Check if Yes"
        })

        items.append(self.item_splitter)
        items.append({
            "type": "label",
            "value": "<h3>Set basic Attributes:</h3>"
        })

        items.extend(ca_items)

        # This item will be last (before enumerators)
        # - sets value of auto synchronization
        auto_sync_name = "avalon_auto_sync"
        auto_sync_item = {
            "name": auto_sync_name,
            "type": "boolean",
            "value": project_defaults.get(auto_sync_name, False),
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

    def prepare_root_items(self, anatomy):
        root_items = []
        self.log.debug("Root items preparation begins.")

        root_names = anatomy.root_names()
        roots = anatomy.roots

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

        default_roots = anatomy.roots
        while isinstance(default_roots, dict):
            key = tuple(default_roots.keys())[0]
            default_roots = default_roots[key]

        empty_text = "Enter root path here..."

        # Root names is None when anatomy templates contain "{root}"
        all_platforms = ["windows", "linux", "darwin"]
        if root_names is None:
            root_items.append(self.item_splitter)
            # find first possible key
            for platform in all_platforms:
                value = default_roots.raw_data.get(platform) or ""
                root_items.append({
                    "label": platform,
                    "name": "__root__{}".format(platform),
                    "type": "text",
                    "value": value,
                    "empty_text": empty_text
                })
            return root_items

        root_name_data = {}
        missing_roots = []
        for root_name in root_names:
            root_name_data[root_name] = {}
            if not isinstance(roots, dict):
                missing_roots.append(root_name)
                continue

            root_item = roots.get(root_name)
            if not root_item:
                missing_roots.append(root_name)
                continue

            for platform in all_platforms:
                root_name_data[root_name][platform] = (
                    root_item.raw_data.get(platform) or ""
                )

        if missing_roots:
            default_values = {}
            for platform in all_platforms:
                default_values[platform] = (
                    default_roots.raw_data.get(platform) or ""
                )

            for root_name in missing_roots:
                root_name_data[root_name] = default_values

        root_names = list(root_name_data.keys())
        root_items.append({
            "type": "hidden",
            "name": "__rootnames__",
            "value": json.dumps(root_names)
        })

        for root_name, values in root_name_data.items():
            root_items.append(self.item_splitter)
            root_items.append({
                "type": "label",
                "value": "Root: \"{}\"".format(root_name)
            })
            for platform, value in values.items():
                root_items.append({
                    "label": platform,
                    "name": "__root__{}{}".format(root_name, platform),
                    "type": "text",
                    "value": value,
                    "empty_text": empty_text
                })

        self.log.debug("Root items preparation ended.")
        return root_items

    def _attributes_to_set(self, project_defaults):
        attributes_to_set = {}

        cust_attrs, hier_cust_attrs = get_pype_attr(self.session, True)

        for attr in hier_cust_attrs:
            key = attr["key"]
            if key.startswith("avalon_"):
                continue
            attributes_to_set[key] = {
                "label": attr["label"],
                "object": attr,
                "default": project_defaults.get(key)
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
                "default": project_defaults.get(key)
            }

        # Sort by label
        attributes_to_set = dict(sorted(
            attributes_to_set.items(),
            key=lambda x: x[1]["label"]
        ))
        return attributes_to_set

    def prepare_custom_attribute_items(self, project_defaults):
        items = []
        multiselect_enumerators = []
        attributes_to_set = self._attributes_to_set(project_defaults)

        self.log.debug("Preparing interface for keys: \"{}\"".format(
            str([key for key in attributes_to_set])
        ))

        for key, in_data in attributes_to_set.items():
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
                        "value": in_data["label"]
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
        if not event['data'].get('values', {}):
            return

        in_data = event['data']['values']

        root_values = {}
        root_key = "__root__"
        for key in tuple(in_data.keys()):
            if key.startswith(root_key):
                _key = key[len(root_key):]
                root_values[_key] = in_data.pop(key)

        root_names = in_data.pop("__rootnames__", None)
        root_data = {}
        if root_names:
            for root_name in json.loads(root_names):
                root_data[root_name] = {}
                for key, value in tuple(root_values.items()):
                    if key.startswith(root_name):
                        _key = key[len(root_name):]
                        root_data[root_name][_key] = value

        else:
            for key, value in root_values.items():
                root_data[key] = value

        project_name = entities[0]["full_name"]
        anatomy = Anatomy(project_name)
        anatomy.templates_obj.save_project_overrides(project_name)
        anatomy.roots_obj.save_project_overrides(
            project_name, root_data, override=True
        )
        anatomy.reset()

        # pop out info about creating project structure
        create_proj_struct = in_data.pop(self.create_project_structure_key)

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

        self.log.debug("Setting Custom Attribute values:")
        entity = entities[0]
        for key, value in in_data.items():
            entity["custom_attributes"][key] = value
            self.log.debug("- Key \"{}\" set to \"{}\"".format(key, value))

        session.commit()

        # Create project structure
        self.create_project_specific_config(entities[0]["full_name"], in_data)

        # Trigger Create Project Structure action
        if create_proj_struct is True:
            self.trigger_action("create.project.structure", event)

        return True

    def create_project_specific_config(self, project_name, json_data):
        self.log.debug("*** Creating project specifig configs ***")
        project_specific_path = project_overrides_dir_path(project_name)
        if not os.path.exists(project_specific_path):
            os.makedirs(project_specific_path)
            self.log.debug((
                "Project specific config folder for project \"{}\" created."
            ).format(project_name))

        # Presets ####################################
        self.log.debug("--- Processing Presets Begins: ---")

        project_defaults_dir = os.path.normpath(os.path.join(
            project_specific_path, "presets", "ftrack"
        ))
        project_defaults_path = os.path.normpath(os.path.join(
            project_defaults_dir, "project_defaults.json"
        ))
        # Create folder if not exist
        if not os.path.exists(project_defaults_dir):
            self.log.debug("Creating Ftrack Presets folder: \"{}\"".format(
                project_defaults_dir
            ))
            os.makedirs(project_defaults_dir)

        with open(project_defaults_path, 'w') as file_stream:
            json.dump(json_data, file_stream, indent=4)

        self.log.debug("*** Creating project specifig configs Finished ***")


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''
    PrepareProject(session, plugins_presets).register()
