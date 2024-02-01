"""Workfile build mechanism using workfile templates.

Build templates are manually prepared using plugin definitions which create
placeholders inside the template which are populated on import.

This approach is very explicit to achive very specific build logic that can be
targeted by task types and names.

Placeholders are created using placeholder plugins which should care about
logic and data of placeholder items. 'PlaceholderItem' is used to keep track
about it's progress.
"""

import os
import re
import collections
import copy
from abc import ABCMeta, abstractmethod

import six

from openpype import AYON_SERVER_ENABLED
from openpype.client import (
    get_asset_by_name,
    get_linked_assets,
    get_representations,
)
from openpype.settings import (
    get_project_settings,
    get_system_settings,
)
from openpype.host import IWorkfileHost, HostBase
from openpype.lib import (
    Logger,
    StringTemplate,
    filter_profiles,
    attribute_definitions,
)
from openpype.lib.attribute_definitions import get_attributes_keys
from openpype.pipeline import Anatomy
from openpype.pipeline.load import (
    get_loaders_by_name,
    get_contexts_for_repre_docs,
    load_with_repre_context,
)

from openpype.pipeline.create import (
    discover_legacy_creator_plugins,
    CreateContext,
)


class TemplateNotFound(Exception):
    """Exception raised when template does not exist."""
    pass


class TemplateProfileNotFound(Exception):
    """Exception raised when current profile
    doesn't match any template profile"""
    pass


class TemplateAlreadyImported(Exception):
    """Error raised when Template was already imported by host for
    this session"""
    pass


class TemplateLoadFailed(Exception):
    """Error raised whend Template loader was unable to load the template"""
    pass


@six.add_metaclass(ABCMeta)
class AbstractTemplateBuilder(object):
    """Abstraction of Template Builder.

    Builder cares about context, shared data, cache, discovery of plugins
    and trigger logic. Provides public api for host workfile build systen.

    Rest of logic is based on plugins that care about collection and creation
    of placeholder items.

    Population of placeholders happens in loops. Each loop will collect all
    available placeholders, skip already populated, and populate the rest.

    Builder item has 2 types of shared data. Refresh lifetime which are cleared
    on refresh and populate lifetime which are cleared after loop of
    placeholder population.

    Args:
        host (Union[HostBase, ModuleType]): Implementation of host.
    """

    _log = None
    use_legacy_creators = False

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
        self._create_context = None

        self._system_settings = None
        self._project_settings = None

        self._current_asset_doc = None
        self._linked_asset_docs = None
        self._task_type = None

    @property
    def project_name(self):
        if isinstance(self._host, HostBase):
            return self._host.get_current_project_name()
        return os.getenv("AVALON_PROJECT")

    @property
    def current_asset_name(self):
        if isinstance(self._host, HostBase):
            return self._host.get_current_asset_name()
        return os.getenv("AVALON_ASSET")

    @property
    def current_task_name(self):
        if isinstance(self._host, HostBase):
            return self._host.get_current_task_name()
        return os.getenv("AVALON_TASK")

    def get_current_context(self):
        if isinstance(self._host, HostBase):
            return self._host.get_current_context()
        return {
            "project_name": self.project_name,
            "asset_name": self.current_asset_name,
            "task_name": self.current_task_name
        }

    @property
    def system_settings(self):
        if self._system_settings is None:
            self._system_settings = get_system_settings()
        return self._system_settings

    @property
    def project_settings(self):
        if self._project_settings is None:
            self._project_settings = get_project_settings(self.project_name)
        return self._project_settings

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
                self.project_name, self.current_asset_doc
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

    @property
    def create_context(self):
        if self._create_context is None:
            self._create_context = CreateContext(
                self.host,
                discover_publish_plugins=False,
                headless=True
            )
        return self._create_context

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

        self._system_settings = None
        self._project_settings = None

        self.clear_shared_data()
        self.clear_shared_populate_data()

    def get_loaders_by_name(self):
        if self._loaders_by_name is None:
            self._loaders_by_name = get_loaders_by_name()
        return self._loaders_by_name

    def _collect_legacy_creators(self):
        creators_by_name = {}
        for creator in discover_legacy_creator_plugins():
            if not creator.enabled:
                continue
            creator_name = creator.__name__
            if creator_name in creators_by_name:
                raise KeyError(
                    "Duplicated creator name {} !".format(creator_name)
                )
            creators_by_name[creator_name] = creator
        self._creators_by_name = creators_by_name

    def _collect_creators(self):
        self._creators_by_name = dict(self.create_context.creators)

    def get_creators_by_name(self):
        if self._creators_by_name is None:
            if self.use_legacy_creators:
                self._collect_legacy_creators()
            else:
                self._collect_creators()

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

    def build_template(
        self,
        template_path=None,
        level_limit=None,
        keep_placeholders=None,
        create_first_version=None,
        workfile_creation_enabled=False
    ):
        """Main callback for building workfile from template path.

        Todo:
            Handle report of populated placeholders from
                'populate_scene_placeholders' to be shown to a user.

        Args:
            template_path (str): Path to a template file with placeholders.
                Template from settings 'get_template_preset' used when not
                passed.
            level_limit (int): Limit of populate loops. Related to
                'populate_scene_placeholders' method.
            keep_placeholders (bool): Add flag to placeholder data for
                hosts to decide if they want to remove
                placeholder after it is used.
            create_first_version (bool): create first version of a workfile
            workfile_creation_enabled (bool): If True, it might create
                                              first version but ignore
                                              process if version is created

        """
        template_preset = self.get_template_preset()

        if template_path is None:
            template_path = template_preset["path"]

        if keep_placeholders is None:
            keep_placeholders = template_preset["keep_placeholder"]
        if create_first_version is None:
            create_first_version = template_preset["create_first_version"]

        # check if first version is created
        created_version_workfile = False
        if create_first_version:
            created_version_workfile = self.create_first_workfile_version()

        # if first version is created, import template
        # and populate placeholders
        if (
            create_first_version
            and workfile_creation_enabled
            and created_version_workfile
        ):
            self.import_template(template_path)
            self.populate_scene_placeholders(
                level_limit, keep_placeholders)

            # save workfile after template is populated
            self.save_workfile(created_version_workfile)

        # ignore process if first workfile is enabled
        # but a version is already created
        if workfile_creation_enabled:
            return

        self.import_template(template_path)
        self.populate_scene_placeholders(
            level_limit, keep_placeholders)

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
            plugin.repopulate_placeholder(placeholder)

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

    def create_first_workfile_version(self):
        """
        Create first version of workfile.

        Should load the content of template into scene so
        'populate_scene_placeholders' can be started.

        Args:
            template_path (str): Fullpath for current task and
                host's template file.
        """
        last_workfile_path = os.environ.get("AVALON_LAST_WORKFILE")
        self.log.info("__ last_workfile_path: {}".format(last_workfile_path))
        if os.path.exists(last_workfile_path):
            # ignore in case workfile existence
            self.log.info("Workfile already exists, skipping creation.")
            return False

        # Create first version
        self.log.info("Creating first version of workfile.")
        self.save_workfile(last_workfile_path)

        # Confirm creation of first version
        return last_workfile_path

    def save_workfile(self, workfile_path):
        """Save workfile in current host."""
        # Save current scene, continue to open file
        if isinstance(self.host, IWorkfileHost):
            self.host.save_workfile(workfile_path)
        else:
            self.host.save_file(workfile_path)

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

    def populate_scene_placeholders(
        self, level_limit=None, keep_placeholders=None
    ):
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
            keep_placeholders (bool): Add flag to placeholder data for
                hosts to decide if they want to remove
                placeholder after it is used.
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
        # Counter is checked at the ned of a loop so the loop happens at least
        #   once.
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

                # add flag for keeping placeholders in scene
                # after they are processed
                placeholder.data["keep_placeholder"] = keep_placeholders

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
        """Get build profiles for workfile build template path.

        Returns:
            List[Dict[str, Any]]: Profiles for template path resolving.
        """

        return (
            self.project_settings
            [self.host_name]
            ["templated_workfile_build"]
            ["profiles"]
        )

    def get_template_preset(self):
        """Unified way how template preset is received usign settings.

        Method is dependent on '_get_build_profiles' which should return filter
        profiles to resolve path to a template. Default implementation looks
        into host settings:
        - 'project_settings/{host name}/templated_workfile_build/profiles'

        Returns:
            str: Path to a template file with placeholders.

        Raises:
            TemplateProfileNotFound: When profiles are not filled.
            TemplateLoadFailed: Profile was found but path is not set.
            TemplateNotFound: Path was set but file does not exists.
        """

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

        # switch to remove placeholders after they are used
        keep_placeholder = profile.get("keep_placeholder")
        create_first_version = profile.get("create_first_version")

        # backward compatibility, since default is True
        if keep_placeholder is None:
            keep_placeholder = True

        if not path:
            raise TemplateLoadFailed((
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
        fill_data["project"] = {
            "name": project_name,
            "code": anatomy.project_code,
        }

        result = StringTemplate.format_template(path, fill_data)
        if result.solved:
            path = result.normalized()

        if path and os.path.exists(path):
            self.log.info("Found template at: '{}'".format(path))
            return {
                "path": path,
                "keep_placeholder": keep_placeholder,
                "create_first_version": create_first_version
            }

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

        return {
            "path": solved_path,
            "keep_placeholder": keep_placeholder,
            "create_first_version": create_first_version
        }


@six.add_metaclass(ABCMeta)
class PlaceholderPlugin(object):
    """Plugin which care about handling of placeholder items logic.

    Plugin create and update placeholders in scene and populate them on
    template import. Populating means that based on placeholder data happens
    a logic in the scene. Most common logic is to load representation using
    loaders or to create instances in scene.
    """

    label = None
    _log = None

    def __init__(self, builder):
        self._builder = builder

    @property
    def builder(self):
        """Access to builder which initialized the plugin.

        Returns:
            AbstractTemplateBuilder: Loader of template build.
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
            List[AbstractAttrDef]: Attribute definitions of
                placeholder options.
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

    def repopulate_placeholder(self, placeholder):
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

    Items are always created and updated by their plugins. Each plugin can use
    modified class of 'PlacehoderItem' but only to add more options instead of
    new other.

    Scene identifier is used to avoid processing of the palceholder item
    multiple times so must be unique across whole workfile builder.

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
            AbstractTemplateBuilder: Builder which is the top part of
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
        return "< {} {} >".format(
            self.__class__.__name__,
            self._scene_identifier
        )

    @property
    def order(self):
        """Order of item processing."""

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

    PlaceholderItem can have implemented methods:
    - 'load_failed' - called when loading of one representation failed
    - 'load_succeed' - called when loading of one representation succeeded
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
            List[AbstractAttrDef]: Attribute definitions common for load
                plugins.
        """

        loaders_by_name = self.builder.get_loaders_by_name()
        loader_items = [
            {"value": loader_name, "label": loader.label or loader_name}
            for loader_name, loader in loaders_by_name.items()
        ]

        loader_items = list(sorted(loader_items, key=lambda i: i["label"]))
        options = options or {}

        # Get families from all loaders excluding "*"
        families = set()
        for loader in loaders_by_name.values():
            families.update(loader.families)
        families.discard("*")

        # Sort for readability
        families = list(sorted(families))

        if AYON_SERVER_ENABLED:
            builder_type_enum_items = [
                {"label": "Current folder", "value": "context_folder"},
                # TODO implement linked folders
                # {"label": "Linked folders", "value": "linked_folders"},
                {"label": "All folders", "value": "all_folders"},
            ]
            build_type_label = "Folder Builder Type"
            build_type_help = (
                "Folder Builder Type\n"
                "\nBuilder type describe what template loader will look"
                " for."
                "\nCurrent Folder: Template loader will look for products"
                " of current context folder (Folder /assets/bob will"
                " find asset)"
                "\nAll folders: All folders matching the regex will be"
                " used."
            )
        else:
            builder_type_enum_items = [
                {"label": "Current asset", "value": "context_asset"},
                {"label": "Linked assets", "value": "linked_asset"},
                {"label": "All assets", "value": "all_assets"},
            ]
            build_type_label = "Asset Builder Type"
            build_type_help = (
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

        attr_defs = [
            attribute_definitions.UISeparatorDef(),
            attribute_definitions.UILabelDef("Main attributes"),
            attribute_definitions.UISeparatorDef(),

            attribute_definitions.EnumDef(
                "builder_type",
                label=build_type_label,
                default=options.get("builder_type"),
                items=builder_type_enum_items,
                tooltip=build_type_help
            ),
            attribute_definitions.EnumDef(
                "family",
                label="Family",
                default=options.get("family"),
                items=families
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
        ]
        if AYON_SERVER_ENABLED:
            attr_defs.extend([
                attribute_definitions.TextDef(
                    "folder_path",
                    label="Folder filter",
                    default=options.get("folder_path"),
                    placeholder="regex filtering by folder path",
                    tooltip=(
                        "Filtering assets by matching"
                        " field regex to folder path"
                    )
                ),
                attribute_definitions.TextDef(
                    "product_name",
                    label="Product filter",
                    default=options.get("product_name"),
                    placeholder="regex filtering by product name",
                    tooltip=(
                        "Filtering assets by matching"
                        " field regex to product name"
                    )
                ),
            ])
        else:
            attr_defs.extend([
                attribute_definitions.TextDef(
                    "asset",
                    label="Asset filter",
                    default=options.get("asset"),
                    placeholder="regex filtering by asset name",
                    tooltip=(
                        "Filtering assets by matching"
                        " field regex to asset's name"
                    )
                ),
                attribute_definitions.TextDef(
                    "subset",
                    label="Subset filter",
                    default=options.get("subset"),
                    placeholder="regex filtering by subset name",
                    tooltip=(
                        "Filtering assets by matching"
                        " field regex to subset's name"
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
            ])
        return attr_defs

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

    def _query_by_folder_regex(self, project_name, folder_regex):
        """Query folders by folder path regex.

        WARNING:
            This method will be removed once the same functionality is
                available in ayon-python-api.

        Args:
            project_name (str): Project name.
            folder_regex (str): Regex for folder path.

        Returns:
            list[str]: List of folder paths.
        """

        from ayon_api.graphql_queries import folders_graphql_query
        from openpype.client import get_ayon_server_api_connection

        query = folders_graphql_query({"id"})

        folders_field = None
        for child in query._children:
            if child.path != "project":
                continue

            for project_child in child._children:
                if project_child.path == "project/folders":
                    folders_field = project_child
                    break
            if folders_field:
                break

        if "folderPathRegex" not in query._variables:
            folder_path_regex_var = query.add_variable(
                "folderPathRegex", "String!"
            )
            folders_field.set_filter("pathEx", folder_path_regex_var)

        query.set_variable_value("projectName", project_name)
        if folder_regex:
            query.set_variable_value("folderPathRegex", folder_regex)

        api = get_ayon_server_api_connection()
        for parsed_data in query.continuous_query(api):
            for folder in parsed_data["project"]["folders"]:
                yield folder["id"]

    def _get_representations_ayon(self, placeholder):
        # An OpenPype placeholder loaded in AYON
        if "asset" in placeholder.data:
            return []

        representation_name = placeholder.data["representation"]
        if not representation_name:
            return []

        project_name = self.builder.project_name
        current_asset_doc = self.builder.current_asset_doc

        folder_path_regex = placeholder.data["folder_path"]
        product_name_regex_value = placeholder.data["product_name"]
        product_name_regex = None
        if product_name_regex_value:
            product_name_regex = re.compile(product_name_regex_value)
        product_type = placeholder.data["family"]

        builder_type = placeholder.data["builder_type"]
        folder_ids = []
        if builder_type == "context_folder":
            folder_ids = [current_asset_doc["_id"]]

        elif builder_type == "all_folders":
            folder_ids = list(self._query_by_folder_regex(
                project_name, folder_path_regex
            ))

        if not folder_ids:
            return []

        from ayon_api import get_products, get_last_versions

        products = list(get_products(
            project_name,
            folder_ids=folder_ids,
            product_types=[product_type],
            fields={"id", "name"}
        ))
        filtered_product_ids = set()
        for product in products:
            if (
                product_name_regex is None
                or product_name_regex.match(product["name"])
            ):
                filtered_product_ids.add(product["id"])

        if not filtered_product_ids:
            return []

        version_ids = set(
            version["id"]
            for version in get_last_versions(
                project_name, filtered_product_ids, fields={"id"}
            ).values()
        )
        return list(get_representations(
            project_name,
            representation_names=[representation_name],
            version_ids=version_ids
        ))


    def _get_representations(self, placeholder):
        """Prepared query of representations based on load options.

        This function is directly connected to options defined in
        'get_load_plugin_options'.

        Note:
            This returns all representation documents from all versions of
                matching subset. To filter for last version use
                '_reduce_last_version_repre_docs'.

        Args:
            placeholder (PlaceholderItem): Item which should be populated.

        Returns:
            List[Dict[str, Any]]: Representation documents matching filters
                from placeholder data.
        """

        if AYON_SERVER_ENABLED:
            return self._get_representations_ayon(placeholder)

        # An AYON placeholder loaded in OpenPype
        if "folder_path" in placeholder.data:
            return []

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

        elif builder_type == "linked_asset":
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

        else:
            context_filters = {
                "asset": [re.compile(placeholder.data["asset"])],
                "subset": [re.compile(placeholder.data["subset"])],
                "hierarchy": [re.compile(placeholder.data["hierarchy"])],
                "representation": [placeholder.data["representation"]],
                "family": [placeholder.data["family"]]
            }

        return list(get_representations(
            project_name,
            context_filters=context_filters
        ))

    def _before_placeholder_load(self, placeholder):
        """Can be overridden. It's called before placeholder representations
        are loaded.
        """

        pass

    def _before_repre_load(self, placeholder, representation):
        """Can be overridden. It's called before representation is loaded."""

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
        """Load placeholder is going to load matching representations.

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
        loader_args = self.parse_loader_args(placeholder.data["loader_args"])

        placeholder_representations = self._get_representations(placeholder)

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
        self._before_placeholder_load(
            placeholder
        )

        failed = False
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
                    placeholder.data["loader_args"],
                )
            )
            try:
                container = load_with_repre_context(
                    loaders_by_name[loader_name],
                    repre_load_context,
                    options=loader_args
                )

            except Exception:
                self.load_failed(placeholder, representation)
                failed = True
            else:
                self.load_succeed(placeholder, container)

        # Run post placeholder process after load of all representations
        self.post_placeholder_process(placeholder, failed)

        if failed:
            self.log.debug(
                "Placeholder cleanup skipped due to failed placeholder "
                "population."
            )
            return
        if not placeholder.data.get("keep_placeholder", True):
            self.delete_placeholder(placeholder)

    def load_failed(self, placeholder, representation):
        if hasattr(placeholder, "load_failed"):
            placeholder.load_failed(representation)

    def load_succeed(self, placeholder, container):
        if hasattr(placeholder, "load_succeed"):
            placeholder.load_succeed(container)

    def post_placeholder_process(self, placeholder, failed):
        """Cleanup placeholder after load of its corresponding representations.

        Args:
            placeholder (PlaceholderItem): Item which was just used to load
                representation.
            failed (bool): Loading of representation failed.
        """

        pass

    def delete_placeholder(self, placeholder):
        """Called when all item population is done."""
        self.log.debug("Clean up of placeholder is not implemented.")


class PlaceholderCreateMixin(object):
    """Mixin prepared for creating placeholder plugins.

    Implementation prepares options for placeholders with
    'get_create_plugin_options'.

    For placeholder population is implemented 'populate_create_placeholder'.

    PlaceholderItem can have implemented methods:
    - 'create_failed' - called when creating of an instance failed
    - 'create_succeed' - called when creating of an instance succeeded
    """

    def get_create_plugin_options(self, options=None):
        """Unified attribute definitions for create placeholder.

        Common function for placeholder plugins used for creating of
        publishable instances. Use it with 'get_placeholder_options'.

        Args:
            plugin (PlaceholderPlugin): Plugin used for creating of
                publish instances.
            options (Dict[str, Any]): Already available options which are used
                as defaults for attributes.

        Returns:
            List[AbstractAttrDef]: Attribute definitions common for create
                plugins.
        """

        creators_by_name = self.builder.get_creators_by_name()

        creator_items = [
            (creator_name, creator.label or creator_name)
            for creator_name, creator in creators_by_name.items()
        ]

        creator_items.sort(key=lambda i: i[1])
        options = options or {}
        return [
            attribute_definitions.UISeparatorDef(),
            attribute_definitions.UILabelDef("Main attributes"),
            attribute_definitions.UISeparatorDef(),

            attribute_definitions.EnumDef(
                "creator",
                label="Creator",
                default=options.get("creator"),
                items=creator_items,
                tooltip=(
                    "Creator"
                    "\nDefines what OpenPype creator will be used to"
                    " create publishable instance."
                    "\nUseable creator depends on current host's creator list."
                    "\nField is case sensitive."
                )
            ),
            attribute_definitions.TextDef(
                "create_variant",
                label="Variant",
                default=options.get("create_variant"),
                placeholder='Main',
                tooltip=(
                    "Creator"
                    "\nDefines variant name which will be use for "
                    "\ncompiling of subset name."
                )
            ),
            attribute_definitions.UISeparatorDef(),
            attribute_definitions.NumberDef(
                "order",
                label="Order",
                default=options.get("order") or 0,
                decimals=0,
                minimum=0,
                maximum=999,
                tooltip=(
                    "Order"
                    "\nOrder defines creating instance priority (0 to 999)"
                    "\nPriority rule is : \"lowest is first to load\"."
                )
            )
        ]

    def populate_create_placeholder(self, placeholder, pre_create_data=None):
        """Create placeholder is going to create matching publishabe instance.

        Args:
            placeholder (PlaceholderItem): Placeholder item with information
                about requested publishable instance.
            pre_create_data (dict): dictionary of configuration from Creator
                configuration in UI
        """

        legacy_create = self.builder.use_legacy_creators
        creator_name = placeholder.data["creator"]
        create_variant = placeholder.data["create_variant"]

        creator_plugin = self.builder.get_creators_by_name()[creator_name]

        # create subset name
        context = self._builder.get_current_context()
        project_name = context["project_name"]
        asset_name = context["asset_name"]
        task_name = context["task_name"]

        if legacy_create:
            asset_doc = get_asset_by_name(
                project_name, asset_name, fields=["_id"]
            )
            assert asset_doc, "No current asset found in Session"
            subset_name = creator_plugin.get_subset_name(
                create_variant,
                task_name,
                asset_doc["_id"],
                project_name
            )

        else:
            asset_doc = get_asset_by_name(project_name, asset_name)
            assert asset_doc, "No current asset found in Session"
            subset_name = creator_plugin.get_subset_name(
                create_variant,
                task_name,
                asset_doc,
                project_name,
                self.builder.host_name
            )

        creator_data = {
            "creator_name": creator_name,
            "create_variant": create_variant,
            "subset_name": subset_name,
            "creator_plugin": creator_plugin
        }

        self._before_instance_create(placeholder)

        # compile subset name from variant
        try:
            if legacy_create:
                creator_instance = creator_plugin(
                    subset_name,
                    asset_name
                ).process()
            else:
                creator_instance = self.builder.create_context.create(
                    creator_plugin.identifier,
                    create_variant,
                    asset_doc,
                    task_name=task_name,
                    pre_create_data=pre_create_data
                )

        except:  # noqa: E722
            failed = True
            self.create_failed(placeholder, creator_data)

        else:
            failed = False
            self.create_succeed(placeholder, creator_instance)

        self.post_placeholder_process(placeholder, failed)

        if failed:
            self.log.debug(
                "Placeholder cleanup skipped due to failed placeholder "
                "population."
            )
            return

        if not placeholder.data.get("keep_placeholder", True):
            self.delete_placeholder(placeholder)

    def create_failed(self, placeholder, creator_data):
        if hasattr(placeholder, "create_failed"):
            placeholder.create_failed(creator_data)

    def create_succeed(self, placeholder, creator_instance):
        if hasattr(placeholder, "create_succeed"):
            placeholder.create_succeed(creator_instance)

    def post_placeholder_process(self, placeholder, failed):
        """Cleanup placeholder after load of its corresponding representations.

        Args:
            placeholder (PlaceholderItem): Item which was just used to load
                representation.
            failed (bool): Loading of representation failed.
        """
        pass

    def delete_placeholder(self, placeholder):
        """Called when all item population is done."""
        self.log.debug("Clean up of placeholder is not implemented.")

    def _before_instance_create(self, placeholder):
        """Can be overriden. Is called before instance is created."""

        pass


class LoadPlaceholderItem(PlaceholderItem):
    """PlaceholderItem for plugin which is loading representations.

    Connected to 'PlaceholderLoadMixin'.
    """

    def __init__(self, *args, **kwargs):
        super(LoadPlaceholderItem, self).__init__(*args, **kwargs)
        self._failed_representations = []

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


class CreatePlaceholderItem(PlaceholderItem):
    """PlaceholderItem for plugin which is creating publish instance.

    Connected to 'PlaceholderCreateMixin'.
    """

    def __init__(self, *args, **kwargs):
        super(CreatePlaceholderItem, self).__init__(*args, **kwargs)
        self._failed_created_publish_instances = []

    def get_errors(self):
        if not self._failed_created_publish_instances:
            return []
        message = (
            "Failed to create {} instance using Creator {}"
        ).format(
            len(self._failed_created_publish_instances),
            self.data["creator"]
        )
        return [message]

    def create_failed(self, creator_data):
        self._failed_created_publish_instances.append(creator_data)
