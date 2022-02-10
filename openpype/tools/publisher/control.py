import os
import copy
import inspect
import logging
import traceback
import collections

import weakref
try:
    from weakref import WeakMethod
except Exception:
    from openpype.lib.python_2_comp import WeakMethod

import avalon.api
import pyblish.api

from openpype.pipeline import PublishValidationError
from openpype.pipeline.create import CreateContext

from Qt import QtCore

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


class MainThreadProcess(QtCore.QObject):
    """Qt based main thread process executor.

    Has timer which controls each 50ms if there is new item to process.

    This approach gives ability to update UI meanwhile plugin is in progress.
    """

    timer_interval = 3

    def __init__(self):
        super(MainThreadProcess, self).__init__()
        self._items_to_process = collections.deque()

        timer = QtCore.QTimer()
        timer.setInterval(self.timer_interval)

        timer.timeout.connect(self._execute)

        self._timer = timer

    def add_item(self, item):
        self._items_to_process.append(item)

    def _execute(self):
        if not self._items_to_process:
            return

        item = self._items_to_process.popleft()
        item.process()

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def clear(self):
        if self._timer.isActive():
            self._timer.stop()
        self._items_to_process = collections.deque()


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

    @property
    def dbcon(self):
        return self._controller.dbcon

    def reset(self):
        self._asset_docs = None
        self._task_names_by_asset_name = {}

    def _query(self):
        if self._asset_docs is None:
            asset_docs = list(self.dbcon.find(
                {"type": "asset"},
                self.projection
            ))
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

    def reset(self, context, publish_discover_result=None):
        """Reset report and clear all data."""
        self._publish_discover_result = publish_discover_result
        self._plugin_data = []
        self._plugin_data_with_plugin = []
        self._current_plugin_data = {}
        self._all_instances_by_id = {}
        self._current_context = context

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

        label = None
        if hasattr(plugin, "label"):
            label = plugin.label

        plugin_data_item = {
            "name": plugin.__name__,
            "label": label,
            "order": plugin.order,
            "instances_data": [],
            "actions_data": [],
            "skipped": False,
            "passed": False
        }
        self._plugin_data_with_plugin.append({
            "plugin": plugin,
            "data": plugin_data_item
        })
        self._plugin_data.append(plugin_data_item)
        return plugin_data_item

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
                    plugins_data.append(self._add_plugin_data_item(plugin))

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


class PublisherController:
    """Middleware between UI, CreateContext and publish Context.

    Handle both creation and publishing parts.

    Args:
        dbcon (AvalonMongoDB): Connection to mongo with context.
        headless (bool): Headless publishing. ATM not implemented or used.
    """
    def __init__(self, dbcon=None, headless=False):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()
        self.headless = headless

        self.create_context = CreateContext(
            self.host, dbcon, headless=headless, reset=False
        )

        # pyblish.api.Context
        self._publish_context = None
        # Pyblish report
        self._publish_report = PublishReport(self)
        # Store exceptions of validation error
        self._publish_validation_errors = []
        # Currently processing plugin errors
        self._publish_current_plugin_validation_errors = None
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

        # Qt based main thread processor
        self._main_thread_processor = MainThreadProcess()
        # Plugin iterator
        self._main_thread_iter = None

        # Variables where callbacks are stored
        self._instances_refresh_callback_refs = set()
        self._plugins_refresh_callback_refs = set()

        self._publish_reset_callback_refs = set()
        self._publish_started_callback_refs = set()
        self._publish_validated_callback_refs = set()
        self._publish_stopped_callback_refs = set()

        self._publish_instance_changed_callback_refs = set()
        self._publish_plugin_changed_callback_refs = set()

        # State flags to prevent executing method which is already in progress
        self._resetting_plugins = False
        self._resetting_instances = False

        # Cacher of avalon documents
        self._asset_docs_cache = AssetDocsCache(self)

    @property
    def project_name(self):
        """Current project context."""
        return self.dbcon.Session["AVALON_PROJECT"]

    @property
    def dbcon(self):
        """Pointer to AvalonMongoDB in creator context."""
        return self.create_context.dbcon

    @property
    def instances(self):
        """Current instances in create context."""
        return self.create_context.instances

    @property
    def creators(self):
        """All creators loaded in create context."""
        return self.create_context.creators

    @property
    def manual_creators(self):
        """Creators that can be shown in create dialog."""
        return self.create_context.manual_creators

    @property
    def host_is_valid(self):
        """Host is valid for creation."""
        return self.create_context.host_is_valid

    @property
    def publish_plugins(self):
        """Publish plugins."""
        return self.create_context.publish_plugins

    @property
    def plugins_with_defs(self):
        """Publish plugins with possible attribute definitions."""
        return self.create_context.plugins_with_defs

    def _create_reference(self, callback):
        if inspect.ismethod(callback):
            ref = WeakMethod(callback)
        elif callable(callback):
            ref = weakref.ref(callback)
        else:
            raise TypeError("Expected function or method got {}".format(
                str(type(callback))
            ))
        return ref

    def add_instances_refresh_callback(self, callback):
        """Callbacks triggered on instances refresh."""
        ref = self._create_reference(callback)
        self._instances_refresh_callback_refs.add(ref)

    def add_plugins_refresh_callback(self, callback):
        """Callbacks triggered on plugins refresh."""
        ref = self._create_reference(callback)
        self._plugins_refresh_callback_refs.add(ref)

    # --- Publish specific callbacks ---
    def add_publish_reset_callback(self, callback):
        """Callbacks triggered on publishing reset."""
        ref = self._create_reference(callback)
        self._publish_reset_callback_refs.add(ref)

    def add_publish_started_callback(self, callback):
        """Callbacks triggered on publishing start."""
        ref = self._create_reference(callback)
        self._publish_started_callback_refs.add(ref)

    def add_publish_validated_callback(self, callback):
        """Callbacks triggered on passing last possible validation order."""
        ref = self._create_reference(callback)
        self._publish_validated_callback_refs.add(ref)

    def add_instance_change_callback(self, callback):
        """Callbacks triggered before next publish instance process."""
        ref = self._create_reference(callback)
        self._publish_instance_changed_callback_refs.add(ref)

    def add_plugin_change_callback(self, callback):
        """Callbacks triggered before next plugin processing."""
        ref = self._create_reference(callback)
        self._publish_plugin_changed_callback_refs.add(ref)

    def add_publish_stopped_callback(self, callback):
        """Callbacks triggered on publishing stop (any reason)."""
        ref = self._create_reference(callback)
        self._publish_stopped_callback_refs.add(ref)

    def get_asset_docs(self):
        """Get asset documents from cache for whole project."""
        return self._asset_docs_cache.get_asset_docs()

    def get_context_title(self):
        """Get context title for artist shown at the top of main window."""
        context_title = None
        if hasattr(self.host, "get_context_title"):
            context_title = self.host.get_context_title()

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

    def _trigger_callbacks(self, callbacks, *args, **kwargs):
        """Helper method to trigger callbacks stored by their rerence."""
        # Trigger reset callbacks
        to_remove = set()
        for ref in callbacks:
            callback = ref()
            if callback:
                callback(*args, **kwargs)
            else:
                to_remove.add(ref)

        for ref in to_remove:
            callbacks.remove(ref)

    def reset(self):
        """Reset everything related to creation and publishing."""
        # Stop publishing
        self.stop_publish()

        # Reset avalon context
        self.create_context.reset_avalon_context()

        self._reset_plugins()
        # Publish part must be reset after plugins
        self._reset_publish()
        self._reset_instances()

    def _reset_plugins(self):
        """Reset to initial state."""
        if self._resetting_plugins:
            return

        self._resetting_plugins = True

        self.create_context.reset_plugins()

        self._resetting_plugins = False

        self._trigger_callbacks(self._plugins_refresh_callback_refs)

    def _reset_instances(self):
        """Reset create instances."""
        if self._resetting_instances:
            return

        self._resetting_instances = True

        self.create_context.reset_context_data()
        with self.create_context.bulk_instances_collection():
            self.create_context.reset_instances()
            self.create_context.execute_autocreators()

        self._resetting_instances = False

        self._trigger_callbacks(self._instances_refresh_callback_refs)

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
            _tmp_items.append(self.create_context)

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
        for plugin in self.plugins_with_defs:
            plugin_name = plugin.__name__
            if plugin_name not in all_defs_by_plugin_name:
                continue
            output.append((
                plugin_name,
                all_defs_by_plugin_name[plugin_name],
                all_plugin_values
            ))
        return output

    def get_icon_for_family(self, family):
        """TODO rename to get creator icon."""
        creator = self.creators.get(family)
        if creator is not None:
            return creator.get_icon()
        return None

    def create(
        self, creator_identifier, subset_name, instance_data, options
    ):
        """Trigger creation and refresh of instances in UI."""
        creator = self.creators[creator_identifier]
        creator.create(subset_name, instance_data, options)

        self._trigger_callbacks(self._instances_refresh_callback_refs)

    def save_changes(self):
        """Save changes happened during creation."""
        if self.create_context.host_is_valid:
            self.create_context.save_changes()

    def remove_instances(self, instances):
        """"""
        # QUESTION Expect that instances are really removed? In that case save
        #   reset is not required and save changes too.
        self.save_changes()

        self.create_context.remove_instances(instances)

        self._trigger_callbacks(self._instances_refresh_callback_refs)

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
        return self._publish_report.get_report(self.publish_plugins)

    def get_validation_errors(self):
        return self._publish_validation_errors

    def _reset_publish(self):
        self._publish_is_running = False
        self._publish_validated = False
        self._publish_up_validation = False
        self._publish_finished = False
        self._publish_comment_is_set = False
        self._main_thread_processor.clear()
        self._main_thread_iter = self._publish_iterator()
        self._publish_context = pyblish.api.Context()
        # Make sure "comment" is set on publish context
        self._publish_context.data["comment"] = ""
        # Add access to create context during publishing
        # - must not be used for changing CreatedInstances during publishing!
        # QUESTION
        # - pop the key after first collector using it would be safest option?
        self._publish_context.data["create_context"] = self.create_context

        self._publish_report.reset(
            self._publish_context,
            self.create_context.publish_discover_result
        )
        self._publish_validation_errors = []
        self._publish_current_plugin_validation_errors = None
        self._publish_error = None

        self._publish_max_progress = len(self.publish_plugins)
        self._publish_progress = 0

        self._trigger_callbacks(self._publish_reset_callback_refs)

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
        self._trigger_callbacks(self._publish_started_callback_refs)
        self._main_thread_processor.start()
        self._publish_next_process()

    def _stop_publish(self):
        """Stop or pause publishing."""
        self._publish_is_running = False
        self._main_thread_processor.stop()
        self._trigger_callbacks(self._publish_stopped_callback_refs)

    def stop_publish(self):
        """Stop publishing process (any reason)."""
        if self._publish_is_running:
            self._stop_publish()

    def run_action(self, plugin, action):
        # TODO handle result in UI
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

        self._main_thread_processor.add_item(item)

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
        for idx, plugin in enumerate(self.publish_plugins):
            self._publish_progress = idx
            # Add plugin to publish report
            self._publish_report.add_plugin_iter(plugin, self._publish_context)

            # Reset current plugin validations error
            self._publish_current_plugin_validation_errors = None

            # Check if plugin is over validation order
            if not self._publish_validated:
                self._publish_validated = (
                    plugin.order >= self._validation_order
                )
                # Trigger callbacks when validation stage is passed
                if self._publish_validated:
                    self._trigger_callbacks(
                        self._publish_validated_callback_refs
                    )

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

            # Trigger callback that new plugin is going to be processed
            self._trigger_callbacks(
                self._publish_plugin_changed_callback_refs, plugin
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

                    self._trigger_callbacks(
                        self._publish_instance_changed_callback_refs,
                        self._publish_context,
                        instance
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
                    self._trigger_callbacks(
                        self._publish_instance_changed_callback_refs,
                        self._publish_context,
                        None
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
        if self._publish_current_plugin_validation_errors is None:
            self._publish_current_plugin_validation_errors = {
                "plugin": result["plugin"],
                "errors": []
            }
            self._publish_validation_errors.append(
                self._publish_current_plugin_validation_errors
            )

        self._publish_current_plugin_validation_errors["errors"].append({
            "exception": result["error"],
            "instance": result["instance"]
        })

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
