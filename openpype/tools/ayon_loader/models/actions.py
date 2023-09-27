import inspect
import copy
import collections
from abc import ABCMeta, abstractmethod

import six

from openpype.client import (
    get_project,
    get_assets,
    get_subsets,
    get_versions,
    get_representations,
)
from openpype.pipeline.load import (
    discover_loader_plugins,
    SubsetLoaderPlugin,
    filter_repre_contexts_by_loader,
    get_loader_identifier,
    load_with_repre_context,
    load_with_subset_context,
    load_with_subset_contexts,
    LoadError,
    IncompatibleLoaderError,
)
from openpype.tools.ayon_utils.models import NestedCacheItem


@six.add_metaclass(ABCMeta)
class BaseActionItem(object):
    @abstractmethod
    def item_type(self):
        pass

    @abstractmethod
    def to_data(self):
        pass

    @classmethod
    @abstractmethod
    def from_data(cls, data):
        pass


class ActionItem(BaseActionItem):
    def __init__(
        self,
        identifier,
        label,
        icon,
        tooltip,
        options,
        order,
        project_name,
        folder_ids,
        product_ids,
        version_ids,
        representation_ids,
    ):
        self.identifier = identifier
        self.label = label
        self.icon = icon
        self.tooltip = tooltip
        self.options = options
        self.order = order
        self.project_name = project_name
        self.folder_ids = folder_ids
        self.product_ids = product_ids
        self.version_ids = version_ids
        self.representation_ids = representation_ids

    def item_type(self):
        return "action"

    def to_data(self):
        return {
            "item_type": self.item_type(),
            "identifier": self.identifier,
            "label": self.label,
            "icon": self.icon,
            "tooltip": self.tooltip,
            "options": self.options,
            "order": self.order,
            "project_name": self.project_name,
            "folder_ids": self.folder_ids,
            "product_ids": self.product_ids,
            "version_ids": self.version_ids,
            "representation_ids": self.representation_ids,
        }

    @classmethod
    def from_data(cls, data):
        new_data = copy.deepcopy(data)
        new_data.pop("item_type")
        return cls(**new_data)


# NOTE This is just an idea. Not implemented on front end,
#    also hits issues with sorting of items in the UI.
# class SeparatorItem(BaseActionItem):
#     def item_type(self):
#         return "separator"
#
#     def to_data(self):
#         return {"item_type": self.item_type()}
#
#     @classmethod
#     def from_data(cls, data):
#         return cls()
#
#
# class MenuItem(BaseActionItem):
#     def __init__(self, label, icon, children):
#         self.label = label
#         self.icon = icon
#         self.children = children
#
#     def item_type(self):
#         return "menu"
#
#     def to_data(self):
#         return {
#             "item_type": self.item_type(),
#             "label": self.label,
#             "icon": self.icon,
#             "children": [child.to_data() for child in self.children]
#         }
#
#     @classmethod
#     def from_data(cls, data):
#         new_data = copy.deepcopy(data)
#         new_data.pop("item_type")
#         children = []
#         for child in data["children"]:
#             child_type = child["item_type"]
#             if child_type == "separator":
#                 children.append(SeparatorItem.from_data(child))
#             elif child_type == "menu":
#                 children.append(MenuItem.from_data(child))
#             elif child_type == "action":
#                 children.append(ActionItem.from_data(child))
#             else:
#                 raise ValueError("Invalid child type: {}".format(child_type))
#
#         new_data["children"] = children
#         return cls(**new_data)


class LoaderActionsModel:
    """Model for loader actions.

    This is probably only part of models that requires to use codebase from
    'openpype.client' because of backwards compatibility with loaders logic
    which are expecting mongo documents.

    TODOs:
        Use controller to get entities (documents) -> possible only when
            loaders are able to handle AYON vs. OpenPype logic.
        Cache loaders for time period and reset them on controller refresh.
            Also cache them per project.
        Add missing site sync logic, and if possible remove it from loaders.
        Implement loader actions to replace load plugins.
        Ask loader actions to return action items instead of guessing them.
    """

    # Cache loader plugins for some time
    # NOTE Set to '0' for development
    loaders_cache_lifetime = 30

    def __init__(self, controller):
        self._controller = controller
        self._tool_name = ""
        self._loaders_by_identifier = NestedCacheItem(
            levels=1, lifetime=self.loaders_cache_lifetime)
        self._product_loaders = NestedCacheItem(
            levels=1, lifetime=self.loaders_cache_lifetime)
        self._repre_loaders = NestedCacheItem(
            levels=1, lifetime=self.loaders_cache_lifetime)

    def reset(self):
        self._loaders_by_identifier.reset()
        self._product_loaders.reset()
        self._repre_loaders.reset()

    def get_versions_action_items(self, project_name, version_ids):
        action_items = []
        if not project_name or not version_ids:
            return action_items

        product_loaders, repre_loaders = self._get_loaders(project_name)
        (
            product_context_by_id,
            repre_context_by_id
        ) = self._contexts_for_versions(project_name, version_ids)

        repre_contexts = list(repre_context_by_id.values())
        repre_ids = set(repre_context_by_id.keys())
        repre_version_ids = set()
        repre_product_ids = set()
        repre_folder_ids = set()
        for repre_context in repre_context_by_id.values():
            repre_product_ids.add(repre_context["subset"]["_id"])
            repre_version_ids.add(repre_context["version"]["_id"])
            repre_folder_ids.add(repre_context["asset"]["_id"])

        action_items = []
        for loader in repre_loaders:
            if not repre_contexts:
                break

            # # do not allow download whole repre, select specific repre
            # if tools_lib.is_sync_loader(loader):
            #     continue

            filtered_repre_contexts = filter_repre_contexts_by_loader(
                repre_contexts, loader)
            if len(filtered_repre_contexts) != len(repre_contexts):
                continue

            item = self._create_loader_action_item(
                loader,
                repre_contexts,
                project_name=project_name,
                folder_ids=repre_folder_ids,
                product_ids=repre_product_ids,
                version_ids=repre_version_ids,
                representation_ids=repre_ids
            )
            action_items.append(item)

        # Subset Loaders.
        product_ids = set(product_context_by_id.keys())
        product_folder_ids = set()
        for product_context in product_context_by_id.values():
            product_folder_ids.add(product_context["asset"]["_id"])

        product_contexts = list(product_context_by_id.values())
        for loader in product_loaders:
            item = self._create_loader_action_item(
                loader,
                product_contexts,
                project_name=project_name,
                folder_ids=product_folder_ids,
                product_ids=product_ids,
            )
            action_items.append(item)

        action_items.sort(key=self._actions_sorter)
        return action_items

    def get_representations_action_items(
        self, project_name, representation_ids
    ):
        return []

    def trigger_action_item(
        self,
        identifier,
        options,
        project_name,
        folder_ids,
        product_ids,
        version_ids,
        representation_ids
    ):
        loader = self._get_loader_by_identifier(project_name, identifier)
        if representation_ids is not None:
            self._trigger_representation_loader(
                loader,
                options,
                project_name,
                folder_ids,
                product_ids,
                version_ids,
                representation_ids,
            )
        elif product_ids is not None:
            self._trigger_product_loader(
                loader,
                options,
                project_name,
                folder_ids,
                product_ids,
            )
        else:
            raise NotImplementedError(
                "Invalid arguments to trigger action item")

    def _get_loader_label(self, loader, representation=None):
        """Pull label info from loader class"""
        label = getattr(loader, "label", None)
        if label is None:
            label = loader.__name__
        if representation:
            # Add the representation as suffix
            label = "{} ({})".format(label, representation["name"])
        return label

    def _get_loader_icon(self, loader):
        """Pull icon info from loader class"""
        # Support font-awesome icons using the `.icon` and `.color`
        # attributes on plug-ins.
        icon = getattr(loader, "icon", None)
        if icon is not None and not isinstance(icon, dict):
            icon = {
                "type": "awesome-font",
                "name": icon,
                "color": getattr(loader, "color", None) or "white"
            }
        return icon

    def _get_loader_tooltip(self, loader):
        # Add tooltip and statustip from Loader docstring
        return inspect.getdoc(loader)

    def _filter_loaders_by_tool_name(self, loaders):
        if not self._tool_name:
            return loaders
        filtered_loaders = []
        for loader in loaders:
            tool_names = getattr(loader, "tool_names", None)
            if (
                tool_names is None
                or "*" in tool_names
                or self._tool_name in tool_names
            ):
                filtered_loaders.append(loader)
        return filtered_loaders

    def _create_loader_action_item(
        self,
        loader,
        contexts,
        project_name,
        folder_ids=None,
        product_ids=None,
        version_ids=None,
        representation_ids=None
    ):
        return ActionItem(
            get_loader_identifier(loader),
            label=self._get_loader_label(loader),
            icon=self._get_loader_icon(loader),
            tooltip=self._get_loader_tooltip(loader),
            options=loader.get_options(contexts),
            order=loader.order,
            project_name=project_name,
            folder_ids=folder_ids,
            product_ids=product_ids,
            version_ids=version_ids,
            representation_ids=representation_ids,
        )

    def _get_loaders(self, project_name):
        """

        TODOs:
            Cache loaders for time period and reset them on controller
                refresh.
            Cache them per project name. Right now they are collected per
                project, but not cached per project.

        Questions:
            Project name is required because of settings. Should be actually
                pass in current project name instead of project name where
                we want to show loaders for?
        """

        loaders_by_identifier_c = self._loaders_by_identifier[project_name]
        product_loaders_c = self._product_loaders[project_name]
        repre_loaders_c = self._repre_loaders[project_name]
        if loaders_by_identifier_c.is_valid:
            return product_loaders_c.get_data(), repre_loaders_c.get_data()

        # Get all representation->loader combinations available for the
        # index under the cursor, so we can list the user the options.
        available_loaders = self._filter_loaders_by_tool_name(
            discover_loader_plugins(project_name)
        )

        repre_loaders = []
        product_loaders = []
        loaders_by_identifier = {}
        for loader_cls in available_loaders:
            if not loader_cls.enabled:
                continue

            identifier = get_loader_identifier(loader_cls)
            loaders_by_identifier[identifier] = loader_cls
            if issubclass(loader_cls, SubsetLoaderPlugin):
                product_loaders.append(loader_cls)
            else:
                repre_loaders.append(loader_cls)

        loaders_by_identifier_c.update_data(loaders_by_identifier)
        product_loaders_c.update_data(product_loaders)
        repre_loaders_c.update_data(repre_loaders)
        return product_loaders, repre_loaders

    def _get_loader_by_identifier(self, project_name, identifier):
        loaders_by_identifier_c = self._loaders_by_identifier[project_name]
        if not loaders_by_identifier_c.is_valid:
            self._get_loaders(project_name)
        loaders_by_identifier = loaders_by_identifier_c.get_data()
        return loaders_by_identifier.get(identifier)

    def _actions_sorter(self, action_item):
        """Sort the Loaders by their order and then their name"""

        return action_item.order, action_item.label

    def _contexts_for_versions(self, project_name, version_ids):
        _version_docs = get_versions(project_name, version_ids)
        version_docs_by_id = {}
        version_docs_by_product_id = collections.defaultdict(list)
        for version_doc in _version_docs:
            version_id = version_doc["_id"]
            product_id = version_doc["parent"]
            version_docs_by_id[version_id] = version_doc
            version_docs_by_product_id[product_id].append(version_doc)

        _product_ids = set(version_docs_by_product_id.keys())
        _product_docs = get_subsets(project_name, subset_ids=_product_ids)
        product_docs_by_id = {p["_id"]: p for p in _product_docs}

        _folder_ids = {p["parent"] for p in product_docs_by_id.values()}
        _folder_docs = get_assets(project_name, asset_ids=_folder_ids)
        folder_docs_by_id = {f["_id"]: f for f in _folder_docs}

        project_doc = get_project(project_name)
        project_doc["code"] = project_doc["data"]["code"]

        repre_context_by_id = {}
        product_context_by_id = {}
        for product_id, product_doc in product_docs_by_id.items():
            folder_id = product_doc["parent"]
            folder_doc = folder_docs_by_id[folder_id]
            product_context_by_id[product_id] = {
                "project": project_doc,
                "asset": folder_doc,
                "subset": product_doc,
            }

        repre_docs = get_representations(
            project_name, version_ids=version_ids)
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            version_doc = version_docs_by_id[version_id]
            product_id = version_doc["parent"]
            product_doc = product_docs_by_id[product_id]
            folder_id = product_doc["parent"]
            folder_doc = folder_docs_by_id[folder_id]

            repre_context_by_id[repre_doc["_id"]] = {
                "project": project_doc,
                "asset": folder_doc,
                "subset": product_doc,
                "version": version_doc,
                "representation": repre_doc,
            }

        return product_context_by_id, repre_context_by_id

    def _trigger_product_loader(
        self,
        loader,
        options,
        project_name,
        folder_ids,
        product_ids,
    ):
        project_doc = get_project(project_name)
        project_doc["code"] = project_doc["data"]["code"]
        folder_docs = get_assets(project_name, asset_ids=folder_ids)
        folder_docs_by_id = {f["_id"]: f for f in folder_docs}
        product_docs = get_subsets(project_name, subset_ids=product_ids)
        product_contexts = []
        for product_doc in product_docs:
            folder_id = product_doc["parent"]
            folder_doc = folder_docs_by_id[folder_id]
            product_contexts.append({
                "project": project_doc,
                "asset": folder_doc,
                "subset": product_doc,
            })

        if loader.is_multiple_contexts_compatible:
            load_with_subset_contexts(loader, product_contexts, options)
        else:
            for product_context in product_contexts:
                load_with_subset_context(loader, product_context, options)

    def _trigger_representation_loader(
        self,
        loader,
        options,
        project_name,
        folder_ids,
        product_ids,
        version_ids,
        representation_ids,
    ):
        project_doc = get_project(project_name)
        project_doc["code"] = project_doc["data"]["code"]
        folder_docs = get_assets(project_name, asset_ids=folder_ids)
        folder_docs_by_id = {f["_id"]: f for f in folder_docs}
        product_docs = get_subsets(project_name, subset_ids=product_ids)
        product_docs_by_id = {p["_id"]: p for p in product_docs}
        version_docs = get_versions(project_name, version_ids=version_ids)
        version_docs_by_id = {v["_id"]: v for v in version_docs}
        repre_docs = get_representations(
            project_name, representation_ids=representation_ids
        )
        repre_contexts = []
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            version_doc = version_docs_by_id[version_id]
            product_id = version_doc["parent"]
            product_doc = product_docs_by_id[product_id]
            folder_id = product_doc["parent"]
            folder_doc = folder_docs_by_id[folder_id]
            repre_contexts.append({
                "project": project_doc,
                "asset": folder_doc,
                "subset": product_doc,
                "version": version_doc,
                "representation": repre_doc,
            })

        for repre_context in repre_contexts:
            load_with_repre_context(loader, repre_context, options=options)
