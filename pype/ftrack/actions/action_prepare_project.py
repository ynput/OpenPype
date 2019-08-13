import os
import json

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from pypeapp import config
from pype.ftrack.lib import get_avalon_attr


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
    icon = '{}/ftrack/action_icons/PrepareProject.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

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

        self.log.debug("Loading custom attributes")
        cust_attrs, hier_cust_attrs = get_avalon_attr(session, True)
        project_defaults = config.get_presets().get("ftrack", {}).get(
            "project_defaults", {}
        )

        self.log.debug("Preparing data which will be shown")
        attributes_to_set = {}
        for attr in hier_cust_attrs:
            key = attr["key"]
            attributes_to_set[key] = {
                "label": attr["label"],
                "object": attr,
                "default": project_defaults.get(key)
            }

        for attr in cust_attrs:
            if attr["entity_type"].lower() != "show":
                continue
            key = attr["key"]
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
        self.log.debug("Preparing interface for keys: \"{}\"".format(
            str([key for key in attributes_to_set])
        ))

        title = "Set Attribute values"
        items = []
        multiselect_enumerators = []

        # This item will be last (before enumerators)
        # - sets value of auto synchronization
        auto_sync_name = "avalon_auto_sync"
        auto_sync_item = {
            "name": auto_sync_name,
            "type": "boolean",
            "value": project_defaults.get(auto_sync_name, False),
            "label": "AutoSync to Avalon"
        }

        item_splitter = {'type': 'label', 'value': '---'}

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
                    multiselect_enumerators.append(item_splitter)

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
                            if (
                                isinstance(default, list) or
                                isinstance(default, tuple)
                            ):
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

        # Add autosync attribute
        items.append(auto_sync_item)

        # Add enumerator items at the end
        for item in multiselect_enumerators:
            items.append(item)

        return {
            'items': items,
            'title': title
        }

    def launch(self, session, entities, event):
        if not event['data'].get('values', {}):
            return

        in_data = event['data']['values']
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

        return True


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    PrepareProject(session, plugins_presets).register()
