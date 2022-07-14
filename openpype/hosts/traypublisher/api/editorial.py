import re
from copy import deepcopy

from openpype.client import get_asset_by_id


class ShotMetadataSover:
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """
    # presets
    clip_name_tokenizer = None
    shot_rename = True
    shot_hierarchy = None
    shot_add_tasks = None

    def __init__(self, creator_settings):
        self.clip_name_tokenizer = creator_settings["clip_name_tokenizer"]
        self.shot_rename = creator_settings["shot_rename"]
        self.shot_hierarchy = creator_settings["shot_hierarchy"]
        self.shot_add_tasks = creator_settings["shot_add_tasks"]

    def convert_to_entity(self, key, value):
        # ftrack compatible entity types
        types = {"shot": "Shot",
                 "folder": "Folder",
                 "episode": "Episode",
                 "sequence": "Sequence",
                 "track": "Sequence",
                 }
        # convert to entity type
        entity_type = types.get(key, None)

        # return if any
        if entity_type:
            return {"entity_type": entity_type, "entity_name": value}

    def _rename_template(self, clip_name, source_data):
        if self.clip_name_tokenizer:
            search_text = ""
            parent_name = source_data["assetEntity"]["name"]

            search_text += parent_name + clip_name
            source_data["anatomy_data"].update({"clip_name": clip_name})
            for type, pattern in self.clip_name_tokenizer.items():
                p = re.compile(pattern)
                match = p.findall(search_text)
                if not match:
                    continue
                source_data["anatomy_data"][type] = match[-1]

            # format to new shot name
            return self.shot_rename[
                "shot_rename_template"].format(
                    **source_data["anatomy_data"])

    def _create_hierarchy(self, source_data):
        asset_doc = source_data["selected_asset_doc"]
        project_doc = source_data["project_doc"]

        project_name = project_doc["name"]
        visual_hierarchy = [asset_doc]
        current_doc = asset_doc

        # TODO: refactory withou the while
        while True:
            visual_parent_id = current_doc["data"]["visualParent"]
            visual_parent = None
            if visual_parent_id:
                visual_parent = get_asset_by_id(project_name, visual_parent_id)

            if not visual_parent:
                visual_hierarchy.append(project_doc)
                break
            visual_hierarchy.append(visual_parent)
            current_doc = visual_parent

        # add current selection context hierarchy from standalonepublisher
        parents = []
        parents.extend(
            {
                "entity_type": entity["data"]["entityType"],
                "entity_name": entity["name"]
            }
            for entity in reversed(visual_hierarchy)
        )

        _hierarchy = []
        if self.shot_hierarchy.get("enabled"):
            parent_template_patern = re.compile(r"\{([a-z]*?)\}")
            # fill the parents parts from presets
            shot_hierarchy = deepcopy(self.shot_hierarchy)
            hierarchy_parents = shot_hierarchy["parents"]

            # fill parent keys data template from anatomy data
            for parent_key in hierarchy_parents:
                hierarchy_parents[parent_key] = hierarchy_parents[
                    parent_key].format(**source_data["anatomy_data"])

            for _index, _parent in enumerate(
                    shot_hierarchy["parents_path"].split("/")):
                parent_filled = _parent.format(**hierarchy_parents)
                parent_key = parent_template_patern.findall(_parent).pop()

                # in case SP context is set to the same folder
                if (_index == 0) and ("folder" in parent_key) \
                        and (parents[-1]["entity_name"] == parent_filled):
                    self.log.debug(f" skipping : {parent_filled}")
                    continue

                # in case first parent is project then start parents from start
                if (_index == 0) and ("project" in parent_key):
                    self.log.debug("rebuilding parents from scratch")
                    project_parent = parents[0]
                    parents = [project_parent]
                    self.log.debug(f"project_parent: {project_parent}")
                    self.log.debug(f"parents: {parents}")
                    continue

                prnt = self.convert_to_entity(
                    parent_key, parent_filled)
                parents.append(prnt)
                _hierarchy.append(parent_filled)

        # convert hierarchy to string
        hierarchy_path = "/".join(_hierarchy)

        output_data = {
            "hierarchy": hierarchy_path,
            "parents": parents
        }
        # print
        self.log.debug(f"__ hierarchy_path: {hierarchy_path}")
        self.log.debug(f"__ parents: {parents}")

        output_data["tasks"] = self._generate_tasks_from_settings(project_doc)

        return output_data

    def _generate_tasks_from_settings(self, project_doc):
        tasks_to_add = {}
        if self.shot_add_tasks:
            project_tasks = project_doc["config"]["tasks"]
            for task_name, task_data in self.shot_add_tasks.items():
                _task_data = deepcopy(task_data)

                # check if task type in project task types
                if _task_data["type"] in project_tasks.keys():
                    tasks_to_add[task_name] = _task_data
                else:
                    raise KeyError(
                        "Missing task type `{}` for `{}` is not"
                        " existing in `{}``".format(
                            _task_data["type"],
                            task_name,
                            list(project_tasks.keys())
                        )
                    )

        return tasks_to_add

    def generate_data(self, clip_name, source_data):
        self.log.info(f"_ source_data: {source_data}")

        # match clip to shot name at start
        shot_name = clip_name

        if self.shot_rename["enabled"]:
            shot_name = self._rename_template(clip_name, source_data)
            self.log.info(f"Renamed shot name: {shot_name}")

        hierarchy_data = self._create_hierarchy(source_data)

        return shot_name, hierarchy_data
