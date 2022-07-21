import re
from copy import deepcopy

from openpype.client import get_asset_by_id
from openpype.pipeline.create import CreatorError


class ShotMetadataSolver:
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    NO_DECOR_PATERN = re.compile(r"\{([a-z]*?)\}")

    # presets
    clip_name_tokenizer = None
    shot_rename = True
    shot_hierarchy = None
    shot_add_tasks = None

    def __init__(
        self,
        clip_name_tokenizer,
        shot_rename,
        shot_hierarchy,
        shot_add_tasks,
        logger
    ):
        self.clip_name_tokenizer = clip_name_tokenizer
        self.shot_rename = shot_rename
        self.shot_hierarchy = shot_hierarchy
        self.shot_add_tasks = shot_add_tasks
        self.log = logger

    def _rename_template(self, data):
        shot_rename_template = self.shot_rename[
            "shot_rename_template"]
        try:
            # format to new shot name
            return shot_rename_template.format(**data)
        except KeyError as _E:
            raise CreatorError((
                "Make sure all keys are correct in settings: \n\n"
                f"From template string {shot_rename_template} > "
                f"`{_E}` has no equivalent in \n"
                f"{list(data.keys())} input formating keys!"
            ))

    def _generate_tokens(self, clip_name, source_data):
        output_data = deepcopy(source_data["anatomy_data"])
        output_data["clip_name"] = clip_name

        if not self.clip_name_tokenizer:
            return output_data

        parent_name = source_data["selected_asset_doc"]["name"]

        search_text = parent_name + clip_name

        for token_key, pattern in self.clip_name_tokenizer.items():
            p = re.compile(pattern)
            match = p.findall(search_text)
            if not match:
                raise CreatorError((
                    "Make sure regex expression is correct: \n\n"
                    f"From settings '{token_key}' key "
                    f"with '{pattern}' expression, \n"
                    f"is not able to find anything in '{search_text}'!"
                ))

            #  QUESTION:how to refactory `match[-1]` to some better way?
            output_data[token_key] = match[-1]

        return output_data

    def _create_parents_from_settings(self, parents, data):

        # fill the parents parts from presets
        shot_hierarchy = deepcopy(self.shot_hierarchy)
        hierarchy_parents = shot_hierarchy["parents"]

        # fill parent keys data template from anatomy data
        try:
            _parent_tokens_formating_data = {
                parent_token["name"]: parent_token["value"].format(**data)
                for parent_token in hierarchy_parents
            }
        except KeyError as _E:
            raise CreatorError((
                "Make sure all keys are correct in settings: \n"
                f"`{_E}` has no equivalent in \n{list(data.keys())}"
            ))

        _parent_tokens_type = {
            parent_token["name"]: parent_token["type"]
            for parent_token in hierarchy_parents
        }
        for _index, _parent in enumerate(
                shot_hierarchy["parents_path"].split("/")
        ):
            # format parent token with value which is formated
            try:
                parent_name = _parent.format(
                    **_parent_tokens_formating_data)
            except KeyError as _E:
                raise CreatorError((
                    "Make sure all keys are correct in settings: \n\n"
                    f"From template string {shot_hierarchy['parents_path']} > "
                    f"`{_E}` has no equivalent in \n"
                    f"{list(_parent_tokens_formating_data.keys())} parents"
                ))

            parent_token_name = (
                self.NO_DECOR_PATERN.findall(_parent).pop())

            if not parent_token_name:
                raise KeyError(
                    f"Parent token is not found in: `{_parent}`")

            # find parent type
            parent_token_type = _parent_tokens_type[parent_token_name]

            # in case selected context is set to the same asset
            if (
                _index == 0
                and parents[-1]["entity_name"] == parent_name
            ):
                self.log.debug(f" skipping : {parent_name}")
                continue

            # in case first parent is project then start parents from start
            if (
                _index == 0
                and parent_token_type == "Project"
            ):
                self.log.debug("rebuilding parents from scratch")
                project_parent = parents[0]
                parents = [project_parent]
                continue

            parents.append({
                "entity_type": parent_token_type,
                "entity_name": parent_name
            })

        self.log.debug(f"__ parents: {parents}")

        return parents

    def _create_hierarchy_path(self, parents):
        return "/".join(
            [
                p["entity_name"] for p in parents
                if p["entity_type"] != "Project"
            ]
        ) if parents else ""

    def _get_parents_from_selected_asset(
        self,
        asset_doc,
        project_doc
    ):
        project_name = project_doc["name"]
        visual_hierarchy = [asset_doc]
        current_doc = asset_doc

        # looping trought all available visual parents
        # if they are not available anymore than it breaks
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

        # add current selection context hierarchy
        return [
            {
                "entity_type": entity["data"]["entityType"],
                "entity_name": entity["name"]
            }
            for entity in reversed(visual_hierarchy)
        ]

    def _generate_tasks_from_settings(self, project_doc):
        tasks_to_add = {}

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

        tasks = {}
        asset_doc = source_data["selected_asset_doc"]
        project_doc = source_data["project_doc"]

        # match clip to shot name at start
        shot_name = clip_name

        # parse all tokens and generate formating data
        formating_data = self._generate_tokens(shot_name, source_data)

        # generate parents from selected asset
        parents = self._get_parents_from_selected_asset(asset_doc, project_doc)

        if self.shot_rename["enabled"]:
            shot_name = self._rename_template(formating_data)
            self.log.info(f"Renamed shot name: {shot_name}")

        if self.shot_hierarchy["enabled"]:
            parents = self._create_parents_from_settings(
                parents, formating_data)

        if self.shot_add_tasks:
            tasks = self._generate_tasks_from_settings(
                project_doc)

        return shot_name, {
            "hierarchy": self._create_hierarchy_path(parents),
            "parents": parents,
            "tasks": tasks
        }
