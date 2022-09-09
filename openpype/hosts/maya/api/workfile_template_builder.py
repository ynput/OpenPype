import re
import json

from maya import cmds

from openpype.client import get_representations
from openpype.lib import attribute_definitions
from openpype.pipeline import legacy_io, registered_host
from openpype.pipeline.workfile.build_template_exceptions import (
    TemplateAlreadyImported
)
from openpype.pipeline.workfile.new_template_loader import (
    AbstractTemplateLoader,
    PlaceholderPlugin,
    PlaceholderItem,
)
from openpype.tools.workfile_template_build import (
    WorkfileBuildPlaceholderDialog,
)

from .lib import read, imprint

PLACEHOLDER_SET = "PLACEHOLDERS_SET"


class MayaTemplateLoader(AbstractTemplateLoader):
    """Concrete implementation of AbstractTemplateLoader for maya"""

    def import_template(self, path):
        """Import template into current scene.
        Block if a template is already loaded.

        Args:
            path (str): A path to current template (usually given by
            get_template_path implementation)

        Returns:
            bool: Wether the template was succesfully imported or not
        """

        if cmds.objExists(PLACEHOLDER_SET):
            raise TemplateAlreadyImported((
                "Build template already loaded\n"
                "Clean scene if needed (File > New Scene)"
            ))

        cmds.sets(name=PLACEHOLDER_SET, empty=True)
        cmds.file(path, i=True, returnNewNodes=True)

        cmds.setAttr(PLACEHOLDER_SET + ".hiddenInOutliner", True)

        return True


class MayaLoadPlaceholderPlugin(PlaceholderPlugin):
    identifier = "maya.load"
    label = "Maya load"

    def _collect_scene_placeholders(self):
        # Cache placeholder data to shared data
        placeholder_nodes = self.builder.get_shared_populate_data(
            "placeholder_nodes"
        )
        if placeholder_nodes is None:
            attributes = cmds.ls("*.plugin_identifier", long=True)
            placeholder_nodes = {}
            for attribute in attributes:
                node_name = attribute.rpartition(".")[0]
                placeholder_nodes[node_name] = (
                    self._parse_placeholder_node_data(node_name)
                )

            self.builder.set_shared_populate_data(
                "placeholder_nodes", placeholder_nodes
            )
        return placeholder_nodes

    def _parse_placeholder_node_data(self, node_name):
        placeholder_data = read(node_name)
        parent_name = (
            cmds.getAttr(node_name + ".parent", asString=True)
            or node_name.rpartition("|")[0]
            or ""
        )
        if parent_name:
            siblings = cmds.listRelatives(parent_name, children=True)
        else:
            siblings = cmds.ls(assemblies=True)
        node_shortname = node_name.rpartition("|")[2]
        current_index = cmds.getAttr(node_name + ".index", asString=True)
        if current_index < 0:
            current_index = siblings.index(node_shortname)

        placeholder_data.update({
            "parent": parent_name,
            "index": current_index
        })
        return placeholder_data

    def _create_placeholder_name(self, placeholder_data):
        placeholder_name_parts = placeholder_data["builder_type"].split("_")

        pos = 1
        # add famlily in any
        placeholder_family = placeholder_data["family"]
        if placeholder_family:
            placeholder_name_parts.insert(pos, placeholder_family)
            pos += 1

        # add loader arguments if any
        loader_args = placeholder_data["loader_args"]
        if loader_args:
            loader_args = json.loads(loader_args.replace('\'', '\"'))
            values = [v for v in loader_args.values()]
            for value in values:
                placeholder_name_parts.insert(pos, value)
                pos += 1

        placeholder_name = "_".join(placeholder_name_parts)

        return placeholder_name.capitalize()

    def _get_loaded_repre_ids(self):
        loaded_representation_ids = self.builder.get_shared_populate_data(
            "loaded_representation_ids"
        )
        if loaded_representation_ids is None:
            try:
                containers = cmds.sets("AVALON_CONTAINERS", q=True)
            except ValueError:
                containers = []

            loaded_representation_ids = {
                cmds.getAttr(container + ".representation")
                for container in containers
            }
            self.builder.set_shared_populate_data(
                "loaded_representation_ids", loaded_representation_ids
            )
        return loaded_representation_ids

    def create_placeholder(self, placeholder_data):
        selection = cmds.ls(selection=True)
        if not selection:
            raise ValueError("Nothing is selected")
        if len(selection) > 1:
            raise ValueError("More then one item are selected")

        placeholder_data["plugin_identifier"] = self.identifier

        placeholder_name = self._create_placeholder_name(placeholder_data)

        placeholder = cmds.spaceLocator(name=placeholder_name)[0]
        # TODO: this can crash if selection can't be used
        cmds.parent(placeholder, selection[0])

        # get the long name of the placeholder (with the groups)
        placeholder_full_name = (
            cmds.ls(selection[0], long=True)[0]
            + "|"
            + placeholder.replace("|", "")
        )

        imprint(placeholder_full_name, placeholder_data)

        # Add helper attributes to keep placeholder info
        cmds.addAttr(
            placeholder_full_name,
            longName="parent",
            hidden=True,
            dataType="string"
        )
        cmds.addAttr(
            placeholder_full_name,
            longName="index",
            hidden=True,
            attributeType="short",
            defaultValue=-1
        )

        cmds.setAttr(placeholder_full_name + ".parent", "", type="string")

    def update_placeholder(self, placeholder_item, placeholder_data):
        node_name = placeholder_item.scene_identifier
        new_values = {}
        for key, value in placeholder_data.items():
            placeholder_value = placeholder_item.data.get(key)
            if value != placeholder_value:
                new_values[key] = value
                placeholder_item.data[key] = value

        for key in new_values.keys():
            cmds.deleteAttr(node_name + "." + key)

        imprint(node_name, new_values)

    def collect_placeholders(self):
        output = []
        scene_placeholders = self._collect_scene_placeholders()
        for node_name, placeholder_data in scene_placeholders.items():
            if placeholder_data.get("plugin_identifier") != self.identifier:
                continue

            # TODO do data validations and maybe updgrades if are invalid
            output.append(
                LoadPlaceholder(node_name, placeholder_data, self)
            )

        return output

    def populate_placeholder(self, placeholder):
        self._populate_placeholder(placeholder)

    def update_template_placeholder(self, placeholder):
        repre_ids = self._get_loaded_repre_ids()
        self._populate_placeholder(placeholder, repre_ids)

    def _populate_placeholder(self, placeholder, ignore_repre_ids=None):
        if ignore_repre_ids is None:
            ignore_repre_ids = set()

        current_asset_doc = self.builder.current_asset_doc
        linked_assets = self.builder.linked_asset_docs
        loader_name = placeholder.data["loader"]
        loader_args = placeholder.data["loader_args"]

        # TODO check loader existence
        placeholder_representations = placeholder.get_representations(
            current_asset_doc,
            linked_assets
        )

        if not placeholder_representations:
            self.log.info((
                "There's no representation for this placeholder: {}"
            ).format(placeholder.scene_identifier))
            return

        loaders_by_name = self.builder.get_loaders_by_name()
        for representation in placeholder_representations:
            repre_id = str(representation["_id"])
            if repre_id in ignore_repre_ids:
                continue

            repre_context = representation["context"]
            self.log.info(
                "Loading {} from {} with loader {}\n"
                "Loader arguments used : {}".format(
                    repre_context["subset"],
                    repre_context["asset"],
                    loader_name,
                    loader_args
                )
            )
            try:
                container = self.load(
                    placeholder, loaders_by_name, representation)
            except Exception:
                placeholder.load_failed(representation)

            else:
                placeholder.load_succeed(container)
            placeholder.clean()

    def get_placeholder_options(self, options=None):
        loaders_by_name = self.builder.get_loaders_by_name()
        loader_items = [
            (loader_name, loader.label or loader_name)
            for loader_name, loader in loaders_by_name.items()
        ]

        loader_items = list(sorted(loader_items, key=lambda i: i[0]))
        options = options or {}
        return [
            attribute_definitions.UISeparatorDef(),
            attribute_definitions.UILabelDef("Main attributes"),
            attribute_definitions.UISeparatorDef(),

            attribute_definitions.EnumDef(
                "builder_type",
                label="Asset Builder Type",
                default=options.get("builder_type"),
                items=[
                    ("context_asset", "Current asset"),
                    ("linked_asset", "Linked assets"),
                    ("all_assets", "All assets")
                ],
                tooltip=(
                    "Asset Builder Type\n"
                    "\nBuilder type describe what template loader will look"
                    " for."
                    "\ncontext_asset : Template loader will look for subsets"
                    " of current context asset (Asset bob will find asset)"
                    "\nlinked_asset : Template loader will look for assets"
                    " linked to current context asset."
                    "\nLinked asset are looked in database under"
                    " field \"inputLinks\""
                )
            ),
            attribute_definitions.TextDef(
                "family",
                label="Family",
                default=options.get("family"),
                placeholder="model, look, ..."
            ),
            attribute_definitions.TextDef(
                "representation",
                label="Representation name",
                default=options.get("representation"),
                placeholder="ma, abc, ..."
            ),
            attribute_definitions.EnumDef(
                "loader",
                label="Loader",
                default=options.get("loader"),
                items=loader_items,
                tooltip=(
                    "Loader"
                    "\nDefines what OpenPype loader will be used to"
                    " load assets."
                    "\nUseable loader depends on current host's loader list."
                    "\nField is case sensitive."
                )
            ),
            attribute_definitions.TextDef(
                "loader_args",
                label="Loader Arguments",
                default=options.get("loader_args"),
                placeholder='{"camera":"persp", "lights":True}',
                tooltip=(
                    "Loader"
                    "\nDefines a dictionnary of arguments used to load assets."
                    "\nUseable arguments depend on current placeholder Loader."
                    "\nField should be a valid python dict."
                    " Anything else will be ignored."
                )
            ),
            attribute_definitions.NumberDef(
                "order",
                label="Order",
                default=options.get("order") or 0,
                decimals=0,
                minimum=0,
                maximum=999,
                tooltip=(
                    "Order"
                    "\nOrder defines asset loading priority (0 to 999)"
                    "\nPriority rule is : \"lowest is first to load\"."
                )
            ),
            attribute_definitions.UISeparatorDef(),
            attribute_definitions.UILabelDef("Optional attributes"),
            attribute_definitions.UISeparatorDef(),
            attribute_definitions.TextDef(
                "asset",
                label="Asset filter",
                default=options.get("asset"),
                placeholder="regex filtering by asset name",
                tooltip=(
                    "Filtering assets by matching field regex to asset's name"
                )
            ),
            attribute_definitions.TextDef(
                "subset",
                label="Subset filter",
                default=options.get("subset"),
                placeholder="regex filtering by subset name",
                tooltip=(
                    "Filtering assets by matching field regex to subset's name"
                )
            ),
            attribute_definitions.TextDef(
                "hierarchy",
                label="Hierarchy filter",
                default=options.get("hierarchy"),
                placeholder="regex filtering by asset's hierarchy",
                tooltip=(
                    "Filtering assets by matching field asset's hierarchy"
                )
            )
        ]


class LoadPlaceholder(PlaceholderItem):
    """Concrete implementation of AbstractPlaceholder for maya
    """

    def __init__(self, *args, **kwargs):
        super(LoadPlaceholder, self).__init__(*args, **kwargs)
        self._failed_representations = []

    def parent_in_hierarchy(self, container):
        """Parent loaded container to placeholder's parent.

        ie : Set loaded content as placeholder's sibling

        Args:
            container (str): Placeholder loaded containers
        """

        if not container:
            return

        roots = cmds.sets(container, q=True)
        nodes_to_parent = []
        for root in roots:
            if root.endswith("_RN"):
                refRoot = cmds.referenceQuery(root, n=True)[0]
                refRoot = cmds.listRelatives(refRoot, parent=True) or [refRoot]
                nodes_to_parent.extend(refRoot)
            elif root not in cmds.listSets(allSets=True):
                nodes_to_parent.append(root)

            elif not cmds.sets(root, q=True):
                return

        if self.data["parent"]:
            cmds.parent(nodes_to_parent, self.data["parent"])
        # Move loaded nodes to correct index in outliner hierarchy
        placeholder_form = cmds.xform(
            self._scene_identifier,
            q=True,
            matrix=True,
            worldSpace=True
        )
        for node in set(nodes_to_parent):
            cmds.reorder(node, front=True)
            cmds.reorder(node, relative=self.data["index"])
            cmds.xform(node, matrix=placeholder_form, ws=True)

        holding_sets = cmds.listSets(object=self._scene_identifier)
        if not holding_sets:
            return
        for holding_set in holding_sets:
            cmds.sets(roots, forceElement=holding_set)

    def clean(self):
        """Hide placeholder, parent them to root
        add them to placeholder set and register placeholder's parent
        to keep placeholder info available for future use
        """

        node = self._scene_identifier
        if self.data['parent']:
            cmds.setAttr(node + '.parent', self.data['parent'], type='string')
        if cmds.getAttr(node + '.index') < 0:
            cmds.setAttr(node + '.index', self.data['index'])

        holding_sets = cmds.listSets(object=node)
        if holding_sets:
            for set in holding_sets:
                cmds.sets(node, remove=set)

        if cmds.listRelatives(node, p=True):
            node = cmds.parent(node, world=True)[0]
        cmds.sets(node, addElement=PLACEHOLDER_SET)
        cmds.hide(node)
        cmds.setAttr(node + ".hiddenInOutliner", True)

    def get_representations(self, current_asset_doc, linked_asset_docs):
        project_name = legacy_io.active_project()

        builder_type = self.data["builder_type"]
        if builder_type == "context_asset":
            context_filters = {
                "asset": [current_asset_doc["name"]],
                "subset": [re.compile(self.data["subset"])],
                "hierarchy": [re.compile(self.data["hierarchy"])],
                "representations": [self.data["representation"]],
                "family": [self.data["family"]]
            }

        elif builder_type != "linked_asset":
            context_filters = {
                "asset": [re.compile(self.data["asset"])],
                "subset": [re.compile(self.data["subset"])],
                "hierarchy": [re.compile(self.data["hierarchy"])],
                "representation": [self.data["representation"]],
                "family": [self.data["family"]]
            }

        else:
            asset_regex = re.compile(self.data["asset"])
            linked_asset_names = []
            for asset_doc in linked_asset_docs:
                asset_name = asset_doc["name"]
                if asset_regex.match(asset_name):
                    linked_asset_names.append(asset_name)

            context_filters = {
                "asset": linked_asset_names,
                "subset": [re.compile(self.data["subset"])],
                "hierarchy": [re.compile(self.data["hierarchy"])],
                "representation": [self.data["representation"]],
                "family": [self.data["family"]],
            }

        return list(get_representations(
            project_name,
            context_filters=context_filters
        ))

    def get_errors(self):
        if not self._failed_representations:
            return []
        message = (
            "Failed to load {} representations using Loader {}"
        ).format(
            len(self._failed_representations),
            self.data["loader"]
        )
        return [message]

    def load_failed(self, representation):
        self._failed_representations.append(representation)

    def load_succeed(self, container):
        self.parent_in_hierarchy(container)


def build_workfile_template(*args):
    builder = MayaTemplateLoader(registered_host())
    builder.build_template()


def update_workfile_template(*args):
    builder = MayaTemplateLoader(registered_host())
    builder.rebuild_template()


def create_placeholder(*args):
    host = registered_host()
    builder = MayaTemplateLoader(host)
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.exec_()


def update_placeholder(*args):
    host = registered_host()
    builder = MayaTemplateLoader(host)
    placeholder_items_by_id = {
        placeholder_item.scene_identifier: placeholder_item
        for placeholder_item in builder.get_placeholders()
    }
    placeholder_items = []
    for node_name in cmds.ls(selection=True, long=True):
        if node_name in placeholder_items_by_id:
            placeholder_items.append(placeholder_items_by_id[node_name])

    # TODO show UI at least
    if len(placeholder_items) == 0:
        raise ValueError("No node selected")

    if len(placeholder_items) > 1:
        raise ValueError("Too many selected nodes")

    placeholder_item = placeholder_items[0]
    window = WorkfileBuildPlaceholderDialog(host, builder)
    window.set_update_mode(placeholder_item)
    window.exec_()
