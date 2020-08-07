import os
import re

from pype.modules.ftrack.lib import BaseAction, statics_icon
from pype.api import config, Anatomy


class CreateProjectFolders(BaseAction):
    """Action create folder structure and may create hierarchy in Ftrack.

    Creation of folder structure and hierarchy in Ftrack is based on presets.
    These presets are located in:
    `~/pype-config/presets/tools/project_folder_structure.json`

    Example of content:
    ```json
    {
        "__project_root__": {
            "prod" : {},
            "resources" : {
              "footage": {
                "plates": {},
                "offline": {}
              },
              "audio": {},
              "art_dept": {}
            },
            "editorial" : {},
            "assets[ftrack.Library]": {
              "characters[ftrack]": {},
              "locations[ftrack]": {}
            },
            "shots[ftrack.Sequence]": {
              "scripts": {},
              "editorial[ftrack.Folder]": {}
            }
        }
    }
    ```
    Key "__project_root__" indicates root folder (or entity). Each key in
    dictionary represents folder name. Value may contain another dictionary
    with subfolders.

    Identifier `[ftrack]` in name says that this should be also created in
    Ftrack hierarchy. It is possible to specify entity type of item with "." .
    If key is `assets[ftrack.Library]` then in ftrack will be created entity
    with name "assets" and entity type "Library". It is expected Library entity
    type exist in Ftrack.
    """

    identifier = "create.project.structure"
    label = "Create Project Structure"
    description = "Creates folder structure"
    role_list = ["Pypeclub", "Administrator", "Project Manager"]
    icon = statics_icon("ftrack", "action_icons", "CreateProjectFolders.svg")

    pattern_array = re.compile(r"\[.*\]")
    pattern_ftrack = re.compile(r".*\[[.]*ftrack[.]*")
    pattern_ent_ftrack = re.compile(r"ftrack\.[^.,\],\s,]*")
    project_root_key = "__project_root__"

    def discover(self, session, entities, event):
        if len(entities) != 1:
            return False

        if entities[0].entity_type.lower() != "project":
            return False

        return True

    def launch(self, session, entities, event):
        entity = entities[0]
        project = self.get_project_from_entity(entity)
        project_folder_presets = (
            config.get_presets()
            .get("tools", {})
            .get("project_folder_structure")
        )
        if not project_folder_presets:
            return {
                "success": False,
                "message": "Project structure presets are not set."
            }

        try:
            # Get paths based on presets
            basic_paths = self.get_path_items(project_folder_presets)
            anatomy = Anatomy(project["full_name"])
            self.create_folders(basic_paths, entity, project, anatomy)
            self.create_ftrack_entities(basic_paths, project)

        except Exception as exc:
            session.rollback()
            return {
                "success": False,
                "message": str(exc)
            }

        return True

    def get_ftrack_paths(self, paths_items):
        all_ftrack_paths = []
        for path_items in paths_items:
            ftrack_path_items = []
            is_ftrack = False
            for item in reversed(path_items):
                if item == self.project_root_key:
                    continue
                if is_ftrack:
                    ftrack_path_items.append(item)
                elif re.match(self.pattern_ftrack, item):
                    ftrack_path_items.append(item)
                    is_ftrack = True
            ftrack_path_items = list(reversed(ftrack_path_items))
            if ftrack_path_items:
                all_ftrack_paths.append(ftrack_path_items)
        return all_ftrack_paths

    def compute_ftrack_items(self, in_list, keys):
        if len(keys) == 0:
            return in_list
        key = keys[0]
        exist = None
        for index, subdict in enumerate(in_list):
            if key in subdict:
                exist = index
                break
        if exist is not None:
            in_list[exist][key] = self.compute_ftrack_items(
                in_list[exist][key], keys[1:]
            )
        else:
            in_list.append({key: self.compute_ftrack_items([], keys[1:])})
        return in_list

    def translate_ftrack_items(self, paths_items):
        main = []
        for path_items in paths_items:
            main = self.compute_ftrack_items(main, path_items)
        return main

    def create_ftrack_entities(self, basic_paths, project_ent):
        only_ftrack_items = self.get_ftrack_paths(basic_paths)
        ftrack_paths = self.translate_ftrack_items(only_ftrack_items)

        for separation in ftrack_paths:
            parent = project_ent
            self.trigger_creation(separation, parent)

    def trigger_creation(self, separation, parent):
        for item, subvalues in separation.items():
            matches = re.findall(self.pattern_array, item)
            ent_type = "Folder"
            if len(matches) == 0:
                name = item
            else:
                match = matches[0]
                name = item.replace(match, "")
                ent_type_match = re.findall(self.pattern_ent_ftrack, match)
                if len(ent_type_match) > 0:
                    ent_type_split = ent_type_match[0].split(".")
                    if len(ent_type_split) == 2:
                        ent_type = ent_type_split[1]
            new_parent = self.create_ftrack_entity(name, ent_type, parent)
            if subvalues:
                for subvalue in subvalues:
                    self.trigger_creation(subvalue, new_parent)

    def create_ftrack_entity(self, name, ent_type, parent):
        for children in parent["children"]:
            if children["name"] == name:
                return children
        data = {
            "name": name,
            "parent_id": parent["id"]
        }
        if parent.entity_type.lower() == "project":
            data["project_id"] = parent["id"]
        else:
            data["project_id"] = parent["project"]["id"]

        existing_entity = self.session.query((
            "TypedContext where name is \"{}\" and "
            "parent_id is \"{}\" and project_id is \"{}\""
        ).format(name, data["parent_id"], data["project_id"])).first()
        if existing_entity:
            return existing_entity

        new_ent = self.session.create(ent_type, data)
        self.session.commit()
        return new_ent

    def get_path_items(self, in_dict):
        output = []
        for key, value in in_dict.items():
            if not value:
                output.append(key)
            else:
                paths = self.get_path_items(value)
                for path in paths:
                    if not isinstance(path, (list, tuple)):
                        path = [path]

                    output.append([key, *path])

        return output

    def compute_paths(self, basic_paths_items, project_root):
        output = []
        for path_items in basic_paths_items:
            clean_items = []
            for path_item in path_items:
                matches = re.findall(self.pattern_array, path_item)
                if len(matches) > 0:
                    path_item = path_item.replace(matches[0], "")
                if path_item == self.project_root_key:
                    path_item = project_root
                clean_items.append(path_item)
            output.append(os.path.normpath(os.path.sep.join(clean_items)))
        return output

    def create_folders(self, basic_paths, entity, project, anatomy):
        roots_paths = []
        if isinstance(anatomy.roots, dict):
            for root in anatomy.roots:
                roots_paths.append(root.value)
        else:
            roots_paths.append(anatomy.roots.value)

        for root_path in roots_paths:
            project_root = os.path.join(root_path, project["full_name"])
            full_paths = self.compute_paths(basic_paths, project_root)
            # Create folders
            for path in full_paths:
                if os.path.exists(path):
                    continue
                os.makedirs(path.format(project_root=project_root))


def register(session, plugins_presets={}):
    CreateProjectFolders(session, plugins_presets).register()
