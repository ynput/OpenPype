import os
import re
import collections
import copy
from abc import ABCMeta, abstractmethod

import six

from openpype.client import (
    get_asset_by_name,
    get_linked_assets,
    get_representations,
)
from openpype.settings import get_project_settings
from openpype.host import HostBase
from openpype.lib import (
    Logger,
    StringTemplate,
    filter_profiles,
    attribute_definitions,
)
from openpype.lib.attribute_definitions import get_attributes_keys
from openpype.pipeline import legacy_io, Anatomy
from openpype.pipeline.load import (
    get_loaders_by_name,
    get_contexts_for_repre_docs,
    load_with_repre_context,
)
from openpype.pipeline.create import get_legacy_creator_by_name

from .build_template_exceptions import (
    TemplateProfileNotFound,
    TemplateLoadingFailed,
    TemplateNotFound,
)


@six.add_metaclass(ABCMeta)
class AbstractTemplateLoader:
    """Abstraction of Template Loader.

    Args:
        host (Union[HostBase, ModuleType]): Implementation of host.
    """

    _log = None

    def __init__(self, host):
        # Get host name
        if isinstance(host, HostBase):
            host_name = host.name
        else:
            host_name = os.environ.get("AVALON_APP")

        self._host = host
        self._host_name = host_name

        # Shared data across placeholder plugins
        self._shared_data = {}
        self._shared_populate_data = {}

        # Where created objects of placeholder plugins will be stored
        self._placeholder_plugins = None
        self._loaders_by_name = None
        self._creators_by_name = None

        self._current_asset_doc = None
        self._linked_asset_docs = None
        self._task_type = None

    @property
    def project_name(self):
        return legacy_io.active_project()

    @property
    def current_asset_name(self):
        return legacy_io.Session["AVALON_ASSET"]

    @property
    def current_task_name(self):
        return legacy_io.Session["AVALON_TASK"]

    @property
    def current_asset_doc(self):
        if self._current_asset_doc is None:
            self._current_asset_doc = get_asset_by_name(
                self.project_name, self.current_asset_name
            )
        return self._current_asset_doc

    @property
    def linked_asset_docs(self):
        if self._linked_asset_docs is None:
            self._linked_asset_docs = get_linked_assets(
                self.current_asset_doc
            )
        return self._linked_asset_docs

    @property
    def current_task_type(self):
        asset_doc = self.current_asset_doc
        if not asset_doc:
            return None
        return (
            asset_doc
            .get("data", {})
            .get("tasks", {})
            .get(self.current_task_name, {})
            .get("type")
        )

    def get_placeholder_plugin_classes(self):
        """Get placeholder plugin classes that can be used to build template.

        Default implementation looks for method
            'get_workfile_build_placeholder_plugins' on host.

        Returns:
            List[PlaceholderPlugin]: Plugin classes available for host.
        """

        if hasattr(self._host, "get_workfile_build_placeholder_plugins"):
            return self._host.get_workfile_build_placeholder_plugins()
        return []

    @property
    def host(self):
        """Access to host implementation.

        Returns:
            Union[HostBase, ModuleType]: Implementation of host.
        """

        return self._host

    @property
    def host_name(self):
        """Name of 'host' implementation.

        Returns:
            str: Host's name.
        """

        return self._host_name

    @property
    def log(self):
        """Dynamically created logger for the plugin."""

        if self._log is None:
            self._log = Logger.get_logger(repr(self))
        return self._log

    def refresh(self):
        """Reset cached data."""

        self._placeholder_plugins = None
        self._loaders_by_name = None
        self._creators_by_name = None

        self._current_asset_doc = None
        self._linked_asset_docs = None
        self._task_type = None

        self.clear_shared_data()
        self.clear_shared_populate_data()

    def get_loaders_by_name(self):
        if self._loaders_by_name is None:
            self._loaders_by_name = get_loaders_by_name()
        return self._loaders_by_name

    def get_creators_by_name(self):
        if self._creators_by_name is None:
            self._creators_by_name = get_legacy_creator_by_name()
        return self._creators_by_name

    def get_shared_data(self, key):
        """Receive shared data across plugins and placeholders.

        This can be used to scroll scene only once to look for placeholder
        items if the storing is unified but each placeholder plugin would have
        to call it again.

        Args:
            key (str): Key under which are shared data stored.

        Returns:
            Union[None, Any]: None if key was not set.
        """

        return self._shared_data.get(key)

    def set_shared_data(self, key, value):
        """Store share data across plugins and placeholders.

        Store data that can be afterwards accessed from any future call. It
        is good practice to check if the same value is not already stored under
        different key or if the key is not already used for something else.

        Key should be self explanatory to content.
        - wrong: 'asset'
        - good: 'asset_name'

        Args:
            key (str): Key under which is key stored.
            value (Any): Value that should be stored under the key.
        """

        self._shared_data[key] = value

    def clear_shared_data(self):
        """Clear shared data.

        Method only clear shared data to default state.
        """

        self._shared_data = {}

    def clear_shared_populate_data(self):
        """Receive shared data across plugins and placeholders.

        These data are cleared after each loop of populating of template.

        This can be used to scroll scene only once to look for placeholder
        items if the storing is unified but each placeholder plugin would have
        to call it again.

        Args:
            key (str): Key under which are shared data stored.

        Returns:
            Union[None, Any]: None if key was not set.
        """

        self._shared_populate_data = {}

    def get_shared_populate_data(self, key):
        """Store share populate data across plugins and placeholders.

        These data are cleared after each loop of populating of template.

        Store data that can be afterwards accessed from any future call. It
        is good practice to check if the same value is not already stored under
        different key or if the key is not already used for something else.

        Key should be self explanatory to content.
        - wrong: 'asset'
        - good: 'asset_name'

        Args:
            key (str): Key under which is key stored.
            value (Any): Value that should be stored under the key.
        """

        return self._shared_populate_data.get(key)

    def set_shared_populate_data(self, key, value):
        """Store share populate data across plugins and placeholders.

        These data are cleared after each loop of populating of template.

        Store data that can be afterwards accessed from any future call. It
        is good practice to check if the same value is not already stored under
        different key or if the key is not already used for something else.

        Key should be self explanatory to content.
        - wrong: 'asset'
        - good: 'asset_name'

        Args:
            key (str): Key under which is key stored.
            value (Any): Value that should be stored under the key.
        """

        self._shared_populate_data[key] = value

    @property
    def placeholder_plugins(self):
        """Access to initialized placeholder plugins.

        Returns:
            List[PlaceholderPlugin]: Initialized plugins available for host.
        """

        if self._placeholder_plugins is None:
            placeholder_plugins = {}
            for cls in self.get_placeholder_plugin_classes():
                try:
                    plugin = cls(self)
                    placeholder_plugins[plugin.identifier] = plugin

                except Exception:
                    self.log.warning(
                        "Failed to initialize placeholder plugin {}".format(
                            cls.__name__
                        ),
                        exc_info=True
                    )

            self._placeholder_plugins = placeholder_plugins
        return self._placeholder_plugins

    def create_placeholder(self, plugin_identifier, placeholder_data):
        """Create new placeholder using plugin identifier and data.

        Args:
            plugin_identifier (str): Identifier of plugin. That's how builder
                know which plugin should be used.
            placeholder_data (Dict[str, Any]): Placeholder item data. They
                should match options required by the plugin.

        Returns:
            PlaceholderItem: Created placeholder item.
        """

        plugin = self.placeholder_plugins[plugin_identifier]
        return plugin.create_placeholder(placeholder_data)

    def get_placeholders(self):
        """Collect placeholder items from scene.

        Each placeholder plugin can collect it's placeholders and return them.
        This method does not use cached values but always go through the scene.

        Returns:
            List[PlaceholderItem]: Sorted placeholder items.
        """

        placeholders = []
        for placeholder_plugin in self.placeholder_plugins.values():
            result = placeholder_plugin.collect_placeholders()
            if result:
                placeholders.extend(result)

        return list(sorted(
            placeholders,
            key=lambda i: i.order
        ))

    def build_template(self, template_path=None, level_limit=None):
        if template_path is None:
            template_path = self.get_template_path()
        self.import_template(template_path)
        self.populate_scene_placeholders(level_limit)

    def rebuild_template(self):
        """Go through existing placeholders in scene and update them.

        This could not make sense for all plugin types so this is optional
        logic for plugins.

        Note:
            Logic is not importing the template again but using placeholders
                that were already available. We should maybe change the method
                name.

        Question:
            Should this also handle subloops as it is possible that another
                template is loaded during processing?
        """

        if not self.placeholder_plugins:
            self.log.info("There are no placeholder plugins available.")
            return

        placeholders = self.get_placeholders()
        if not placeholders:
            self.log.info("No placeholders were found.")
            return

        for placeholder in placeholders:
            plugin = placeholder.plugin
            plugin.update_template_placeholder(placeholder)

        self.clear_shared_populate_data()

    @abstractmethod
    def import_template(self, template_path):
        """
        Import template in current host.

        Should load the content of template into scene so
        'populate_scene_placeholders' can be started.

        Args:
            template_path (str): Fullpath for current task and
                host's template file.
        """

        pass

    def _prepare_placeholders(self, placeholders):
        """Run preparation part for placeholders on plugins.

        Args:
            placeholders (List[PlaceholderItem]): Placeholder items that will
                be processed.
        """

        # Prepare placeholder items by plugin
        plugins_by_identifier = {}
        placeholders_by_plugin_id = collections.defaultdict(list)
        for placeholder in placeholders:
            plugin = placeholder.plugin
            identifier = plugin.identifier
            plugins_by_identifier[identifier] = plugin
            placeholders_by_plugin_id[identifier].append(placeholder)

        # Plugin should prepare data for passed placeholders
        for identifier, placeholders in placeholders_by_plugin_id.items():
            plugin = plugins_by_identifier[identifier]
            plugin.prepare_placeholders(placeholders)

    def populate_scene_placeholders(self, level_limit=None):
        """Find placeholders in scene using plugins and process them.

        This should happen after 'import_template'.

        Collect available placeholders from scene. All of them are processed
        after that shared data are cleared. Placeholder items are collected
        again and if there are any new the loop happens again. This is possible
        to change with defying 'level_limit'.

        Placeholders are marked as processed so they're not re-processed. To
        identify which placeholders were already processed is used
        placeholder's 'scene_identifier'.

        Args:
            level_limit (int): Level of loops that can happen. Default is 1000.
        """

        if not self.placeholder_plugins:
            self.log.warning("There are no placeholder plugins available.")
            return

        placeholders = self.get_placeholders()
        if not placeholders:
            self.log.warning("No placeholders were found.")
            return

        # Avoid infinite loop
        # - 1000 iterations of placeholders processing must be enough
        if not level_limit:
            level_limit = 1000

        placeholder_by_scene_id = {
            placeholder.scene_identifier: placeholder
            for placeholder in placeholders
        }
        all_processed = len(placeholders) == 0
        iter_counter = 0
        while not all_processed:
            filtered_placeholders = []
            for placeholder in placeholders:
                if placeholder.finished:
                    continue

                if placeholder.in_progress:
                    self.log.warning((
                        "Placeholder that should be processed"
                        " is already in progress."
                    ))
                    continue
                filtered_placeholders.append(placeholder)

            self._prepare_placeholders(filtered_placeholders)

            for placeholder in filtered_placeholders:
                placeholder.set_in_progress()
                placeholder_plugin = placeholder.plugin
                try:
                    placeholder_plugin.populate_placeholder(placeholder)

                except Exception as exc:
                    self.log.warning(
                        (
                            "Failed to process placeholder {} with plugin {}"
                        ).format(
                            placeholder.scene_identifier,
                            placeholder_plugin.__class__.__name__
                        ),
                        exc_info=True
                    )
                    placeholder.set_failed(exc)

                placeholder.set_finished()

            # Clear shared data before getting new placeholders
            self.clear_shared_populate_data()

            iter_counter += 1
            if iter_counter >= level_limit:
                break

            all_processed = True
            collected_placeholders = self.get_placeholders()
            for placeholder in collected_placeholders:
                identifier = placeholder.scene_identifier
                if identifier in placeholder_by_scene_id:
                    continue

                all_processed = False
                placeholder_by_scene_id[identifier] = placeholder
                placeholders.append(placeholder)

        self.refresh()

    def _get_build_profiles(self):
        project_settings = get_project_settings(self.project_name)
        return (
            project_settings
            [self.host_name]
            ["templated_workfile_build"]
            ["profiles"]
        )

    def get_template_path(self):
        host_name = self.host_name
        project_name = self.project_name
        task_name = self.current_task_name
        task_type = self.current_task_type

        build_profiles = self._get_build_profiles()
        profile = filter_profiles(
            build_profiles,
            {
                "task_types": task_type,
                "task_names": task_name
            }
        )

        if not profile:
            raise TemplateProfileNotFound((
                "No matching profile found for task '{}' of type '{}' "
                "with host '{}'"
            ).format(task_name, task_type, host_name))

        path = profile["path"]
        if not path:
            raise TemplateLoadingFailed((
                "Template path is not set.\n"
                "Path need to be set in {}\\Template Workfile Build "
                "Settings\\Profiles"
            ).format(host_name.title()))

        # Try fill path with environments and anatomy roots
        anatomy = Anatomy(project_name)
        fill_data = {
            key: value
            for key, value in os.environ.items()
        }
        fill_data["root"] = anatomy.roots
        result = StringTemplate.format_template(path, fill_data)
        if result.solved:
            path = result.normalized()

        if path and os.path.exists(path):
            self.log.info("Found template at: '{}'".format(path))
            return path

        solved_path = None
        while True:
            try:
                solved_path = anatomy.path_remapper(path)
            except KeyError as missing_key:
                raise KeyError(
                    "Could not solve key '{}' in template path '{}'".format(
                        missing_key, path))

            if solved_path is None:
                solved_path = path
            if solved_path == path:
                break
            path = solved_path

        solved_path = os.path.normpath(solved_path)
        if not os.path.exists(solved_path):
            raise TemplateNotFound(
                "Template found in openPype settings for task '{}' with host "
                "'{}' does not exists. (Not found : {})".format(
                    task_name, host_name, solved_path))

        self.log.info("Found template at: '{}'".format(solved_path))

        return solved_path


@six.add_metaclass(ABCMeta)
class PlaceholderPlugin(object):
    label = None
    _log = None

    def __init__(self, builder):
        self._builder = builder

    @property
    def builder(self):
        """Access to builder which initialized the plugin.

        Returns:
            AbstractTemplateLoader: Loader of template build.
        """

        return self._builder

    @property
    def project_name(self):
        return self._builder.project_name

    @property
    def log(self):
        """Dynamically created logger for the plugin."""

        if self._log is None:
            self._log = Logger.get_logger(repr(self))
        return self._log

    @property
    def identifier(self):
        """Identifier which will be stored to placeholder.

        Default implementation uses class name.

        Returns:
            str: Unique identifier of placeholder plugin.
        """

        return self.__class__.__name__

    @abstractmethod
    def create_placeholder(self, placeholder_data):
        """Create new placeholder in scene and get it's item.

        It matters on the plugin implementation if placeholder will use
        selection in scene or create new node.

        Args:
            placeholder_data (Dict[str, Any]): Data that were created
                based on attribute definitions from 'get_placeholder_options'.

        Returns:
            PlaceholderItem: Created placeholder item.
        """

        pass

    @abstractmethod
    def update_placeholder(self, placeholder_item, placeholder_data):
        """Update placeholder item with new data.

        New data should be propagated to object of placeholder item itself
        and also into the scene.

        Reason:
            Some placeholder plugins may require some special way how the
            updates should be propagated to object.

        Args:
            placeholder_item (PlaceholderItem): Object of placeholder that
                should be updated.
            placeholder_data (Dict[str, Any]): Data related to placeholder.
                Should match plugin options.
        """

        pass

    @abstractmethod
    def collect_placeholders(self):
        """Collect placeholders from scene.

        Returns:
            List[PlaceholderItem]: Placeholder objects.
        """

        pass

    def get_placeholder_options(self, options=None):
        """Placeholder options for data showed.

        Returns:
            List[AbtractAttrDef]: Attribute definitions of placeholder options.
        """

        return []

    def get_placeholder_keys(self):
        """Get placeholder keys that are stored in scene.

        Returns:
            Set[str]: Key of placeholder keys that are stored in scene.
        """

        option_keys = get_attributes_keys(self.get_placeholder_options())
        option_keys.add("plugin_identifier")
        return option_keys

    def prepare_placeholders(self, placeholders):
        """Preparation part of placeholders.

        Args:
            placeholders (List[PlaceholderItem]): List of placeholders that
                will be processed.
        """

        pass

    @abstractmethod
    def populate_placeholder(self, placeholder):
        """Process single placeholder item.

        Processing of placeholders is defined by their order thus can't be
        processed in batch.

        Args:
            placeholder (PlaceholderItem): Placeholder that should be
                processed.
        """

        pass

    def update_template_placeholder(self, placeholder):
        """Update scene with current context for passed placeholder.

        Can be used to re-run placeholder logic (if it make sense).
        """

        pass

    def get_plugin_shared_data(self, key):
        """Receive shared data across plugin and placeholders.

        Using shared data from builder but stored under plugin identifier.

        Args:
            key (str): Key under which are shared data stored.

        Returns:
            Union[None, Any]: None if key was not set.
        """

        plugin_data = self.builder.get_shared_data(self.identifier)
        if plugin_data is None:
            return None
        return plugin_data.get(key)

    def set_plugin_shared_data(self, key, value):
        """Store share data across plugin and placeholders.

        Using shared data from builder but stored under plugin identifier.

        Key should be self explanatory to content.
        - wrong: 'asset'
        - good: 'asset_name'

        Args:
            key (str): Key under which is key stored.
            value (Any): Value that should be stored under the key.
        """

        plugin_data = self.builder.get_shared_data(self.identifier)
        if plugin_data is None:
            plugin_data = {}
        plugin_data[key] = value
        self.builder.set_shared_data(self.identifier, plugin_data)

    def get_plugin_shared_populate_data(self, key):
        """Receive shared data across plugin and placeholders.

        Using shared populate data from builder but stored under plugin
        identifier.

        Shared populate data are cleaned up during populate while loop.

        Args:
            key (str): Key under which are shared data stored.

        Returns:
            Union[None, Any]: None if key was not set.
        """

        plugin_data = self.builder.get_shared_populate_data(self.identifier)
        if plugin_data is None:
            return None
        return plugin_data.get(key)

    def set_plugin_shared_populate_data(self, key, value):
        """Store share data across plugin and placeholders.

        Using shared data from builder but stored under plugin identifier.

        Key should be self explanatory to content.
        - wrong: 'asset'
        - good: 'asset_name'

        Shared populate data are cleaned up during populate while loop.

        Args:
            key (str): Key under which is key stored.
            value (Any): Value that should be stored under the key.
        """

        plugin_data = self.builder.get_shared_populate_data(self.identifier)
        if plugin_data is None:
            plugin_data = {}
        plugin_data[key] = value
        self.builder.set_shared_populate_data(self.identifier, plugin_data)


class PlaceholderItem(object):
    """Item representing single item in scene that is a placeholder to process.

    Scene identifier is used to avoid processing of the palceholder item
    multiple times.

    Args:
        scene_identifier (str): Unique scene identifier. If placeholder is
            created from the same "node" it must have same identifier.
        data (Dict[str, Any]): Data related to placeholder. They're defined
            by plugin.
        plugin (PlaceholderPlugin): Plugin which created the placeholder item.
    """

    default_order = 100

    def __init__(self, scene_identifier, data, plugin):
        self._log = None
        self._scene_identifier = scene_identifier
        self._data = data
        self._plugin = plugin

        # Keep track about state of Placeholder process
        self._state = 0

        # Error messages to be shown in UI
        # - all other messages should be logged
        self._errors = []  # -> List[str]

    @property
    def plugin(self):
        """Access to plugin which created placeholder.

        Returns:
            PlaceholderPlugin: Plugin object.
        """

        return self._plugin

    @property
    def builder(self):
        """Access to builder.

        Returns:
            AbstractTemplateLoader: Builder which is the top part of
                placeholder.
        """

        return self.plugin.builder

    @property
    def data(self):
        """Placeholder data which can modify how placeholder is processed.

        Possible general keys
        - order: Can define the order in which is palceholder processed.
                    Lower == earlier.

        Other keys are defined by placeholder and should validate them on item
        creation.

        Returns:
            Dict[str, Any]: Placeholder item data.
        """

        return self._data

    def to_dict(self):
        """Create copy of item's data.

        Returns:
            Dict[str, Any]: Placeholder data.
        """

        return copy.deepcopy(self.data)

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(repr(self))
        return self._log

    def __repr__(self):
        return "< {} {} >".format(self.__class__.__name__, self.name)

    @property
    def order(self):
        order = self._data.get("order")
        if order is None:
            return self.default_order
        return order

    @property
    def scene_identifier(self):
        return self._scene_identifier

    @property
    def finished(self):
        """Item was already processed."""

        return self._state == 2

    @property
    def in_progress(self):
        """Processing is in progress."""

        return self._state == 1

    def set_in_progress(self):
        """Change to in progress state."""

        self._state = 1

    def set_finished(self):
        """Change to finished state."""

        self._state = 2

    def set_failed(self, exception):
        self.add_error(str(exception))

    def add_error(self, error):
        """Set placeholder item as failed and mark it as finished."""

        self._errors.append(error)

    def get_errors(self):
        """Exception with which the placeholder process failed.

        Gives ability to access the exception.
        """

        return self._errors


class PlaceholderLoadMixin(object):
    """Mixin prepared for loading placeholder plugins.

    Implementation prepares options for placeholders with
    'get_load_plugin_options'.

    For placeholder population is implemented 'populate_load_placeholder'.

    Requires that PlaceholderItem has implemented methods:
    - 'load_failed' - called when loading of one representation failed
    - 'load_succeed' - called when loading of one representation succeeded
    - 'clean' - called when placeholder processing finished
    """

    def get_load_plugin_options(self, options=None):
        """Unified attribute definitions for load placeholder.

        Common function for placeholder plugins used for loading of
        repsentations. Use it in 'get_placeholder_options'.

        Args:
            plugin (PlaceholderPlugin): Plugin used for loading of
                representations.
            options (Dict[str, Any]): Already available options which are used
                as defaults for attributes.

        Returns:
            List[AbtractAttrDef]: Attribute definitions common for load
                plugins.
        """

        loaders_by_name = self.builder.get_loaders_by_name()
        loader_items = [
            (loader_name, loader.label or loader_name)
            for loader_name, loader in loaders_by_name.items()
        ]

        loader_items = list(sorted(loader_items, key=lambda i: i[1]))
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

    def parse_loader_args(self, loader_args):
        """Helper function to parse string of loader arugments.

        Empty dictionary is returned if conversion fails.

        Args:
            loader_args (str): Loader args filled by user.

        Returns:
            Dict[str, Any]: Parsed arguments used as dictionary.
        """

        if not loader_args:
            return {}

        try:
            parsed_args = eval(loader_args)
            if isinstance(parsed_args, dict):
                return parsed_args

        except Exception as err:
            print(
                "Error while parsing loader arguments '{}'.\n{}: {}\n\n"
                "Continuing with default arguments. . .".format(
                    loader_args, err.__class__.__name__, err))

        return {}

    def get_representations(self, placeholder):
        project_name = self.builder.project_name
        current_asset_doc = self.builder.current_asset_doc
        linked_asset_docs = self.builder.linked_asset_docs

        builder_type = placeholder.data["builder_type"]
        if builder_type == "context_asset":
            context_filters = {
                "asset": [current_asset_doc["name"]],
                "subset": [re.compile(placeholder.data["subset"])],
                "hierarchy": [re.compile(placeholder.data["hierarchy"])],
                "representation": [placeholder.data["representation"]],
                "family": [placeholder.data["family"]]
            }

        elif builder_type != "linked_asset":
            context_filters = {
                "asset": [re.compile(placeholder.data["asset"])],
                "subset": [re.compile(placeholder.data["subset"])],
                "hierarchy": [re.compile(placeholder.data["hierarchy"])],
                "representation": [placeholder.data["representation"]],
                "family": [placeholder.data["family"]]
            }

        else:
            asset_regex = re.compile(placeholder.data["asset"])
            linked_asset_names = []
            for asset_doc in linked_asset_docs:
                asset_name = asset_doc["name"]
                if asset_regex.match(asset_name):
                    linked_asset_names.append(asset_name)

            context_filters = {
                "asset": linked_asset_names,
                "subset": [re.compile(placeholder.data["subset"])],
                "hierarchy": [re.compile(placeholder.data["hierarchy"])],
                "representation": [placeholder.data["representation"]],
                "family": [placeholder.data["family"]],
            }

        return list(get_representations(
            project_name,
            context_filters=context_filters
        ))

    def _before_repre_load(self, placeholder, representation):
        """Can be overriden. Is called before representation is loaded."""

        pass

    def _reduce_last_version_repre_docs(self, representations):
        """Reduce representations to last verison."""

        mapping = {}
        for repre_doc in representations:
            repre_context = repre_doc["context"]

            asset_name = repre_context["asset"]
            subset_name = repre_context["subset"]
            version = repre_context.get("version", -1)

            if asset_name not in mapping:
                mapping[asset_name] = {}

            subset_mapping = mapping[asset_name]
            if subset_name not in subset_mapping:
                subset_mapping[subset_name] = collections.defaultdict(list)

            version_mapping = subset_mapping[subset_name]
            version_mapping[version].append(repre_doc)

        output = []
        for subset_mapping in mapping.values():
            for version_mapping in subset_mapping.values():
                last_version = tuple(sorted(version_mapping.keys()))[-1]
                output.extend(version_mapping[last_version])
        return output

    def populate_load_placeholder(self, placeholder, ignore_repre_ids=None):
        """Load placeholder is goind to load matching representations.

        Note:
            Ignore repre ids is to avoid loading the same representation again
            on load. But the representation can be loaded with different loader
            and there could be published new version of matching subset for the
            representation. We should maybe expect containers.

            Also import loaders don't have containers at all...

        Args:
            placeholder (PlaceholderItem): Placeholder item with information
                about requested representations.
            ignore_repre_ids (Iterable[Union[str, ObjectId]]): Representation
                ids that should be skipped.
        """

        if ignore_repre_ids is None:
            ignore_repre_ids = set()

        # TODO check loader existence
        loader_name = placeholder.data["loader"]
        loader_args = placeholder.data["loader_args"]

        placeholder_representations = self.get_representations(placeholder)

        filtered_representations = []
        for representation in self._reduce_last_version_repre_docs(
            placeholder_representations
        ):
            repre_id = str(representation["_id"])
            if repre_id not in ignore_repre_ids:
                filtered_representations.append(representation)

        if not filtered_representations:
            self.log.info((
                "There's no representation for this placeholder: {}"
            ).format(placeholder.scene_identifier))
            return

        repre_load_contexts = get_contexts_for_repre_docs(
            self.project_name, filtered_representations
        )
        loaders_by_name = self.builder.get_loaders_by_name()
        for repre_load_context in repre_load_contexts.values():
            representation = repre_load_context["representation"]
            repre_context = representation["context"]
            self._before_repre_load(
                placeholder, representation
            )
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
                container = load_with_repre_context(
                    loaders_by_name[loader_name],
                    repre_load_context,
                    options=self.parse_loader_args(loader_args)
                )

            except Exception:
                placeholder.load_failed(representation)

            else:
                placeholder.load_succeed(container)
            self.cleanup_placeholder(placeholder)

    def cleanup_placeholder(self, placeholder):
        pass
