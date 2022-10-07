import os
import copy
import logging
import traceback
import collections
from abc import ABCMeta, abstractmethod, abstractproperty

import six
import pyblish.api

from openpype.client import get_assets
from openpype.lib.events import EventSystem
from openpype.pipeline import (
    PublishValidationError,
    registered_host,
)
from openpype.pipeline.create import CreateContext

# Define constant for plugin orders offset
PLUGIN_ORDER_OFFSET = 0.5


class MainThreadItem:
    """Callback with args and kwargs."""

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.callback(*self.args, **self.kwargs)


class AssetDocsCache:
    """Cache asset documents for creation part."""

    projection = {
        "_id": True,
        "name": True,
        "data.visualParent": True,
        "data.tasks": True
    }

    def __init__(self, controller):
        self._controller = controller
        self._asset_docs = None
        self._task_names_by_asset_name = {}

    def reset(self):
        self._asset_docs = None
        self._task_names_by_asset_name = {}

    def _query(self):
        if self._asset_docs is None:
            project_name = self._controller.project_name
            asset_docs = get_assets(
                project_name, fields=self.projection.keys()
            )
            task_names_by_asset_name = {}
            for asset_doc in asset_docs:
                asset_name = asset_doc["name"]
                asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
                task_names_by_asset_name[asset_name] = list(asset_tasks.keys())
            self._asset_docs = asset_docs
            self._task_names_by_asset_name = task_names_by_asset_name

    def get_asset_docs(self):
        self._query()
        return copy.deepcopy(self._asset_docs)

    def get_task_names_by_asset_name(self):
        self._query()
        return copy.deepcopy(self._task_names_by_asset_name)


class PublishReport:
    """Report for single publishing process.

    Report keeps current state of publishing and currently processed plugin.
    """

    def __init__(self, controller):
        self.controller = controller
        self._publish_discover_result = None
        self._plugin_data = []
        self._plugin_data_with_plugin = []

        self._stored_plugins = []
        self._current_plugin_data = []
        self._all_instances_by_id = {}
        self._current_context = None

    def reset(self, context, create_context):
        """Reset report and clear all data."""

        self._publish_discover_result = create_context.publish_discover_result
        self._plugin_data = []
        self._plugin_data_with_plugin = []
        self._current_plugin_data = {}
        self._all_instances_by_id = {}
        self._current_context = context

        for plugin in create_context.publish_plugins_mismatch_targets:
            plugin_data = self._add_plugin_data_item(plugin)
            plugin_data["skipped"] = True

    def add_plugin_iter(self, plugin, context):
        """Add report about single iteration of plugin."""
        for instance in context:
            self._all_instances_by_id[instance.id] = instance

        if self._current_plugin_data:
            self._current_plugin_data["passed"] = True

        self._current_plugin_data = self._add_plugin_data_item(plugin)

    def _get_plugin_data_item(self, plugin):
        store_item = None
        for item in self._plugin_data_with_plugin:
            if item["plugin"] is plugin:
                store_item = item["data"]
                break
        return store_item

    def _add_plugin_data_item(self, plugin):
        if plugin in self._stored_plugins:
            raise ValueError("Plugin is already stored")

        self._stored_plugins.append(plugin)

        plugin_data_item = self._create_plugin_data_item(plugin)

        self._plugin_data_with_plugin.append({
            "plugin": plugin,
            "data": plugin_data_item
        })
        self._plugin_data.append(plugin_data_item)
        return plugin_data_item

    def _create_plugin_data_item(self, plugin):
        label = None
        if hasattr(plugin, "label"):
            label = plugin.label

        return {
            "name": plugin.__name__,
            "label": label,
            "order": plugin.order,
            "targets": list(plugin.targets),
            "instances_data": [],
            "actions_data": [],
            "skipped": False,
            "passed": False
        }

    def set_plugin_skipped(self):
        """Set that current plugin has been skipped."""
        self._current_plugin_data["skipped"] = True

    def add_result(self, result):
        """Handle result of one plugin and it's instance."""
        instance = result["instance"]
        instance_id = None
        if instance is not None:
            instance_id = instance.id
        self._current_plugin_data["instances_data"].append({
            "id": instance_id,
            "logs": self._extract_instance_log_items(result)
        })

    def add_action_result(self, action, result):
        """Add result of single action."""
        plugin = result["plugin"]

        store_item = self._get_plugin_data_item(plugin)
        if store_item is None:
            store_item = self._add_plugin_data_item(plugin)

        action_name = action.__name__
        action_label = action.label or action_name
        log_items = self._extract_log_items(result)
        store_item["actions_data"].append({
            "success": result["success"],
            "name": action_name,
            "label": action_label,
            "logs": log_items
        })

    def get_report(self, publish_plugins=None):
        """Report data with all details of current state."""
        instances_details = {}
        for instance in self._all_instances_by_id.values():
            instances_details[instance.id] = self._extract_instance_data(
                instance, instance in self._current_context
            )

        plugins_data = copy.deepcopy(self._plugin_data)
        if plugins_data and not plugins_data[-1]["passed"]:
            plugins_data[-1]["passed"] = True

        if publish_plugins:
            for plugin in publish_plugins:
                if plugin not in self._stored_plugins:
                    plugins_data.append(self._create_plugin_data_item(plugin))

        crashed_file_paths = {}
        if self._publish_discover_result is not None:
            items = self._publish_discover_result.crashed_file_paths.items()
            for filepath, exc_info in items:
                crashed_file_paths[filepath] = "".join(
                    traceback.format_exception(*exc_info)
                )

        return {
            "plugins_data": plugins_data,
            "instances": instances_details,
            "context": self._extract_context_data(self._current_context),
            "crashed_file_paths": crashed_file_paths
        }

    def _extract_context_data(self, context):
        return {
            "label": context.data.get("label")
        }

    def _extract_instance_data(self, instance, exists):
        return {
            "name": instance.data.get("name"),
            "label": instance.data.get("label"),
            "family": instance.data["family"],
            "families": instance.data.get("families") or [],
            "exists": exists
        }

    def _extract_instance_log_items(self, result):
        instance = result["instance"]
        instance_id = None
        if instance:
            instance_id = instance.id

        log_items = self._extract_log_items(result)
        for item in log_items:
            item["instance_id"] = instance_id
        return log_items

    def _extract_log_items(self, result):
        output = []
        records = result.get("records") or []
        for record in records:
            record_exc_info = record.exc_info
            if record_exc_info is not None:
                record_exc_info = "".join(
                    traceback.format_exception(*record_exc_info)
                )

            try:
                msg = record.getMessage()
            except Exception:
                msg = str(record.msg)

            output.append({
                "type": "record",
                "msg": msg,
                "name": record.name,
                "lineno": record.lineno,
                "levelno": record.levelno,
                "levelname": record.levelname,
                "threadName": record.threadName,
                "filename": record.filename,
                "pathname": record.pathname,
                "msecs": record.msecs,
                "exc_info": record_exc_info
            })

        exception = result.get("error")
        if exception:
            fname, line_no, func, exc = exception.traceback
            output.append({
                "type": "error",
                "msg": str(exception),
                "filename": str(fname),
                "lineno": str(line_no),
                "func": str(func),
                "traceback": exception.formatted_traceback
            })

        return output


class PublishPluginsProxy:
    """Wrapper around publish plugin.

    Prepare mapping for publish plugins and actions. Also can create
    serializable data for plugin actions so UI don't have to have access to
    them.

    This object is created in process where publishing is actually running.

    Notes:
        Actions have id but single action can be used on multiple plugins so
            to run an action is needed combination of plugin and action.

    Args:
        plugins [List[pyblish.api.Plugin]]: Discovered plugins that will be
            processed.
    """

    def __init__(self, plugins):
        plugins_by_id = {}
        actions_by_id = {}
        action_ids_by_plugin_id = {}
        for plugin in plugins:
            plugin_id = plugin.id
            plugins_by_id[plugin_id] = plugin

            action_ids = set()
            action_ids_by_plugin_id[plugin_id] = action_ids

            actions = getattr(plugin, "actions", None) or []
            for action in actions:
                action_id = action.id
                action_ids.add(action_id)
                actions_by_id[action_id] = action

        self._plugins_by_id = plugins_by_id
        self._actions_by_id = actions_by_id
        self._action_ids_by_plugin_id = action_ids_by_plugin_id

    def get_action(self, action_id):
        return self._actions_by_id[action_id]

    def get_plugin(self, plugin_id):
        return self._plugins_by_id[plugin_id]

    def get_plugin_id(self, plugin):
        """Get id of plugin based on plugin object.

        It's used for validation errors report.

        Args:
            plugin (pyblish.api.Plugin): Publish plugin for which id should be
                returned.

        Returns:
            str: Plugin id.
        """

        return plugin.id

    def get_plugin_action_items(self, plugin_id):
        """Get plugin action items for plugin by it's id.

        Args:
            plugin_id (str): Publish plugin id.

        Returns:
            List[PublishPluginActionItem]: Items with information about publish
                plugin actions.
        """

        return [
            self._create_action_item(self._actions_by_id[action_id], plugin_id)
            for action_id in self._action_ids_by_plugin_id[plugin_id]
        ]

    def _create_action_item(self, action, plugin_id):
        label = action.label or action.__name__
        icon = getattr(action, "icon", None)
        return PublishPluginActionItem(
            action.id,
            plugin_id,
            action.active,
            action.on,
            label,
            icon
        )


class PublishPluginActionItem:
    """Representation of publish plugin action.

    Data driven object which is used as proxy for controller and UI.

    Args:
        action_id (str): Action id.
        plugin_id (str): Plugin id.
        active (bool): Action is active.
        on_filter (str): Actions have 'on' attribte which define when can be
            action triggered (e.g. 'all', 'failed', ...).
        label (str): Action's label.
        icon (Union[str, None]) Action's icon.
    """

    def __init__(self, action_id, plugin_id, active, on_filter, label, icon):
        self.action_id = action_id
        self.plugin_id = plugin_id
        self.active = active
        self.on_filter = on_filter
        self.label = label
        self.icon = icon

    def to_data(self):
        """Serialize object to dictionary.

        Returns:
            Dict[str, Union[str,bool,None]]: Serialized object.
        """

        return {
            "action_id": self.action_id,
            "plugin_id": self.plugin_id,
            "active": self.active,
            "on_filter": self.on_filter,
            "label": self.label,
            "icon": self.icon
        }

    @classmethod
    def from_data(cls, data):
        """Create object from data.

        Args:
            data (Dict[str, Union[str,bool,None]]): Data used to recreate
                object.

        Returns:
            PublishPluginActionItem: Object created using data.
        """

        return cls(**data)


class ValidationErrorItem:
    """Data driven validation error item.

    Prepared data container with information about validation error and it's
    source plugin.

    Can be converted to raw data and recreated should be used for controller
    and UI connection.

    Args:
        instance_id (str): Id of pyblish instance to which is validation error
            connected.
        instance_label (str): Prepared instance label.
        plugin_id (str): Id of pyblish Plugin which triggered the validation
            error. Id is generated using 'PublishPluginsProxy'.
    """

    def __init__(
        self,
        instance_id,
        instance_label,
        plugin_id,
        context_validation,
        title,
        description,
        detail,
    ):
        self.instance_id = instance_id
        self.instance_label = instance_label
        self.plugin_id = plugin_id
        self.context_validation = context_validation
        self.title = title
        self.description = description
        self.detail = detail

    def to_data(self):
        """Serialize object to dictionary.

        Returns:
            Dict[str, Union[str, bool, None]]: Serialized object data.
        """

        return {
            "instance_id": self.instance_id,
            "instance_label": self.instance_label,
            "plugin_id": self.plugin_id,
            "context_validation": self.context_validation,
            "title": self.title,
            "description": self.description,
            "detail": self.detail,
        }

    @classmethod
    def from_result(cls, plugin_id, error, instance):
        """Create new object based on resukt from controller.

        Returns:
            ValidationErrorItem: New object with filled data.
        """

        instance_label = None
        instance_id = None
        if instance is not None:
            instance_label = (
                instance.data.get("label") or instance.data.get("name")
            )
            instance_id = instance.id

        return cls(
            instance_id,
            instance_label,
            plugin_id,
            instance is None,
            error.title,
            error.description,
            error.detail,
        )

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class PublishValidationErrorsReport:
    """Publish validation errors report that can be parsed to raw data.

    Args:
        error_items (List[ValidationErrorItem]): List of validation errors.
        plugin_action_items (Dict[str, PublishPluginActionItem]): Action items
            by plugin id.
    """

    def __init__(self, error_items, plugin_action_items):
        self._error_items = error_items
        self._plugin_action_items = plugin_action_items

    def __iter__(self):
        for item in self._error_items:
            yield item

    def group_items_by_title(self):
        """Group errors by plugin and their titles.

        Items are grouped by plugin and title -> same title from different
        plugin is different item. Items are ordered by plugin order.

        Returns:
            List[Dict[str, Any]]: List where each item title, instance
                information related to title and possible plugin actions.
        """

        ordered_plugin_ids = []
        error_items_by_plugin_id = collections.defaultdict(list)
        for error_item in self._error_items:
            plugin_id = error_item.plugin_id
            if plugin_id not in ordered_plugin_ids:
                ordered_plugin_ids.append(plugin_id)
            error_items_by_plugin_id[plugin_id].append(error_item)

        grouped_error_items = []
        for plugin_id in ordered_plugin_ids:
            plugin_action_items = self._plugin_action_items[plugin_id]
            error_items = error_items_by_plugin_id[plugin_id]

            titles = []
            error_items_by_title = collections.defaultdict(list)
            for error_item in error_items:
                title = error_item.title
                if title not in titles:
                    titles.append(error_item.title)
                error_items_by_title[title].append(error_item)

            for title in titles:
                grouped_error_items.append({
                    "plugin_action_items": list(plugin_action_items),
                    "error_items": error_items_by_title[title],
                    "title": title
                })
        return grouped_error_items

    def to_data(self):
        """Serialize object to dictionary.

        Returns:
            Dict[str, Any]: Serialized data.
        """

        return {
            "error_items": [
                item.to_data()
                for item in self._error_items
            ],
            "plugin_action_items": {
                plugin_id: [
                    action_item.to_data()
                    for action_item in action_items
                ]
                for plugin_id, action_items in self._plugin_action_items.items()
            }
        }

    @classmethod
    def from_data(cls, data):
        """Recreate object from data.

        Args:
            data (dict[str, Any]): Data to recreate object. Can be created
                using 'to_data' method.

        Returns:
            PublishValidationErrorsReport: New object based on data.
        """

        error_items = [
            ValidationErrorItem.from_data(error_item)
            for error_item in data["error_items"]
        ]
        plugin_action_items = [
            PublishPluginActionItem.from_data(action_item)
            for action_item in data["plugin_action_items"]
        ]
        return cls(error_items, plugin_action_items)


class PublishValidationErrors:
    """Object to keep track about validation errors by plugin."""

    def __init__(self):
        self._plugins_proxy = None
        self._error_items = []
        self._plugin_action_items = {}

    def __bool__(self):
        return self.has_errors

    @property
    def has_errors(self):
        """At least one error was added."""

        return bool(self._error_items)

    def reset(self, plugins_proxy):
        """Reset object to default state.

        Args:
            plugins_proxy (PublishPluginsProxy): Proxy which store plugins,
                actions by ids and create mapping of action ids by plugin ids.
        """

        self._plugins_proxy = plugins_proxy
        self._error_items = []
        self._plugin_action_items = {}

    def create_report(self):
        """Create report based on currently existing errors.

        Returns:
            PublishValidationErrorsReport: Validation error report with all
                error information and publish plugin action items.
        """

        return PublishValidationErrorsReport(
            self._error_items, self._plugin_action_items
        )

    def add_error(self, plugin, error, instance):
        """Add error from pyblish result.

        Args:
            plugin (pyblish.api.Plugin): Plugin which triggered error.
            error (ValidationException): Validation error.
            instance (Union[pyblish.api.Instance, None]): Instance on which was
                error raised or None if was raised on context.
        """

        # Make sure the cached report is cleared
        plugin_id = self._plugins_proxy.get_plugin_id(plugin)
        self._error_items.append(
            ValidationErrorItem.from_result(plugin_id, error, instance)
        )
        if plugin_id in self._plugin_action_items:
            return

        plugin_actions = self._plugins_proxy.get_plugin_action_items(
            plugin_id
        )
        self._plugin_action_items[plugin_id] = plugin_actions


@six.add_metaclass(ABCMeta)
class AbstractPublisherController(object):
    """Publisher tool controller.

    Define what must be implemented to be able use Publisher functionality.

    Goal is to have "data driven" controller that can be used to control UI
    running in different process. That lead to some ""
    """

    _log = None
    _event_system = None

    @property
    def log(self):
        """Controller's logger object.

        Returns:
            logging.Logger: Logger object that can be used for logging.
        """

        if self._log is None:
            self._log = logging.getLogget(self.__class__.__name__)
        return self._log

    @property
    def event_system(self):
        """Inner event system for publisher controller.

        Event system is autocreated.

        Known topics:
            "show.detailed.help" - Detailed help requested (UI related).
            "show.card.message" - Show card message request (UI related).
            "instances.refresh.finished" - Instances are refreshed.
            "plugins.refresh.finished" - Plugins refreshed.
            "publish.reset.finished" - Controller reset finished.
            "publish.process.started" - Publishing started. Can be started from
                paused state.
            "publish.process.validated" - Publishing passed validation.
            "publish.process.stopped" - Publishing stopped/paused process.
            "publish.process.plugin.changed" - Plugin state has changed.
            "publish.process.instance.changed" - Instance state has changed.

        Returns:
            EventSystem: Event system which can trigger callbacks for topics.
        """

        if self._event_system is None:
            self._event_system = EventSystem()
        return self._event_system

    @abstractproperty
    def project_name(self):
        """Current context project name.

        Returns:
            str: Name of project.
        """

        pass

    @abstractproperty
    def current_asset_name(self):
        """Current context asset name.

        Returns:
            Union[str, None]: Name of asset.
        """

        pass

    @abstractproperty
    def current_task_name(self):
        """Current context task name.

        Returns:
            Union[str, None]: Name of task.
        """

        pass

    @abstractproperty
    def instances(self):
        """Collected/created instances.

        Returns:
            List[CreatedInstance]: List of created instances.
        """

        pass

    @abstractmethod
    def get_context_title(self):
        """Get context title for artist shown at the top of main window.

        Returns:
            Union[str, None]: Context title for window or None. In case of None
                a warning is displayed (not nice for artists).
        """

        pass

    @abstractmethod
    def get_asset_docs(self):
        pass

    @abstractmethod
    def get_asset_hierarchy(self):
        pass

    @abstractmethod
    def get_task_names_by_asset_names(self, asset_names):
        pass

    @abstractmethod
    def reset(self):
        """Reset whole controller.

        This should reset create context, publish context and all variables
        that are related to it.
        """

        pass

    @abstractmethod
    def get_creator_attribute_definitions(self, instances):
        pass

    @abstractmethod
    def get_publish_attribute_definitions(self, instances, include_context):
        pass

    @abstractmethod
    def get_creator_icon(self, identifier):
        """Receive creator's icon by identifier.

        Args:
            identifier (str): Creator's identifier.

        Returns:
            Union[str, None]: Creator's icon string.
        """

        pass

    @abstractmethod
    def create(
        self, creator_identifier, subset_name, instance_data, options
    ):
        """Trigger creation by creator identifier.

        Should also trigger refresh of instanes.

        Args:
            creator_identifier (str): Identifier of Creator plugin.
            subset_name (str): Calculated subset name.
            instance_data (Dict[str, Any]): Base instance data with variant,
                asset name and task name.
            options (Dict[str, Any]): Data from pre-create attributes.
        """

    def save_changes(self):
        """Save changes in create context."""

        pass

    def remove_instances(self, instances):
        """Remove list of instances from create context."""

        pass

    @abstractproperty
    def publish_has_finished(self):
        """Has publishing finished.

        Returns:
            bool: If publishing finished and all plugins were iterated.
        """

        pass

    @abstractproperty
    def publish_is_running(self):
        """Publishing is running right now.

        Returns:
            bool: If publishing is in progress.
        """

        pass

    @abstractproperty
    def publish_has_validated(self):
        """Publish validation passed.

        Returns:
            bool: If publishing passed last possible validation order.
        """

        pass

    @abstractproperty
    def publish_has_crashed(self):
        """Publishing crashed for any reason.

        Returns:
            bool: Publishing crashed.
        """

        pass

    @abstractproperty
    def publish_has_validation_errors(self):
        """During validation happened at least one validation error.

        Returns:
            bool: Validation error was raised during validation.
        """

        pass

    @abstractproperty
    def publish_max_progress(self):
        """Get maximum possible progress number.

        Returns:
            int: Number that can be used as 100% of publish progress bar.
        """

        pass

    @abstractproperty
    def publish_progress(self):
        """Current progress number.

        Returns:
            int: Current progress value which is between 0 and
                'publish_max_progress'.
        """

        pass

    @abstractproperty
    def publish_comment_is_set(self):
        """Publish comment was at least once set.

        Publish comment can be set only once when publish is started for a
        first time. This helpt to idetify if 'set_comment' should be called or
        not.
        """

        pass

    @abstractmethod
    def get_publish_crash_error(self):

        pass

    @abstractmethod
    def get_publish_report(self):
        pass

    @abstractmethod
    def get_validation_errors(self):
        pass

    @abstractmethod
    def publish(self):
        """Trigger publishing without any order limitations."""

        pass

    @abstractmethod
    def validate(self):
        """Trigger publishing which will stop after validation order."""

        pass

    @abstractmethod
    def stop_publish(self):
        """Stop publishing can be also used to pause publishing.

        Pause of publishing is possible only if all plugins successfully
        finished.
        """

        pass

    @abstractmethod
    def run_action(self, plugin_id, action_id):
        """Trigger pyblish action on a plugin.

        Args:
            plugin_id (str): Id of publish plugin.
            action_id (str): Id of publish action.
        """

        pass

    @abstractmethod
    def reset_project_data_cache(self):
        pass

    @abstractmethod
    def set_comment(self, comment):
        """Set comment on pyblish context.

        Set "comment" key on current pyblish.api.Context data.

        Args:
            comment (str): Artist's comment.
        """

        pass

    @abstractmethod
    def emit_card_message(self, message):
        """Emit a card message which can have a lifetime.

        This is for UI purposes. Method can be extended to more arguments
        in future e.g. different message timeout or type (color).

        Args:
            message (str): Message that will be showed.
        """

        pass


class PublisherController(AbstractPublisherController):
    """Middleware between UI, CreateContext and publish Context.

    Handle both creation and publishing parts.

    Args:
        dbcon (AvalonMongoDB): Connection to mongo with context.
        headless (bool): Headless publishing. ATM not implemented or used.
    """

    _log = None

    def __init__(self, dbcon=None, headless=False):
        self._host = registered_host()
        self._headless = headless

        self._create_context = CreateContext(
            self._host, dbcon, headless=headless, reset=False
        )

        self._publish_plugins_proxy = None

        # pyblish.api.Context
        self._publish_context = None
        # Pyblish report
        self._publish_report = PublishReport(self)
        # Store exceptions of validation error
        self._publish_validation_errors = PublishValidationErrors()
        # Any other exception that happened during publishing
        self._publish_error = None
        # Publishing is in progress
        self._publish_is_running = False
        # Publishing is over validation order
        self._publish_validated = False
        # Publishing should stop at validation stage
        self._publish_up_validation = False
        # All publish plugins are processed
        self._publish_finished = False
        self._publish_max_progress = 0
        self._publish_progress = 0
        # This information is not much important for controller but for widget
        #   which can change (and set) the comment.
        self._publish_comment_is_set = False

        # Validation order
        # - plugin with order same or higher than this value is extractor or
        #   higher
        self._validation_order = (
            pyblish.api.ValidatorOrder + PLUGIN_ORDER_OFFSET
        )

        # Plugin iterator
        self._main_thread_iter = None

        # State flags to prevent executing method which is already in progress
        self._resetting_plugins = False
        self._resetting_instances = False

        # Cacher of avalon documents
        self._asset_docs_cache = AssetDocsCache(self)

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger("PublisherController")
        return self._log

    @property
    def project_name(self):
        """Current project context defined by host.

        Returns:
            str: Project name.
        """

        return self._host.get_current_context()["project_name"]

    @property
    def current_asset_name(self):
        """Current context asset name defined by host.

        Returns:
            Union[str, None]: Asset name or None if asset is not set.
        """

        return self._host.get_current_context()["asset_name"]

    @property
    def current_task_name(self):
        """Current context task name defined by host.

        Returns:
            Union[str, None]: Task name or None if task is not set.
        """

        return self._host.get_current_context()["task_name"]

    @property
    def instances(self):
        """Current instances in create context."""
        return self._create_context.instances

    @property
    def _creators(self):
        """All creators loaded in create context."""

        return self._create_context.creators

    @property
    def manual_creators(self):
        """Creators that can be shown in create dialog."""
        return self._create_context.manual_creators

    @property
    def host_is_valid(self):
        """Host is valid for creation."""

        return self._create_context.host_is_valid

    @property
    def _publish_plugins(self):
        """Publish plugins."""
        return self._create_context.publish_plugins

    def _emit_event(self, topic, data=None):
        if data is None:
            data = {}
        self.event_system.emit(topic, data, "controller")

    # --- Publish specific callbacks ---
    def get_asset_docs(self):
        """Get asset documents from cache for whole project."""
        return self._asset_docs_cache.get_asset_docs()

    def get_context_title(self):
        """Get context title for artist shown at the top of main window."""

        context_title = None
        if hasattr(self._host, "get_context_title"):
            context_title = self._host.get_context_title()

        if context_title is None:
            context_title = os.environ.get("AVALON_APP_NAME")
            if context_title is None:
                context_title = os.environ.get("AVALON_APP")

        return context_title

    def get_asset_hierarchy(self):
        """Prepare asset documents into hierarchy."""
        _queue = collections.deque(self.get_asset_docs())

        output = collections.defaultdict(list)
        while _queue:
            asset_doc = _queue.popleft()
            parent_id = asset_doc["data"]["visualParent"]
            output[parent_id].append(asset_doc)
        return output

    def get_task_names_by_asset_names(self, asset_names):
        """Prepare task names by asset name."""
        task_names_by_asset_name = (
            self._asset_docs_cache.get_task_names_by_asset_name()
        )
        result = {}
        for asset_name in asset_names:
            result[asset_name] = set(
                task_names_by_asset_name.get(asset_name) or []
            )
        return result

    def reset(self):
        """Reset everything related to creation and publishing."""
        # Stop publishing
        self.stop_publish()

        self.save_changes()

        # Reset avalon context
        self._create_context.reset_avalon_context()

        self._reset_plugins()
        # Publish part must be reset after plugins
        self._reset_publish()
        self._reset_instances()

        self.emit_card_message("Refreshed..")

    def _reset_plugins(self):
        """Reset to initial state."""
        if self._resetting_plugins:
            return

        self._resetting_plugins = True

        self._create_context.reset_plugins()

        self._resetting_plugins = False

        self._emit_event("plugins.refresh.finished")

    def _reset_instances(self):
        """Reset create instances."""
        if self._resetting_instances:
            return

        self._resetting_instances = True

        self._create_context.reset_context_data()
        with self._create_context.bulk_instances_collection():
            self._create_context.reset_instances()
            self._create_context.execute_autocreators()

        self._resetting_instances = False

        self._emit_event("instances.refresh.finished")

    def emit_card_message(self, message):
        self._emit_event("show.card.message", {"message": message})

    def get_creator_attribute_definitions(self, instances):
        """Collect creator attribute definitions for multuple instances.

        Args:
            instances(list<CreatedInstance>): List of created instances for
                which should be attribute definitions returned.
        """
        output = []
        _attr_defs = {}
        for instance in instances:
            for attr_def in instance.creator_attribute_defs:
                found_idx = None
                for idx, _attr_def in _attr_defs.items():
                    if attr_def == _attr_def:
                        found_idx = idx
                        break

                value = None
                if attr_def.is_value_def:
                    value = instance.creator_attributes[attr_def.key]
                if found_idx is None:
                    idx = len(output)
                    output.append((attr_def, [instance], [value]))
                    _attr_defs[idx] = attr_def
                else:
                    item = output[found_idx]
                    item[1].append(instance)
                    item[2].append(value)
        return output

    def get_publish_attribute_definitions(self, instances, include_context):
        """Collect publish attribute definitions for passed instances.

        Args:
            instances(list<CreatedInstance>): List of created instances for
                which should be attribute definitions returned.
            include_context(bool): Add context specific attribute definitions.
        """
        _tmp_items = []
        if include_context:
            _tmp_items.append(self._create_context)

        for instance in instances:
            _tmp_items.append(instance)

        all_defs_by_plugin_name = {}
        all_plugin_values = {}
        for item in _tmp_items:
            for plugin_name, attr_val in item.publish_attributes.items():
                attr_defs = attr_val.attr_defs
                if not attr_defs:
                    continue

                if plugin_name not in all_defs_by_plugin_name:
                    all_defs_by_plugin_name[plugin_name] = attr_val.attr_defs

                if plugin_name not in all_plugin_values:
                    all_plugin_values[plugin_name] = {}

                plugin_values = all_plugin_values[plugin_name]

                for attr_def in attr_defs:
                    if attr_def.key not in plugin_values:
                        plugin_values[attr_def.key] = []
                    attr_values = plugin_values[attr_def.key]

                    value = attr_val[attr_def.key]
                    attr_values.append((item, value))

        output = []
        for plugin in self._create_context.plugins_with_defs:
            plugin_name = plugin.__name__
            if plugin_name not in all_defs_by_plugin_name:
                continue
            output.append((
                plugin_name,
                all_defs_by_plugin_name[plugin_name],
                all_plugin_values
            ))
        return output

    def get_creator_icon(self, identifier):
        """TODO rename to get creator icon."""
        creator = self._creators.get(identifier)
        if creator is not None:
            return creator.get_icon()
        return None

    def create(
        self, creator_identifier, subset_name, instance_data, options
    ):
        """Trigger creation and refresh of instances in UI."""
        creator = self._creators[creator_identifier]
        creator.create(subset_name, instance_data, options)

        self._emit_event("instances.refresh.finished")

    def save_changes(self):
        """Save changes happened during creation."""
        if self._create_context.host_is_valid:
            self._create_context.save_changes()

    def remove_instances(self, instances):
        """"""
        # QUESTION Expect that instances are really removed? In that case save
        #   reset is not required and save changes too.
        self.save_changes()

        self._create_context.remove_instances(instances)

        self._emit_event("instances.refresh.finished")

    # --- Publish specific implementations ---
    @property
    def publish_has_finished(self):
        return self._publish_finished

    @property
    def publish_is_running(self):
        return self._publish_is_running

    @property
    def publish_has_validated(self):
        return self._publish_validated

    @property
    def publish_has_crashed(self):
        return bool(self._publish_error)

    @property
    def publish_has_validation_errors(self):
        return bool(self._publish_validation_errors)

    @property
    def publish_max_progress(self):
        return self._publish_max_progress

    @property
    def publish_progress(self):
        return self._publish_progress

    @property
    def publish_comment_is_set(self):
        return self._publish_comment_is_set

    def get_publish_crash_error(self):
        return self._publish_error

    def get_publish_report(self):
        return self._publish_report.get_report(self._publish_plugins)

    def get_validation_errors(self):
        return self._publish_validation_errors.create_report()

    def _reset_publish(self):
        self._publish_is_running = False
        self._publish_validated = False
        self._publish_up_validation = False
        self._publish_finished = False
        self._publish_comment_is_set = False

        self._main_thread_iter = self._publish_iterator()
        self._publish_context = pyblish.api.Context()
        # Make sure "comment" is set on publish context
        self._publish_context.data["comment"] = ""
        # Add access to create context during publishing
        # - must not be used for changing CreatedInstances during publishing!
        # QUESTION
        # - pop the key after first collector using it would be safest option?
        self._publish_context.data["create_context"] = self._create_context

        self._publish_plugins_proxy = PublishPluginsProxy(
            self._publish_plugins
        )

        self._publish_report.reset(self._publish_context, self._create_context)
        self._publish_validation_errors.reset(self._publish_plugins_proxy)
        self._publish_error = None

        self._publish_max_progress = len(self._publish_plugins)
        self._publish_progress = 0

        self._emit_event("publish.reset.finished")

    def set_comment(self, comment):
        self._publish_context.data["comment"] = comment
        self._publish_comment_is_set = True

    def publish(self):
        """Run publishing."""
        self._publish_up_validation = False
        self._start_publish()

    def validate(self):
        """Run publishing and stop after Validation."""
        if self._publish_validated:
            return
        self._publish_up_validation = True
        self._start_publish()

    def _start_publish(self):
        """Start or continue in publishing."""
        if self._publish_is_running:
            return

        # Make sure changes are saved
        self.save_changes()

        self._publish_is_running = True

        self._emit_event("publish.process.started")

        self._publish_next_process()

    def _stop_publish(self):
        """Stop or pause publishing."""
        self._publish_is_running = False

        self._emit_event("publish.process.stopped")

    def stop_publish(self):
        """Stop publishing process (any reason)."""

        if self._publish_is_running:
            self._stop_publish()

    def run_action(self, plugin_id, action_id):
        # TODO handle result in UI
        plugin = self._publish_plugins_proxy.get_plugin(plugin_id)
        action = self._publish_plugins_proxy.get_action(action_id)

        result = pyblish.plugin.process(
            plugin, self._publish_context, None, action.id
        )
        self._publish_report.add_action_result(action, result)

    def _publish_next_process(self):
        # Validations of progress before using iterator
        # - same conditions may be inside iterator but they may be used
        #   only in specific cases (e.g. when it happens for a first time)

        # There are validation errors and validation is passed
        # - can't do any progree
        if (
            self._publish_validated
            and self._publish_validation_errors
        ):
            item = MainThreadItem(self.stop_publish)

        # Any unexpected error happened
        # - everything should stop
        elif self._publish_error:
            item = MainThreadItem(self.stop_publish)

        # Everything is ok so try to get new processing item
        else:
            item = next(self._main_thread_iter)

        self._process_main_thread_item(item)

    def _process_main_thread_item(self, item):
        item()

    def _publish_iterator(self):
        """Main logic center of publishing.

        Iterator returns `MainThreadItem` objects with callbacks that should be
        processed in main thread (threaded in future?). Cares about changing
        states of currently processed publish plugin and instance. Also
        change state of processed orders like validation order has passed etc.

        Also stops publishing if should stop on validation.

        QUESTION:
        Does validate button still make sense?
        """
        for idx, plugin in enumerate(self._publish_plugins):
            self._publish_progress = idx

            # Check if plugin is over validation order
            if not self._publish_validated:
                self._publish_validated = (
                    plugin.order >= self._validation_order
                )
                # Trigger callbacks when validation stage is passed
                if self._publish_validated:
                    self._emit_event("publish.process.validated")

            # Stop if plugin is over validation order and process
            #   should process up to validation.
            if self._publish_up_validation and self._publish_validated:
                yield MainThreadItem(self.stop_publish)

            # Stop if validation is over and validation errors happened
            if (
                self._publish_validated
                and self._publish_validation_errors
            ):
                yield MainThreadItem(self.stop_publish)

            # Add plugin to publish report
            self._publish_report.add_plugin_iter(plugin, self._publish_context)

            # Trigger callback that new plugin is going to be processed
            plugin_label = plugin.__name__
            if hasattr(plugin, "label") and plugin.label:
                plugin_label = plugin.label
            self._emit_event(
                "publish.process.plugin.changed",
                {"plugin_label": plugin_label}
            )

            # Plugin is instance plugin
            if plugin.__instanceEnabled__:
                instances = pyblish.logic.instances_by_plugin(
                    self._publish_context, plugin
                )
                if not instances:
                    self._publish_report.set_plugin_skipped()
                    continue

                for instance in instances:
                    if instance.data.get("publish") is False:
                        continue

                    instance_label = (
                        instance.data.get("label")
                        or instance.data["name"]
                    )
                    self._emit_event(
                        "publish.process.instance.changed",
                        {"instance_label": instance_label}
                    )

                    yield MainThreadItem(
                        self._process_and_continue, plugin, instance
                    )
            else:
                families = collect_families_from_instances(
                    self._publish_context, only_active=True
                )
                plugins = pyblish.logic.plugins_by_families(
                    [plugin], families
                )
                if plugins:
                    instance_label = (
                        self._publish_context.data.get("label")
                        or self._publish_context.data.get("name")
                        or "Context"
                    )
                    self._emit_event(
                        "publish.process.instance.changed",
                        {"instance_label": instance_label}
                    )
                    yield MainThreadItem(
                        self._process_and_continue, plugin, None
                    )
                else:
                    self._publish_report.set_plugin_skipped()

        # Cleanup of publishing process
        self._publish_finished = True
        self._publish_progress = self._publish_max_progress
        yield MainThreadItem(self.stop_publish)

    def _add_validation_error(self, result):
        self._publish_validation_errors.add_error(
            result["plugin"],
            result["error"],
            result["instance"]
        )

    def _process_and_continue(self, plugin, instance):
        result = pyblish.plugin.process(
            plugin, self._publish_context, instance
        )

        self._publish_report.add_result(result)

        exception = result.get("error")
        if exception:
            if (
                isinstance(exception, PublishValidationError)
                and not self._publish_validated
            ):
                self._add_validation_error(result)

            else:
                self._publish_error = exception

        self._publish_next_process()

    def reset_project_data_cache(self):
        self._asset_docs_cache.reset()


def collect_families_from_instances(instances, only_active=False):
    """Collect all families for passed publish instances.

    Args:
        instances(list<pyblish.api.Instance>): List of publish instances from
            which are families collected.
        only_active(bool): Return families only for active instances.
    """
    all_families = set()
    for instance in instances:
        if only_active:
            if instance.data.get("publish") is False:
                continue
        family = instance.data.get("family")
        if family:
            all_families.add(family)

        families = instance.data.get("families") or tuple()
        for family in families:
            all_families.add(family)

    return list(all_families)
