import collections

from Qt import QtCore

from openpype.pipeline.create import CreatedInstance

from .control import MainThreadItem, PublisherController


class MainThreadProcess(QtCore.QObject):
    """Qt based main thread process executor.

    Has timer which controls each 50ms if there is new item to process.

    This approach gives ability to update UI meanwhile plugin is in progress.
    """

    count_timeout = 2

    def __init__(self):
        super(MainThreadProcess, self).__init__()
        self._items_to_process = collections.deque()

        timer = QtCore.QTimer()
        timer.setInterval(0)

        timer.timeout.connect(self._execute)

        self._timer = timer
        self._switch_counter = self.count_timeout

    def process(self, func, *args, **kwargs):
        item = MainThreadItem(func, *args, **kwargs)
        self.add_item(item)

    def add_item(self, item):
        self._items_to_process.append(item)

    def _execute(self):
        if not self._items_to_process:
            return

        if self._switch_counter > 0:
            self._switch_counter -= 1
            return

        self._switch_counter = self.count_timeout

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


class QtPublisherController(PublisherController):
    def __init__(self, *args, **kwargs):
        self._main_thread_processor = MainThreadProcess()

        super(QtPublisherController, self).__init__(*args, **kwargs)

        self.event_system.add_callback(
            "publish.process.started", self._qt_on_publish_start
        )
        self.event_system.add_callback(
            "publish.process.stopped", self._qt_on_publish_stop
        )

    def _reset_publish(self):
        super(QtPublisherController, self)._reset_publish()
        self._main_thread_processor.clear()

    def _process_main_thread_item(self, item):
        self._main_thread_processor.add_item(item)

    def _qt_on_publish_start(self):
        self._main_thread_processor.start()

    def _qt_on_publish_stop(self):
        self._main_thread_processor.stop()


class QtRemotePublishController(QtPublisherController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._created_instances = {}

    def _on_create_instance_change(self):
        # TODO somehow get serialized instances from client
        serialized_instances = []

        created_instances = {}
        for serialized_data in serialized_instances:
            item = CreatedInstance.deserialize_on_remote(
                serialized_data,
                self._creator_items
            )
            created_instances[item.id] = item

        self._created_instances = created_instances
        self._emit_event("instances.refresh.finished")

    @property
    def project_name(self):
        """Current context project name.

        Returns:
            str: Name of project.
        """

        pass

    @property
    def current_asset_name(self):
        """Current context asset name.

        Returns:
            Union[str, None]: Name of asset.
        """

        pass

    @property
    def current_task_name(self):
        """Current context task name.

        Returns:
            Union[str, None]: Name of task.
        """

        pass

    @property
    def host_is_valid(self):
        """Host is valid for creation part.

        Host must have implemented certain functionality to be able create
        in Publisher tool.

        Returns:
            bool: Host can handle creation of instances.
        """

        pass

    @property
    def instances(self):
        """Collected/created instances.

        Returns:
            List[CreatedInstance]: List of created instances.
        """

        return self._created_instances

    def get_context_title(self):
        """Get context title for artist shown at the top of main window.

        Returns:
            Union[str, None]: Context title for window or None. In case of None
                a warning is displayed (not nice for artists).
        """

        pass

    def get_asset_docs(self):
        pass

    def get_asset_hierarchy(self):
        pass

    def get_task_names_by_asset_names(self, asset_names):
        pass

    def get_existing_subset_names(self, asset_name):
        pass

    def reset(self):
        """Reset whole controller.

        This should reset create context, publish context and all variables
        that are related to it.
        """

        pass

    def get_publish_attribute_definitions(self, instances, include_context):
        pass

    def get_subset_name(
        self,
        creator_identifier,
        variant,
        task_name,
        asset_name,
        instance_id=None
    ):
        """Get subset name based on passed data.

        Args:
            creator_identifier (str): Identifier of creator which should be
                responsible for subset name creation.
            variant (str): Variant value from user's input.
            task_name (str): Name of task for which is instance created.
            asset_name (str): Name of asset for which is instance created.
            instance_id (Union[str, None]): Existing instance id when subset
                name is updated.
        """

        pass

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

        pass

    def save_changes(self):
        """Save changes happened during creation."""

        created_instance_changes = {}
        for instance_id, instance in self._created_instances.items():
            created_instance_changes[instance_id] = (
                instance.remote_changes()
            )

        # TODO trigger save changes
        self._trigger("save_changes", created_instance_changes)

    def remove_instances(self, instances):
        """Remove list of instances from create context."""
        # TODO add Args:

        pass

    @property
    def publish_has_finished(self):
        """Has publishing finished.

        Returns:
            bool: If publishing finished and all plugins were iterated.
        """

        pass

    @property
    def publish_is_running(self):
        """Publishing is running right now.

        Returns:
            bool: If publishing is in progress.
        """

        pass

    @property
    def publish_has_validated(self):
        """Publish validation passed.

        Returns:
            bool: If publishing passed last possible validation order.
        """

        pass

    @property
    def publish_has_crashed(self):
        """Publishing crashed for any reason.

        Returns:
            bool: Publishing crashed.
        """

        pass

    @property
    def publish_has_validation_errors(self):
        """During validation happened at least one validation error.

        Returns:
            bool: Validation error was raised during validation.
        """

        pass

    @property
    def publish_max_progress(self):
        """Get maximum possible progress number.

        Returns:
            int: Number that can be used as 100% of publish progress bar.
        """

        pass

    @property
    def publish_progress(self):
        """Current progress number.

        Returns:
            int: Current progress value which is between 0 and
                'publish_max_progress'.
        """

        pass

    @property
    def publish_comment_is_set(self):
        """Publish comment was at least once set.

        Publish comment can be set only once when publish is started for a
        first time. This helpt to idetify if 'set_comment' should be called or
        not.
        """

        pass

    def get_publish_crash_error(self):
        pass

    def get_publish_report(self):
        pass

    def get_validation_errors(self):
        pass

    def publish(self):
        """Trigger publishing without any order limitations."""

        pass

    def validate(self):
        """Trigger publishing which will stop after validation order."""

        pass

    def stop_publish(self):
        """Stop publishing can be also used to pause publishing.

        Pause of publishing is possible only if all plugins successfully
        finished.
        """

        pass

    def run_action(self, plugin_id, action_id):
        """Trigger pyblish action on a plugin.

        Args:
            plugin_id (str): Id of publish plugin.
            action_id (str): Id of publish action.
        """

        pass

    def set_comment(self, comment):
        """Set comment on pyblish context.

        Set "comment" key on current pyblish.api.Context data.

        Args:
            comment (str): Artist's comment.
        """

        pass

    def emit_card_message(self, message):
        """Emit a card message which can have a lifetime.

        This is for UI purposes. Method can be extended to more arguments
        in future e.g. different message timeout or type (color).

        Args:
            message (str): Message that will be showed.
        """

        pass
