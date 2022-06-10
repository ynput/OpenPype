import os
import copy
import json
import collections

from bson.objectid import ObjectId

from openpype.api import Anatomy, config
from openpype_modules.ftrack.lib import BaseAction, statics_icon
from openpype_modules.ftrack.lib.avalon_sync import CUST_ATTR_ID_KEY
from openpype_modules.ftrack.lib.custom_attributes import (
    query_custom_attributes
)
from openpype.lib.delivery import (
    path_from_representation,
    get_format_dict,
    check_destination_path,
    process_single_file,
    process_sequence
)
from openpype.pipeline import AvalonMongoDB


class Delivery(BaseAction):

    identifier = "delivery.action"
    label = "Delivery"
    description = "Deliver data to client"
    role_list = ["Pypeclub", "Administrator", "Project manager"]
    icon = statics_icon("ftrack", "action_icons", "Delivery.svg")
    settings_key = "delivery_action"

    def __init__(self, *args, **kwargs):
        self.dbcon = AvalonMongoDB()

        super(Delivery, self).__init__(*args, **kwargs)

    def discover(self, session, entities, event):
        is_valid = False
        for entity in entities:
            if entity.entity_type.lower() in ("assetversion", "reviewsession"):
                is_valid = True
                break

        if is_valid:
            is_valid = self.valid_roles(session, entities, event)
        return is_valid

    def interface(self, session, entities, event):
        if event["data"].get("values", {}):
            return

        title = "Delivery data to Client"

        items = []
        item_splitter = {"type": "label", "value": "---"}

        project_entity = self.get_project_from_entity(entities[0])
        project_name = project_entity["full_name"]
        self.dbcon.install()
        self.dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = self.dbcon.find_one({"type": "project"}, {"name": True})
        if not project_doc:
            return {
                "success": False,
                "message": (
                    "Didn't found project \"{}\" in avalon."
                ).format(project_name)
            }

        repre_names = self._get_repre_names(session, entities)
        self.dbcon.uninstall()

        items.append({
            "type": "hidden",
            "name": "__project_name__",
            "value": project_name
        })

        # Prepare anatomy data
        anatomy = Anatomy(project_name)
        new_anatomies = []
        first = None
        for key, template in (anatomy.templates.get("delivery") or {}).items():
            # Use only keys with `{root}` or `{root[*]}` in value
            if isinstance(template, str) and "{root" in template:
                new_anatomies.append({
                    "label": key,
                    "value": key
                })
                if first is None:
                    first = key

        skipped = False
        # Add message if there are any common components
        if not repre_names or not new_anatomies:
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

        if not repre_names:
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

        for repre_name in repre_names:
            items.append({
                "type": "boolean",
                "value": False,
                "label": repre_name,
                "name": repre_name
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

    def _get_repre_names(self, session, entities):
        version_ids = self._get_interest_version_ids(session, entities)
        if not version_ids:
            return []
        repre_docs = self.dbcon.find({
            "type": "representation",
            "parent": {"$in": version_ids}
        })
        return list(sorted(repre_docs.distinct("name")))

    def _get_interest_version_ids(self, session, entities):
        # Extract AssetVersion entities
        asset_versions = self._extract_asset_versions(session, entities)
        # Prepare Asset ids
        asset_ids = {
            asset_version["asset_id"]
            for asset_version in asset_versions
        }
        # Query Asset entities
        assets = session.query((
            "select id, name, context_id from Asset where id in ({})"
        ).format(self.join_query_keys(asset_ids))).all()
        assets_by_id = {
            asset["id"]: asset
            for asset in assets
        }
        parent_ids = set()
        subset_names = set()
        version_nums = set()
        for asset_version in asset_versions:
            asset_id = asset_version["asset_id"]
            asset = assets_by_id[asset_id]

            parent_ids.add(asset["context_id"])
            subset_names.add(asset["name"])
            version_nums.add(asset_version["version"])

        asset_docs_by_ftrack_id = self._get_asset_docs(session, parent_ids)
        subset_docs = self._get_subset_docs(
            asset_docs_by_ftrack_id,
            subset_names,
            asset_versions,
            assets_by_id
        )
        version_docs = self._get_version_docs(
            asset_docs_by_ftrack_id,
            subset_docs,
            version_nums,
            asset_versions,
            assets_by_id
        )

        return [version_doc["_id"] for version_doc in version_docs]

    def _extract_asset_versions(self, session, entities):
        asset_version_ids = set()
        review_session_ids = set()
        for entity in entities:
            entity_type_low = entity.entity_type.lower()
            if entity_type_low == "assetversion":
                asset_version_ids.add(entity["id"])
            elif entity_type_low == "reviewsession":
                review_session_ids.add(entity["id"])

        for version_id in self._get_asset_version_ids_from_review_sessions(
            session, review_session_ids
        ):
            asset_version_ids.add(version_id)

        asset_versions = session.query((
            "select id, version, asset_id from AssetVersion where id in ({})"
        ).format(self.join_query_keys(asset_version_ids))).all()

        return asset_versions

    def _get_asset_version_ids_from_review_sessions(
        self, session, review_session_ids
    ):
        if not review_session_ids:
            return set()
        review_session_objects = session.query((
            "select version_id from ReviewSessionObject"
            " where review_session_id in ({})"
        ).format(self.join_query_keys(review_session_ids))).all()

        return {
            review_session_object["version_id"]
            for review_session_object in review_session_objects
        }

    def _get_version_docs(
        self,
        asset_docs_by_ftrack_id,
        subset_docs,
        version_nums,
        asset_versions,
        assets_by_id
    ):
        subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in subset_docs
        }
        version_docs = list(self.dbcon.find({
            "type": "version",
            "parent": {"$in": list(subset_docs_by_id.keys())},
            "name": {"$in": list(version_nums)}
        }))
        version_docs_by_parent_id = collections.defaultdict(dict)
        for version_doc in version_docs:
            subset_doc = subset_docs_by_id[version_doc["parent"]]

            asset_id = subset_doc["parent"]
            subset_name = subset_doc["name"]
            version = version_doc["name"]
            if version_docs_by_parent_id[asset_id].get(subset_name) is None:
                version_docs_by_parent_id[asset_id][subset_name] = {}

            version_docs_by_parent_id[asset_id][subset_name][version] = (
                version_doc
            )

        filtered_versions = []
        for asset_version in asset_versions:
            asset_id = asset_version["asset_id"]
            asset = assets_by_id[asset_id]
            parent_id = asset["context_id"]
            asset_doc = asset_docs_by_ftrack_id.get(parent_id)
            if not asset_doc:
                continue

            subsets_by_name = version_docs_by_parent_id.get(asset_doc["_id"])
            if not subsets_by_name:
                continue

            subset_name = asset["name"]
            version_docs_by_version = subsets_by_name.get(subset_name)
            if not version_docs_by_version:
                continue

            version = asset_version["version"]
            version_doc = version_docs_by_version.get(version)
            if version_doc:
                filtered_versions.append(version_doc)
        return filtered_versions

    def _get_subset_docs(
        self,
        asset_docs_by_ftrack_id,
        subset_names,
        asset_versions,
        assets_by_id
    ):
        asset_doc_ids = [
            asset_doc["_id"]
            for asset_doc in asset_docs_by_ftrack_id.values()
        ]
        subset_docs = list(self.dbcon.find({
            "type": "subset",
            "parent": {"$in": asset_doc_ids},
            "name": {"$in": list(subset_names)}
        }))
        subset_docs_by_parent_id = collections.defaultdict(dict)
        for subset_doc in subset_docs:
            asset_id = subset_doc["parent"]
            subset_name = subset_doc["name"]
            subset_docs_by_parent_id[asset_id][subset_name] = subset_doc

        filtered_subsets = []
        for asset_version in asset_versions:
            asset_id = asset_version["asset_id"]
            asset = assets_by_id[asset_id]

            parent_id = asset["context_id"]
            asset_doc = asset_docs_by_ftrack_id.get(parent_id)
            if not asset_doc:
                continue

            subsets_by_name = subset_docs_by_parent_id.get(asset_doc["_id"])
            if not subsets_by_name:
                continue

            subset_name = asset["name"]
            subset_doc = subsets_by_name.get(subset_name)
            if subset_doc:
                filtered_subsets.append(subset_doc)
        return filtered_subsets

    def _get_asset_docs(self, session, parent_ids):
        asset_docs = list(self.dbcon.find({
            "type": "asset",
            "data.ftrackId": {"$in": list(parent_ids)}
        }))

        asset_docs_by_ftrack_id = {}
        for asset_doc in asset_docs:
            ftrack_id = asset_doc["data"].get("ftrackId")
            if ftrack_id:
                asset_docs_by_ftrack_id[ftrack_id] = asset_doc

        attr_def = session.query((
            "select id from CustomAttributeConfiguration where key is \"{}\""
        ).format(CUST_ATTR_ID_KEY)).first()
        if attr_def is None:
            return asset_docs_by_ftrack_id

        avalon_mongo_id_values = query_custom_attributes(
            session, [attr_def["id"]], parent_ids, True
        )
        entity_ids_by_mongo_id = {
            ObjectId(item["value"]): item["entity_id"]
            for item in avalon_mongo_id_values
            if item["value"]
        }

        missing_ids = set(parent_ids)
        for entity_id in set(entity_ids_by_mongo_id.values()):
            if entity_id in missing_ids:
                missing_ids.remove(entity_id)

        entity_ids_by_name = {}
        if missing_ids:
            not_found_entities = session.query((
                "select id, name from TypedContext where id in ({})"
            ).format(self.join_query_keys(missing_ids))).all()
            entity_ids_by_name = {
                entity["name"]: entity["id"]
                for entity in not_found_entities
            }

        expressions = []
        if entity_ids_by_mongo_id:
            expression = {
                "type": "asset",
                "_id": {"$in": list(entity_ids_by_mongo_id.keys())}
            }
            expressions.append(expression)

        if entity_ids_by_name:
            expression = {
                "type": "asset",
                "name": {"$in": list(entity_ids_by_name.keys())}
            }
            expressions.append(expression)

        if expressions:
            if len(expressions) == 1:
                filter = expressions[0]
            else:
                filter = {"$or": expressions}

            asset_docs = self.dbcon.find(filter)
            for asset_doc in asset_docs:
                if asset_doc["_id"] in entity_ids_by_mongo_id:
                    entity_id = entity_ids_by_mongo_id[asset_doc["_id"]]
                    asset_docs_by_ftrack_id[entity_id] = asset_doc

                elif asset_doc["name"] in entity_ids_by_name:
                    entity_id = entity_ids_by_name[asset_doc["name"]]
                    asset_docs_by_ftrack_id[entity_id] = asset_doc

        return asset_docs_by_ftrack_id

    def launch(self, session, entities, event):
        if "values" not in event["data"]:
            return {
                "success": True,
                "message": "Nothing to do"
            }

        values = event["data"]["values"]
        skipped = values.pop("__skipped__")
        if skipped:
            return {
                "success": False,
                "message": "Action skipped"
            }

        user_id = event["source"]["user"]["id"]
        user_entity = session.query(
            "User where id is {}".format(user_id)
        ).one()

        job = session.create("Job", {
            "user": user_entity,
            "status": "running",
            "data": json.dumps({
                "description": "Delivery processing."
            })
        })
        session.commit()

        try:
            self.dbcon.install()
            report = self.real_launch(session, entities, event)

        except Exception as exc:
            report = {
                "success": False,
                "title": "Delivery failed",
                "items": [{
                    "type": "label",
                    "value": (
                        "Error during delivery action process:<br>{}"
                        "<br><br>Check logs for more information."
                    ).format(str(exc))
                }]
            }
            self.log.warning(
                "Failed during processing delivery action.",
                exc_info=True
            )

        finally:
            if report["success"]:
                job["status"] = "done"
            else:
                job["status"] = "failed"
            session.commit()
            self.dbcon.uninstall()

        if not report["success"]:
            self.show_interface(
                items=report["items"],
                title=report["title"],
                event=event
            )
            return {
                "success": False,
                "message": "Errors during delivery process. See report."
            }

        return report

    def real_launch(self, session, entities, event):
        self.log.info("Delivery action just started.")
        report_items = collections.defaultdict(list)

        values = event["data"]["values"]

        location_path = values.pop("__location_path__")
        anatomy_name = values.pop("__new_anatomies__")
        project_name = values.pop("__project_name__")

        repre_names = []
        for key, value in values.items():
            if value is True:
                repre_names.append(key)

        if not repre_names:
            return {
                "success": True,
                "message": "No selected components to deliver."
            }

        location_path = location_path.strip()
        if location_path:
            location_path = os.path.normpath(location_path)
            if not os.path.exists(location_path):
                os.makedirs(location_path)

        self.dbcon.Session["AVALON_PROJECT"] = project_name

        self.log.debug("Collecting representations to process.")
        version_ids = self._get_interest_version_ids(session, entities)
        repres_to_deliver = list(self.dbcon.find({
            "type": "representation",
            "parent": {"$in": version_ids},
            "name": {"$in": repre_names}
        }))

        anatomy = Anatomy(project_name)

        format_dict = get_format_dict(anatomy, location_path)

        datetime_data = config.get_datetime_data()
        for repre in repres_to_deliver:
            source_path = repre.get("data", {}).get("path")
            debug_msg = "Processing representation {}".format(repre["_id"])
            if source_path:
                debug_msg += " with published path {}.".format(source_path)
            self.log.debug(debug_msg)

            anatomy_data = copy.deepcopy(repre["context"])
            repre_report_items = check_destination_path(repre["_id"],
                                                        anatomy,
                                                        anatomy_data,
                                                        datetime_data,
                                                        anatomy_name)

            if repre_report_items:
                report_items.update(repre_report_items)
                continue

            # Get source repre path
            frame = repre['context'].get('frame')

            if frame:
                repre["context"]["frame"] = len(str(frame)) * "#"

            repre_path = path_from_representation(repre, anatomy)
            # TODO add backup solution where root of path from component
            # is replaced with root
            args = (
                repre_path,
                repre,
                anatomy,
                anatomy_name,
                anatomy_data,
                format_dict,
                report_items,
                self.log
            )
            if not frame:
                process_single_file(*args)
            else:
                process_sequence(*args)

        return self.report(report_items)

    def report(self, report_items):
        """Returns dict with final status of delivery (succes, fail etc.)."""
        items = []

        for msg, _items in report_items.items():
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
            "title": "Delivery report",
            "success": False
        }


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    Delivery(session).register()
