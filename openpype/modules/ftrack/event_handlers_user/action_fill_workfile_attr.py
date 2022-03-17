import collections

import ftrack_api

from avalon.api import AvalonMongoDB
from openpype.api import get_project_settings
from openpype.lib import (
    get_workfile_template_key,
    get_workdir_data,
    Anatomy,
    StringTemplate,
)
from openpype_modules.ftrack.lib import BaseAction, statics_icon
from openpype_modules.ftrack.lib.avalon_sync import create_chunks


class FillWorkfileAttributeAction(BaseAction):
    """Action fill work filename into custom attribute on tasks.

    Prerequirements are that the project is synchronized so it is possible to
    access project anatomy and project/asset documents. Tasks that are not
    synchronized are skipped too.
    """

    identifier = "fill.workfile.attr"
    label = "OpenPype Admin"
    variant = "- Fill workfile attribute"
    description = "Precalculate and fill workfile name into a custom attribute"
    icon = statics_icon("ftrack", "action_icons", "OpenPypeAdmin.svg")

    settings_key = "fill_workfile_attribute"

    def discover(self, session, entities, event):
        """ Validate selection. """
        is_valid = False
        for ent in event["data"]["selection"]:
            # Ignore entities that are not tasks or projects
            if ent["entityType"].lower() in ["show", "task"]:
                is_valid = True
                break

        if is_valid:
            is_valid = self.valid_roles(session, entities, event)
        return is_valid

    def launch(self, session, entities, event):
        task_entities = []
        other_entities = []
        project_entity = None
        project_selected = False
        for entity in entities:
            if project_entity is None:
                project_entity = self.get_project_from_entity(entity)

            ent_type_low = entity.entity_type.lower()
            if ent_type_low == "project":
                project_selected = True
                break

            elif ent_type_low == "task":
                task_entities.append(entity)
            else:
                other_entities.append(entity)

        project_name = project_entity["full_name"]
        project_settings = get_project_settings(project_name)
        custom_attribute_key = (
            project_settings
            .get("ftrack", {})
            .get("user_handlers", {})
            .get(self.settings_key, {})
            .get("custom_attribute_key")
        )
        if not custom_attribute_key:
            return {
                "success": False,
                "message": "Custom attribute key is not set in settings"
            }

        task_obj_type = session.query(
            "select id from ObjectType where name is \"Task\""
        ).one()
        text_type = session.query(
            "select id from CustomAttributeType where name is \"text\""
        ).one()
        attr_conf = session.query(
            (
                "select id, key from CustomAttributeConfiguration"
                " where object_type_id is \"{}\""
                " and type_id is \"{}\""
                " and key is \"{}\""
            ).format(
                task_obj_type["id"], text_type["id"], custom_attribute_key
            )
        ).first()
        if not attr_conf:
            return {
                "success": False,
                "message": (
                    "Could not find Task (text) Custom attribute \"{}\""
                ).format(custom_attribute_key)
            }

        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        asset_docs = list(dbcon.find({"type": "asset"}))
        if project_selected:
            asset_docs_with_task_names = self._get_asset_docs_for_project(
                session, project_entity, asset_docs
            )

        else:
            asset_docs_with_task_names = self._get_tasks_for_selection(
                session, other_entities, task_entities, asset_docs
            )

        host_name = "{host}"
        project_doc = dbcon.find_one({"type": "project"})
        project_settings = get_project_settings(project_name)
        anatomy = Anatomy(project_name)
        templates_by_key = {}

        operations = []
        for asset_doc, task_entities in asset_docs_with_task_names:
            for task_entity in task_entities:
                workfile_data = get_workdir_data(
                    project_doc, asset_doc, task_entity["name"], host_name
                )
                workfile_data["version"] = 1
                workfile_data["ext"] = "{ext}"

                task_type = workfile_data["task"]["type"]
                template_key = get_workfile_template_key(
                    task_type, host_name, project_settings=project_settings
                )
                if template_key in templates_by_key:
                    template = templates_by_key[template_key]
                else:
                    template = StringTemplate(
                        anatomy.templates[template_key]["file"]
                    )
                    templates_by_key[template_key] = template

                result = template.format(workfile_data)
                if not result.solved:
                    # TODO report
                    pass
                else:
                    table_values = collections.OrderedDict((
                        ("configuration_id", attr_conf["id"]),
                        ("entity_id", task_entity["id"])
                    ))
                    operations.append(
                        ftrack_api.operation.UpdateEntityOperation(
                            "ContextCustomAttributeValue",
                            table_values,
                            "value",
                            ftrack_api.symbol.NOT_SET,
                            str(result)
                        )
                    )

        if operations:
            for sub_operations in create_chunks(operations, 50):
                for op in sub_operations:
                    session.recorded_operations.push(op)
                session.commit()

        return True

    def _get_asset_docs_for_project(self, session, project_entity, asset_docs):
        asset_docs_task_names = collections.defaultdict(list)
        for asset_doc in asset_docs:
            asset_data = asset_doc["data"]
            asset_tasks = asset_data.get("tasks")
            ftrack_id = asset_data.get("ftrackId")
            if not asset_tasks or not ftrack_id:
                continue
            asset_docs_task_names[ftrack_id].append(
                (asset_doc, list(asset_tasks.keys()))
            )

        task_entities = session.query((
            "select id, name, parent_id from Task where project_id is {}"
        ).format(project_entity["id"])).all()
        task_entities_by_parent_id = collections.defaultdict(list)
        for task_entity in task_entities:
            parent_id = task_entity["parent_id"]
            task_entities_by_parent_id[parent_id].append(task_entity)

        output = []
        for ftrack_id, items in asset_docs_task_names.items():
            for item in items:
                asset_doc, task_names = item
                valid_task_entities = []
                for task_entity in task_entities_by_parent_id[ftrack_id]:
                    if task_entity["name"] in task_names:
                        valid_task_entities.append(task_entity)

                if valid_task_entities:
                    output.append((asset_doc, valid_task_entities))

        return output

    def _get_tasks_for_selection(
        self, session, other_entities, task_entities, asset_docs
    ):
        all_tasks = object()
        asset_docs_by_ftrack_id = {}
        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in asset_docs:
            asset_data = asset_doc["data"]
            ftrack_id = asset_data.get("ftrackId")
            parent_id = asset_data.get("visualParent")
            asset_docs_by_parent_id[parent_id].append(asset_doc)
            if ftrack_id:
                asset_docs_by_ftrack_id[ftrack_id] = asset_doc

        missing_docs = set()
        all_tasks_ids = set()
        task_names_by_ftrack_id = collections.defaultdict(list)
        for other_entity in other_entities:
            ftrack_id = other_entity["id"]
            if ftrack_id not in asset_docs_by_ftrack_id:
                missing_docs.add(ftrack_id)
                continue
            all_tasks_ids.add(ftrack_id)
            task_names_by_ftrack_id[ftrack_id] = all_tasks

        for task_entity in task_entities:
            parent_id = task_entity["parent_id"]
            if parent_id not in asset_docs_by_ftrack_id:
                missing_docs.add(parent_id)
                continue

            if all_tasks_ids not in all_tasks_ids:
                task_names_by_ftrack_id[ftrack_id].append(task_entity["name"])

        ftrack_ids = set()
        asset_doc_with_task_names_by_id = collections.defaultdict(list)
        for ftrack_id, task_names in task_names_by_ftrack_id.items():
            asset_doc = asset_docs_by_ftrack_id[ftrack_id]
            asset_data = asset_doc["data"]
            asset_tasks = asset_data.get("tasks")
            if not asset_tasks:
                # TODO add to report
                continue

            if task_names is all_tasks:
                task_names = list(asset_tasks.keys())
            else:
                new_task_names = []
                for task_name in task_names:
                    if task_name in asset_tasks:
                        new_task_names.append(task_name)
                    else:
                        # TODO add report
                        pass
                task_names = new_task_names

            if task_names:
                ftrack_ids.add(ftrack_id)
                asset_doc_with_task_names_by_id[ftrack_id].append(
                    (asset_doc, task_names)
                )

        task_entities = session.query((
            "select id, name, parent_id from Task where parent_id in ({})"
        ).format(self.join_query_keys(ftrack_ids))).all()
        task_entitiy_by_parent_id = collections.defaultdict(list)
        for task_entity in task_entities:
            parent_id = task_entity["parent_id"]
            task_entitiy_by_parent_id[parent_id].append(task_entity)

        output = []
        for ftrack_id, items in asset_doc_with_task_names_by_id.items():
            for item in items:
                asset_doc, task_names = item
                valid_task_entities = []
                for task_entity in task_entitiy_by_parent_id[ftrack_id]:
                    if task_entity["name"] in task_names:
                        valid_task_entities.append(task_entity)
                if valid_task_entities:
                    output.append((asset_doc, valid_task_entities))
        return output


def register(session):
    FillWorkfileAttributeAction(session).register()
