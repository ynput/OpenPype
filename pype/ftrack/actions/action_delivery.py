import os
import copy
import shutil

import clique
from bson.objectid import ObjectId
from avalon import pipeline
from avalon.vendor import filelink
from avalon.tools.libraryloader.io_nonsingleton import DbConnector

from pypeapp import Anatomy
from pype.ftrack import BaseAction
from pype.ftrack.lib.avalon_sync import CustAttrIdKey


class Delivery(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = "delivery.action"
    #: Action label.
    label = "Delivery"
    #: Action description.
    description = "Deliver data to client"
    #: roles that are allowed to register this action
    role_list = ["Pypeclub", "Administrator", "Project manager"]
    # icon = '{}/ftrack/action_icons/TestAction.svg'.format(
    #     os.environ.get('PYPE_STATICS_SERVER', '')
    # )

    db_con = DbConnector()

    def discover(self, session, entities, event):
        ''' Validation '''
        for entity in entities:
            if entity.entity_type.lower() == "assetversion":
                return True

        return False

    def interface(self, session, entities, event):
        if event["data"].get("values", {}):
            return

        title = "Delivery data to Client"

        items = []
        item_splitter = {"type": "label", "value": "---"}

        # Prepare component names for processing
        components = None
        project = None
        for entity in entities:
            if project is None:
                project_id = None
                for ent_info in entity["link"]:
                    if ent_info["type"].lower() == "project":
                        project_id = ent_info["id"]
                        break

                if project_id is None:
                    project = entity["asset"]["parent"]["project"]
                else:
                    project = session.query((
                        "select id, full_name from Project where id is \"{}\""
                    ).format(project_id)).one()

            _components = set(
                [component["name"] for component in entity["components"]]
            )
            if components is None:
                components = _components
                continue

            components = components.intersection(_components)
            if not components:
                break

        project_name = project["full_name"]
        items.append({
            "type": "hidden",
            "name": "__project_name__",
            "value": project_name
        })

        # Prpeare anatomy data
        anatomy = Anatomy(project_name)
        new_anatomies = []
        first = None
        for key in (anatomy.templates.get("delivery") or {}):
            new_anatomies.append({
                "label": key,
                "value": key
            })
            if first is None:
                first = key

        skipped = False
        # Add message if there are any common components
        if not components or not new_anatomies:
            skipped = True
            items.append({
                "type": "label",
                "value": "<h1>Something went wrong:</h1>"
            })

        items.append({
            "type": "hidden",
            "name": "__skipped__",
            "value": skipped
        })

        if not components:
            if len(entities) == 1:
                items.append({
                    "type": "label",
                    "value": (
                        "- Selected entity doesn't have components to deliver."
                    )
                })
            else:
                items.append({
                    "type": "label",
                    "value": (
                        "- Selected entities don't have common components."
                    )
                })

        # Add message if delivery anatomies are not set
        if not new_anatomies:
            items.append({
                "type": "label",
                "value": (
                    "- `\"delivery\"` anatomy key is not set in config."
                )
            })

        # Skip if there are any data shortcomings
        if skipped:
            return {
                "items": items,
                "title": title
            }

        items.append({
            "value": "<h1>Choose Components to deliver</h1>",
            "type": "label"
        })

        for component in components:
            items.append({
                "type": "boolean",
                "value": False,
                "label": component,
                "name": component
            })

        items.append(item_splitter)

        items.append({
            "value": "<h2>Location for delivery</h2>",
            "type": "label"
        })

        items.append({
            "type": "text",
            "name": "__location_path__",
            "empty_text": "Type location path here..."
        })

        items.append(item_splitter)

        items.append({
            "value": "<h2>Anatomy of delivery files</h2>",
            "type": "label"
        })

        items.append({
            "type": "label",
            "value": (
                "<p><i>NOTE: These can be set in Anatomy.yaml"
                " within `delivery` key.</i></p>"
            )
        })

        items.append({
            "type": "enumerator",
            "name": "__new_anatomies__",
            "data": new_anatomies,
            "value": first
        })

        return {
            "items": items,
            "title": title
        }

    def launch(self, session, entities, event):
        if "values" not in event["data"]:
            return

        values = event["data"]["values"]
        skipped = values.pop("__skipped__")
        if skipped:
            return None

        component_names = []
        location_path = values.pop("__location_path__")
        anatomy_name = values.pop("__new_anatomies__")
        project_name = values.pop("__project_name__")

        for key, value in values.items():
            if value is True:
                component_names.append(key)

        if not component_names:
            return None

        location_path = os.path.normpath(location_path.strip())
        if location_path and not os.path.exists(location_path):
            return {
                "success": False,
                "message": (
                    "Entered location path does not exists. \"{}\""
                ).format(location_path)
            }

        self.db_con.install()
        self.db_con.Session["AVALON_PROJECT"] = project_name

        components = []
        repres_to_deliver = []
        for entity in entities:
            asset = entity["asset"]
            subset_name = asset["name"]
            version = entity["version"]

            parent = asset["parent"]
            parent_mongo_id = parent["custom_attributes"].get(CustAttrIdKey)
            if not parent_mongo_id:
                # TODO log error (much better)
                self.log.warning((
                    "Seems like entity <{}> is not synchronized to avalon"
                ).format(parent["name"]))
                continue

            parent_mongo_id = ObjectId(parent_mongo_id)
            subset_ent = self.db_con.find_one({
                "type": "subset",
                "parent": parent_mongo_id,
                "name": subset_name
            })

            version_ent = self.db_con.find_one({
                "type": "version",
                "name": version,
                "parent": subset_ent["_id"]
            })

            repre_ents = self.db_con.find({
                "type": "representation",
                "parent": version_ent["_id"]
            })

            repres_by_name = {}
            for repre in repre_ents:
                repre_name = repre["name"]
                repres_by_name[repre_name] = repre

            for component in entity["components"]:
                comp_name = component["name"]
                if comp_name not in component_names:
                    continue

                repre = repres_by_name.get(comp_name)
                repres_to_deliver.append(repre)

        src_dst_files = {}
        anatomy = Anatomy(project_name)
        for repre in repres_to_deliver:
            # Get destination repre path
            anatomy_data = copy.deepcopy(repre["context"])
            if location_path:
                anatomy_data["root"] = location_path
            else:
                anatomy_data["root"] = pipeline.registered_root()

            # Get source repre path
            repre_path = self.path_from_represenation(repre)
            # TODO add backup solution where root of path from component
            # is repalced with AVALON_PROJECTS root

            if repre_path and os.path.exists(repre_path):
                self.process_single_file(
                    repre_path, anatomy, anatomy_name, anatomy_data
                )

            else:
                self.process_sequence(
                    repre_path, anatomy, anatomy_name, anatomy_data
                )

        self.db_con.uninstall()

    def process_single_file(
        self, repre_path, anatomy, anatomy_name, anatomy_data
    ):
        anatomy_filled = anatomy.format(anatomy_data)
        delivery_path = anatomy_filled.get("delivery", {}).get(anatomy_name)
        if not delivery_path:
            # TODO log error! - missing keys in anatomy
            return

        delivery_folder = os.path.dirname(delivery_path)
        if not os.path.exists(delivery_folder):
            os.makedirs(delivery_folder)

        self.copy_file(repre_path, delivery_path)

    def process_sequence(
        self, repre_path, anatomy, anatomy_name, anatomy_data
    ):
        dir_path, file_name = os.path.split(repre_path)
        if not os.path.exists(dir_path):
            # TODO log if folder don't exist
            return

        base_name, ext = os.path.splitext(file_name)
        file_name_items = None
        if "#" in base_name:
            file_name_items = [part for part in base_name.split("#") if part]

        elif "%" in base_name:
            file_name_items = base_name.split("%")

        if not file_name_items:
            # TODO log if file does not exists
            return

        src_collections, remainder = clique.assemble(os.listdir(dir_path))
        src_collection = None
        for col in src_collections:
            if col.tail != ext:
                continue

            # skip if collection don't have same basename
            if not col.head.startswith(file_name_items[0]):
                continue

            src_collection = col
            break

        if src_collection is None:
            # TODO log error!
            return

        anatomy_data["frame"] = "{frame}"
        anatomy_filled = anatomy.format(anatomy_data)
        delivery_path = anatomy_filled.get("delivery", {}).get(anatomy_name)
        if not delivery_path:
            # TODO log error! - missing keys in anatomy
            return

        delivery_folder = os.path.dirname(delivery_path)
        dst_head, dst_tail = delivery_path.split("{frame}")
        dst_padding = src_collection.padding
        dst_collection = clique.Collection(
            head=dst_head,
            tail=dst_tail,
            padding=dst_padding
        )

        if not os.path.exists(delivery_folder):
            os.makedirs(delivery_folder)

        src_head = src_collection.head
        src_tail = src_collection.tail
        for index in src_collection.indexes:
            src_padding = src_collection.format("{padding}") % index
            src_file_name = "{}{}{}".format(src_head, src_padding, src_tail)

            dst_padding = dst_collection.format("{padding}") % index
            dst_file_name = "{}{}{}".format(dst_head, dst_padding, dst_tail)

            self.copy_file(src, dst)

    def path_from_represenation(self, representation):
        try:
            template = representation["data"]["template"]

        except KeyError:
            return None

        try:
            context = representation["context"]
            context["root"] = os.environ.get("AVALON_PROJECTS") or ""
            path = pipeline.format_template_with_optional_keys(
                context, template
            )

        except KeyError:
            # Template references unavailable data
            return None

        if os.path.exists(path):
            return os.path.normpath(path)

    def copy_file(self, src_path, dst_path):
        try:
            filelink.create(
                src_path,
                dst_path,
                filelink.HARDLINK
            )
        except OSError:
            shutil.copyfile(src_path, dst_path)

def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    Delivery(session, plugins_presets).register()
