import os
import copy
import shutil
import collections

import clique
from bson.objectid import ObjectId

from avalon import pipeline
from avalon.vendor import filelink

from pype.api import Anatomy
from pype.modules.ftrack.lib import BaseAction, statics_icon
from pype.modules.ftrack.lib.avalon_sync import CustAttrIdKey
from pype.modules.ftrack.lib.io_nonsingleton import DbConnector


class Delivery(BaseAction):

    identifier = "delivery.action"
    label = "Delivery"
    description = "Deliver data to client"
    role_list = ["Pypeclub", "Administrator", "Project manager"]
    icon = statics_icon("ftrack", "action_icons", "Delivery.svg")

    db_con = DbConnector()

    def discover(self, session, entities, event):
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
            "type": "label",
            "value": (
                "<i>NOTE: It is possible to replace `root` key in anatomy.</i>"
            )
        })

        items.append({
            "type": "text",
            "name": "__location_path__",
            "empty_text": "Type location path here...(Optional)"
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

        self.report_items = collections.defaultdict(list)

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
            return {
                "success": True,
                "message": "Not selected components to deliver."
            }

        location_path = location_path.strip()
        if location_path:
            location_path = os.path.normpath(location_path)
            if not os.path.exists(location_path):
                return {
                    "success": False,
                    "message": (
                        "Entered location path does not exists. \"{}\""
                    ).format(location_path)
                }

        self.db_con.install()
        self.db_con.Session["AVALON_PROJECT"] = project_name

        repres_to_deliver = []
        for entity in entities:
            asset = entity["asset"]
            subset_name = asset["name"]
            version = entity["version"]

            parent = asset["parent"]
            parent_mongo_id = parent["custom_attributes"].get(CustAttrIdKey)
            if parent_mongo_id:
                parent_mongo_id = ObjectId(parent_mongo_id)
            else:
                asset_ent = self.db_con.find_one({
                    "type": "asset",
                    "data.ftrackId": parent["id"]
                })
                if not asset_ent:
                    ent_path = "/".join(
                        [ent["name"] for ent in parent["link"]]
                    )
                    msg = "Not synchronized entities to avalon"
                    self.report_items[msg].append(ent_path)
                    self.log.warning("{} <{}>".format(msg, ent_path))
                    continue

                parent_mongo_id = asset_ent["_id"]

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

        anatomy = Anatomy(project_name)
        for repre in repres_to_deliver:
            # Get destination repre path
            anatomy_data = copy.deepcopy(repre["context"])
            anatomy_filled = anatomy.format_all(anatomy_data)
            test_path = anatomy_filled["delivery"][anatomy_name]

            if not test_path.solved:
                msg = (
                    "Missing keys in Representation's context"
                    " for anatomy template \"{}\"."
                ).format(anatomy_name)

                if test_path.missing_keys:
                    keys = ", ".join(test_path.missing_keys)
                    sub_msg = (
                        "Representation: {}<br>- Missing keys: \"{}\"<br>"
                    ).format(str(repre["_id"]), keys)

                if test_path.invalid_types:
                    items = []
                    for key, value in test_path.invalid_types.items():
                        items.append("\"{}\" {}".format(key, str(value)))

                    keys = ", ".join(items)
                    sub_msg = (
                        "Representation: {}<br>"
                        "- Invalid value DataType: \"{}\"<br>"
                    ).format(str(repre["_id"]), keys)

                self.report_items[msg].append(sub_msg)
                self.log.warning(
                    "{} Representation: \"{}\" Filled: <{}>".format(
                        msg, str(repre["_id"]), str(test_path)
                    )
                )
                continue

            # Get source repre path
            frame = repre['context'].get('frame')

            if frame:
                repre["context"]["frame"] = len(str(frame)) * "#"

            repre_path = self.path_from_represenation(repre, anatomy)
            # TODO add backup solution where root of path from component
            # is repalced with root
            if not frame:
                self.process_single_file(
                    repre_path, anatomy, anatomy_name, anatomy_data
                )

            else:
                self.process_sequence(
                    repre_path, anatomy, anatomy_name, anatomy_data
                )

        self.db_con.uninstall()

        return self.report()

    def process_single_file(
        self, repre_path, anatomy, anatomy_name, anatomy_data
    ):
        anatomy_filled = anatomy.format(anatomy_data)
        delivery_path = anatomy_filled["delivery"][anatomy_name]
        delivery_folder = os.path.dirname(delivery_path)
        if not os.path.exists(delivery_folder):
            os.makedirs(delivery_folder)

        self.copy_file(repre_path, delivery_path)

    def process_sequence(
        self, repre_path, anatomy, anatomy_name, anatomy_data
    ):
        dir_path, file_name = os.path.split(str(repre_path))

        base_name, ext = os.path.splitext(file_name)
        file_name_items = None
        if "#" in base_name:
            file_name_items = [part for part in base_name.split("#") if part]

        elif "%" in base_name:
            file_name_items = base_name.split("%")

        if not file_name_items:
            msg = "Source file was not found"
            self.report_items[msg].append(repre_path)
            self.log.warning("{} <{}>".format(msg, repre_path))
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
            msg = "Source collection of files was not found"
            self.report_items[msg].append(repre_path)
            self.log.warning("{} <{}>".format(msg, repre_path))
            return

        frame_indicator = "@####@"

        anatomy_data["frame"] = frame_indicator
        anatomy_filled = anatomy.format(anatomy_data)

        delivery_path = anatomy_filled["delivery"][anatomy_name]
        print(delivery_path)
        delivery_folder = os.path.dirname(delivery_path)
        dst_head, dst_tail = delivery_path.split(frame_indicator)
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
            src = os.path.normpath(
                os.path.join(dir_path, src_file_name)
            )

            dst_padding = dst_collection.format("{padding}") % index
            dst = "{}{}{}".format(dst_head, dst_padding, dst_tail)

            self.copy_file(src, dst)

    def path_from_represenation(self, representation, anatomy):
        try:
            template = representation["data"]["template"]

        except KeyError:
            return None

        try:
            context = representation["context"]
            context["root"] = anatomy.roots
            path = pipeline.format_template_with_optional_keys(
                context, template
            )

        except KeyError:
            # Template references unavailable data
            return None

        return os.path.normpath(path)

    def copy_file(self, src_path, dst_path):
        if os.path.exists(dst_path):
            return
        try:
            filelink.create(
                src_path,
                dst_path,
                filelink.HARDLINK
            )
        except OSError:
            shutil.copyfile(src_path, dst_path)

    def report(self):
        items = []
        title = "Delivery report"
        for msg, _items in self.report_items.items():
            if not _items:
                continue

            if items:
                items.append({"type": "label", "value": "---"})

            items.append({
                "type": "label",
                "value": "# {}".format(msg)
            })
            if not isinstance(_items, (list, tuple)):
                _items = [_items]
            __items = []
            for item in _items:
                __items.append(str(item))

            items.append({
                "type": "label",
                "value": '<p>{}</p>'.format("<br>".join(__items))
            })

        if not items:
            return {
                "success": True,
                "message": "Delivery Finished"
            }

        return {
            "items": items,
            "title": title,
            "success": False,
            "message": "Delivery Finished"
        }


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    Delivery(session, plugins_presets).register()
