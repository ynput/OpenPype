import os
from openpype_modules.ftrack.lib import BaseAction, statics_icon
from avalon import lib as avalonlib
from openpype.api import (
    Anatomy,
    get_project_settings
)
from openpype.lib import ApplicationManager


class CreateFolders(BaseAction):
    identifier = "create.folders"
    label = "Create Folders"
    icon = statics_icon("ftrack", "action_icons", "CreateFolders.svg")

    def discover(self, session, entities, event):
        if len(entities) != 1:
            return False

        not_allowed = ["assetversion", "project"]
        if entities[0].entity_type.lower() in not_allowed:
            return False

        return True

    def interface(self, session, entities, event):
        if event["data"].get("values", {}):
            return
        entity = entities[0]
        without_interface = True
        for child in entity["children"]:
            if child["object_type"]["name"].lower() != "task":
                without_interface = False
                break
        self.without_interface = without_interface
        if without_interface:
            return
        title = "Create folders"

        entity_name = entity["name"]
        msg = (
            "<h2>Do you want create folders also"
            " for all children of \"{}\"?</h2>"
        )
        if entity.entity_type.lower() == "project":
            entity_name = entity["full_name"]
            msg = msg.replace(" also", "")
            msg += "<h3>(Project root won't be created if not checked)</h3>"
        items = []
        item_msg = {
            "type": "label",
            "value": msg.format(entity_name)
        }
        item_label = {
            "type": "label",
            "value": "With all chilren entities"
        }
        item = {
            "name": "children_included",
            "type": "boolean",
            "value": False
        }
        items.append(item_msg)
        items.append(item_label)
        items.append(item)

        return {
            "items": items,
            "title": title
        }

    def launch(self, session, entities, event):
        '''Callback method for custom action.'''
        with_childrens = True
        if self.without_interface is False:
            if "values" not in event["data"]:
                return
            with_childrens = event["data"]["values"]["children_included"]

        entity = entities[0]
        if entity.entity_type.lower() == "project":
            proj = entity
        else:
            proj = entity["project"]
        project_name = proj["full_name"]
        project_code = proj["name"]

        if entity.entity_type.lower() == 'project' and with_childrens is False:
            return {
                'success': True,
                'message': 'Nothing was created'
            }

        all_entities = []
        all_entities.append(entity)
        if with_childrens:
            all_entities = self.get_notask_children(entity)

        anatomy = Anatomy(project_name)

        work_keys = ["work", "folder"]
        work_template = anatomy.templates
        for key in work_keys:
            work_template = work_template[key]
        work_has_apps = "{app" in work_template

        publish_keys = ["publish", "folder"]
        publish_template = anatomy.templates
        for key in publish_keys:
            publish_template = publish_template[key]
        publish_has_apps = "{app" in publish_template

        collected_paths = []
        for entity in all_entities:
            if entity.entity_type.lower() == "project":
                continue
            ent_data = {
                "project": {
                    "name": project_name,
                    "code": project_code
                }
            }

            ent_data["asset"] = entity["name"]

            parents = entity["link"][1:-1]
            hierarchy_names = [p["name"] for p in parents]
            hierarchy = ""
            if hierarchy_names:
                hierarchy = os.path.sep.join(hierarchy_names)
            ent_data["hierarchy"] = hierarchy

            tasks_created = False
            for child in entity["children"]:
                if child["object_type"]["name"].lower() != "task":
                    continue
                tasks_created = True
                task_data = ent_data.copy()
                task_data["task"] = child["name"]

                apps = []

                # Template wok
                if work_has_apps:
                    app_data = task_data.copy()
                    for app in apps:
                        app_data["app"] = app
                        collected_paths.append(self.compute_template(
                            anatomy, app_data, work_keys
                        ))
                else:
                    collected_paths.append(self.compute_template(
                        anatomy, task_data, work_keys
                    ))

                # Template publish
                if publish_has_apps:
                    app_data = task_data.copy()
                    for app in apps:
                        app_data["app"] = app
                        collected_paths.append(self.compute_template(
                            anatomy, app_data, publish_keys
                        ))
                else:
                    collected_paths.append(self.compute_template(
                        anatomy, task_data, publish_keys
                    ))

            if not tasks_created:
                # create path for entity
                collected_paths.append(self.compute_template(
                    anatomy, ent_data, work_keys
                ))
                collected_paths.append(self.compute_template(
                    anatomy, ent_data, publish_keys
                ))

        if len(collected_paths) == 0:
            return {
                "success": True,
                "message": "No project folders to create."
            }

        self.log.info("Creating folders:")

        for path in set(collected_paths):
            self.log.info(path)
            if not os.path.exists(path):
                os.makedirs(path)

        return {
            "success": True,
            "message": "Successfully created project folders."
        }

    def get_notask_children(self, entity):
        output = []
        if entity.entity_type.lower() == "task":
            return output

        output.append(entity)
        for child in entity["children"]:
            output.extend(self.get_notask_children(child))
        return output

    def compute_template(self, anatomy, data, anatomy_keys):
        filled_template = anatomy.format_all(data)
        for key in anatomy_keys:
            filled_template = filled_template[key]

        if filled_template.solved:
            return os.path.normpath(filled_template)

        self.log.warning(
            "Template \"{}\" was not fully filled \"{}\"".format(
                filled_template.template, filled_template
            )
        )
        return os.path.normpath(filled_template.split("{")[0])


def register(session):
    """Register plugin. Called when used as an plugin."""
    CreateFolders(session).register()
