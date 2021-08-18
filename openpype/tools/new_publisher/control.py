import copy
import weakref
import logging
import collections
import avalon.api
import pyblish.api
from openpype.api import (
    get_system_settings,
    get_project_settings
)

from openpype.pipeline import (
    PublishValidationError,
    KnownPublishError,
    OpenPypePyblishPluginMixin
)

from openpype.pipeline.create import (
    BaseCreator,
    CreateContext
)

from Qt import QtCore


PLUGIN_ORDER_OFFSET = 0.5


class MainThreadItem:
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.callback(*self.args, **self.kwargs)


class MainThreadProcess(QtCore.QObject):
    def __init__(self):
        super(MainThreadProcess, self).__init__()
        self._items_to_process = collections.deque()

        timer = QtCore.QTimer()
        timer.setInterval(50)

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


class PublisherController:
    def __init__(self, dbcon=None, headless=False):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()
        self.headless = headless

        self.create_context = CreateContext(
            self.host, dbcon, headless=False, reset=False
        )

        # pyblish.api.Context
        self._publish_context = None
        # Pyblish logs
        self._publish_logs = []
        # Store exceptions of validation error
        self._publish_validation_errors = []
        # Any other exception that happened during publishing
        self._publish_error = None
        # Publishing is over validation order
        self._publish_validated = False
        # Publishing should stop at validation stage
        self._publish_up_validation = False
        # All publish plugins are processed
        self._publish_finished = False

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

        # Varianbles where callbacks are stored
        self._instances_refresh_callback_refs = set()
        self._plugins_refresh_callback_refs = set()
        self._publish_instance_changed_callback_refs = set()
        self._publish_plugin_changed_callback_refs = set()
        self._publishing_stopped_callback_refs = set()

        # State flags to prevent executing method which is already in progress
        self._resetting_plugins = False
        self._resetting_instances = False

        # Cacher of avalon documents
        self._asset_docs_cache = AssetDocsCache(self)

    @property
    def project_name(self):
        return self.dbcon.Session["AVALON_PROJECT"]

    @property
    def dbcon(self):
        return self.create_context.dbcon

    @property
    def instances(self):
        return self.create_context.instances

    @property
    def creators(self):
        return self.create_context.creators

    @property
    def publish_plugins(self):
        return self.create_context.publish_plugins

    @property
    def plugins_with_defs(self):
        return self.create_context.plugins_with_defs

    def add_instances_refresh_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._instances_refresh_callback_refs.add(ref)

    def add_plugins_refresh_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._plugins_refresh_callback_refs.add(ref)

    def add_instance_change_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._publish_instance_changed_callback_refs.add(ref)

    def add_plugin_change_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._publish_plugin_changed_callback_refs.add(ref)

    def add_publish_stopped_callback(self, callback):
        ref = weakref.WeakMethod(callback)
        self._publishing_stopped_callback_refs.add(ref)

    def _trigger_callbacks(self, callbacks, *args, **kwargs):
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
        self._reset_plugins()
        # Publish part must be resetted after plugins
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
        if self._resetting_instances:
            return

        self._resetting_instances = True

        self.create_context.reset_instances()

        self._resetting_instances = False

        self._trigger_callbacks(self._instances_refresh_callback_refs)

    def get_family_attribute_definitions(self, instances):
        output = []
        _attr_defs = {}
        for instance in instances:
            for attr_def in instance.family_attribute_defs:
                found_idx = None
                for idx, _attr_def in _attr_defs.items():
                    if attr_def == _attr_def:
                        found_idx = idx
                        break

                value = instance.data["family_attributes"][attr_def.key]
                if found_idx is None:
                    idx = len(output)
                    output.append((attr_def, [instance], [value]))
                    _attr_defs[idx] = attr_def
                else:
                    item = output[found_idx]
                    item[1].append(instance)
                    item[2].append(value)
        return output

    def get_publish_attribute_definitions(self, instances):
        all_defs_by_plugin_name = {}
        all_plugin_values = {}
        for instance in instances:
            for plugin_name, attr_val in instance.publish_attributes.items():
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
                    attr_values.append((instance, value))

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

    def create(self, family, subset_name, instance_data, options):
        # QUESTION Force to return instances or call `list_instances` on each
        #   creation? (`list_instances` may slow down...)
        creator = self.creators[family]
        creator.create(subset_name, instance_data, options)

        self._reset_instances()

    def save_instance_changes(self):
        update_list = []
        for instance in self.instances:
            instance_changes = instance.changes()
            if instance_changes:
                update_list.append((instance, instance_changes))

        if update_list:
            self.host.update_instances(update_list)

    def remove_instances(self, instances):
        self.host.remove_instances(instances)

        self._reset_instances()

    def _reset_publish(self):
        self._publish_validated = False
        self._publish_up_validation = False
        self._publish_finished = False
        self._main_thread_processor.clear()
        self._main_thread_iter = self._publish_iterator()
        self._publish_context = pyblish.api.Context()

        self._publish_logs = []
        self._publish_validation_errors = []
        self._publish_error = None

    def validate(self):
        if self._publish_validated:
            return
        self._publish_up_validation = True
        self._start_publish()

    def publish(self):
        self._publish_up_validation = False
        self._start_publish()

    def _start_publish(self):
        self._main_thread_processor.start()
        self._publish_next_process()

    def _stop_publish(self):
        self._main_thread_processor.stop()
        self._trigger_callbacks(self._publishing_stopped_callback_refs)

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
            item = MainThreadItem(self._stop_publish)

        # Any unexpected error happened
        # - everything should stop
        elif self._publish_error:
            item = MainThreadItem(self._stop_publish)

        # Everything is ok so try to get new processing item
        else:
            item = next(self._main_thread_iter)

        self._main_thread_processor.add_item(item)

    def _publish_iterator(self):
        for plugin in self.publish_plugins:
            if (
                self._publish_up_validation
                and plugin.order >= self._validation_order
            ):
                yield MainThreadItem(self._stop_publish)

            self._trigger_callbacks(
                self._publish_plugin_changed_callback_refs, plugin
            )
            if plugin.__instanceEnabled__:
                instances = pyblish.logic.instances_by_plugin(
                    self._publish_context, plugin
                )
                if not instances:
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
        self._publish_finished = True
        yield MainThreadItem(self._stop_publish)

    def _process_and_continue(self, plugin, instance):
        # TODO execute plugin
        result = pyblish.plugin.process(
            plugin, self._publish_context, instance
        )
        exception = result.get("error")
        if exception:
            if (
                isinstance(exception, PublishValidationError)
                and not self._publish_validated
            ):
                self._publish_validation_errors.append(exception)

            else:
                self._publish_error = exception

        self._publish_next_process()

    def get_asset_docs(self):
        return self._asset_docs_cache.get_asset_docs()

    def get_asset_hierarchy(self):
        _queue = collections.deque(self.get_asset_docs())

        output = collections.defaultdict(list)
        while _queue:
            asset_doc = _queue.popleft()
            parent_id = asset_doc["data"]["visualParent"]
            output[parent_id].append(asset_doc)
        return output

    def get_task_names_for_asset_names(self, asset_names):
        task_names_by_asset_name = (
            self._asset_docs_cache.get_task_names_by_asset_name()
        )
        tasks = None
        for asset_name in asset_names:
            task_names = set(task_names_by_asset_name.get(asset_name, []))
            if tasks is None:
                tasks = task_names
            else:
                tasks &= task_names

            if not tasks:
                break
        return tasks


def collect_families_from_instances(instances, only_active=False):
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
