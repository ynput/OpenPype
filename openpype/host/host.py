import logging
import contextlib
from abc import ABCMeta, abstractproperty, abstractmethod
import six

# NOTE can't import 'typing' because of issues in Maya 2020
#   - shiboken crashes on 'typing' module import


class MissingMethodsError(ValueError):
    """Exception when host miss some required methods for specific workflow.

    Args:
        host (HostBase): Host implementation where are missing methods.
        missing_methods (list[str]): List of missing methods.
    """

    def __init__(self, host, missing_methods):
        joined_missing = ", ".join(
            ['"{}"'.format(item) for item in missing_methods]
        )
        message = (
            "Host \"{}\" miss methods {}".format(host.name, joined_missing)
        )
        super(MissingMethodsError, self).__init__(message)


@six.add_metaclass(ABCMeta)
class HostBase(object):
    """Base of host implementation class.

    Host is pipeline implementation of DCC application. This class should help
    to identify what must/should/can be implemented for specific functionality.

    Compared to 'avalon' concept:
    What was before considered as functions in host implementation folder. The
    host implementation should primarily care about adding ability of creation
    (mark subsets to be published) and optionaly about referencing published
    representations as containers.

    Host may need extend some functionality like working with workfiles
    or loading. Not all host implementations may allow that for those purposes
    can be logic extended with implementing functions for the purpose. There
    are prepared interfaces to be able identify what must be implemented to
    be able use that functionality.
    - current statement is that it is not required to inherit from interfaces
        but all of the methods are validated (only their existence!)

    # Installation of host before (avalon concept):
    ```python
    from openpype.pipeline import install_host
    import openpype.hosts.maya.api as host

    install_host(host)
    ```

    # Installation of host now:
    ```python
    from openpype.pipeline import install_host
    from openpype.hosts.maya.api import MayaHost

    host = MayaHost()
    install_host(host)
    ```

    Todo:
        - move content of 'install_host' as method of this class
            - register host object
            - install legacy_io
            - install global plugin paths
        - store registered plugin paths to this object
        - handle current context (project, asset, task)
            - this must be done in many separated steps
        - have it's object of host tools instead of using globals

    This implementation will probably change over time when more
        functionality and responsibility will be added.
    """

    _log = None

    def __init__(self):
        """Initialization of host.

        Register DCC callbacks, host specific plugin paths, targets etc.
        (Part of what 'install' did in 'avalon' concept.)

        Note:
            At this moment global "installation" must happen before host
            installation. Because of this current limitation it is recommended
            to implement 'install' method which is triggered after global
            'install'.
        """

        pass

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @abstractproperty
    def name(self):
        """Host name."""

        pass

    def get_current_context(self):
        """Get current context information.

        This method should be used to get current context of host. Usage of
        this method can be crutial for host implementations in DCCs where
        can be opened multiple workfiles at one moment and change of context
        can't be catched properly.

        Default implementation returns values from 'legacy_io.Session'.

        Returns:
            dict: Context with 3 keys 'project_name', 'asset_name' and
                'task_name'. All of them can be 'None'.
        """

        from openpype.pipeline import legacy_io

        if legacy_io.is_installed():
            legacy_io.install()

        return {
            "project_name": legacy_io.Session["AVALON_PROJECT"],
            "asset_name": legacy_io.Session["AVALON_ASSET"],
            "task_name": legacy_io.Session["AVALON_TASK"]
        }

    def get_context_title(self):
        """Context title shown for UI purposes.

        Should return current context title if possible.

        Note:
            This method is used only for UI purposes so it is possible to
                return some logical title for contextless cases.
            Is not meant for "Context menu" label.

        Returns:
            str: Context title.
            None: Default title is used based on UI implementation.
        """

        # Use current context to fill the context title
        current_context = self.get_current_context()
        project_name = current_context["project_name"]
        asset_name = current_context["asset_name"]
        task_name = current_context["task_name"]
        items = []
        if project_name:
            items.append(project_name)
            if asset_name:
                items.append(asset_name)
                if task_name:
                    items.append(task_name)
        if items:
            return "/".join(items)
        return None

    @contextlib.contextmanager
    def maintained_selection(self):
        """Some functionlity will happen but selection should stay same.

        This is DCC specific. Some may not allow to implement this ability
        that is reason why default implementation is empty context manager.

        Yields:
            None: Yield when is ready to restore selected at the end.
        """

        try:
            yield
        finally:
            pass


class ILoadHost:
    """Implementation requirements to be able use reference of representations.

    The load plugins can do referencing even without implementation of methods
    here, but switch and removement of containers would not be possible.

    Questions:
        - Is list container dependency of host or load plugins?
        - Should this be directly in HostBase?
            - how to find out if referencing is available?
            - do we need to know that?
    """

    @staticmethod
    def get_missing_load_methods(host):
        """Look for missing methods on "old type" host implementation.

        Method is used for validation of implemented functions related to
        loading. Checks only existence of methods.

        Args:
            Union[ModuleType, HostBase]: Object of host where to look for
                required methods.

        Returns:
            list[str]: Missing method implementations for loading workflow.
        """

        if isinstance(host, ILoadHost):
            return []

        required = ["ls"]
        missing = []
        for name in required:
            if not hasattr(host, name):
                missing.append(name)
        return missing

    @staticmethod
    def validate_load_methods(host):
        """Validate implemented methods of "old type" host for load workflow.

        Args:
            Union[ModuleType, HostBase]: Object of host to validate.

        Raises:
            MissingMethodsError: If there are missing methods on host
                implementation.
        """
        missing = ILoadHost.get_missing_load_methods(host)
        if missing:
            raise MissingMethodsError(host, missing)

    @abstractmethod
    def get_referenced_containers(self):
        """Retreive referenced containers from scene.

        This can be implemented in hosts where referencing can be used.

        Todo:
            Rename function to something more self explanatory.
                Suggestion: 'get_referenced_containers'

        Returns:
            list[dict]: Information about loaded containers.
        """

        pass

    # --- Deprecated method names ---
    def ls(self):
        """Deprecated variant of 'get_referenced_containers'.

        Todo:
            Remove when all usages are replaced.
        """

        return self.get_referenced_containers()


@six.add_metaclass(ABCMeta)
class IWorkfileHost:
    """Implementation requirements to be able use workfile utils and tool."""

    @staticmethod
    def get_missing_workfile_methods(host):
        """Look for missing methods on "old type" host implementation.

        Method is used for validation of implemented functions related to
        workfiles. Checks only existence of methods.

        Args:
            Union[ModuleType, HostBase]: Object of host where to look for
                required methods.

        Returns:
            list[str]: Missing method implementations for workfiles workflow.
        """

        if isinstance(host, IWorkfileHost):
            return []

        required = [
            "open_file",
            "save_file",
            "current_file",
            "has_unsaved_changes",
            "file_extensions",
            "work_root",
        ]
        missing = []
        for name in required:
            if not hasattr(host, name):
                missing.append(name)
        return missing

    @staticmethod
    def validate_workfile_methods(host):
        """Validate methods of "old type" host for workfiles workflow.

        Args:
            Union[ModuleType, HostBase]: Object of host to validate.

        Raises:
            MissingMethodsError: If there are missing methods on host
                implementation.
        """

        missing = IWorkfileHost.get_missing_workfile_methods(host)
        if missing:
            raise MissingMethodsError(host, missing)

    @abstractmethod
    def get_workfile_extensions(self):
        """Extensions that can be used as save.

        Questions:
            This could potentially use 'HostDefinition'.
        """

        return []

    @abstractmethod
    def save_workfile(self, dst_path=None):
        """Save currently opened scene.

        Args:
            dst_path (str): Where the current scene should be saved. Or use
                current path if 'None' is passed.
        """

        pass

    @abstractmethod
    def open_workfile(self, filepath):
        """Open passed filepath in the host.

        Args:
            filepath (str): Path to workfile.
        """

        pass

    @abstractmethod
    def get_current_workfile(self):
        """Retreive path to current opened file.

        Returns:
            str: Path to file which is currently opened.
            None: If nothing is opened.
        """

        return None

    def workfile_has_unsaved_changes(self):
        """Currently opened scene is saved.

        Not all hosts can know if current scene is saved because the API of
        DCC does not support it.

        Returns:
            bool: True if scene is saved and False if has unsaved
                modifications.
            None: Can't tell if workfiles has modifications.
        """

        return None

    def work_root(self, session):
        """Modify workdir per host.

        Default implementation keeps workdir untouched.

        Warnings:
            We must handle this modification with more sofisticated way because
            this can't be called out of DCC so opening of last workfile
            (calculated before DCC is launched) is complicated. Also breaking
            defined work template is not a good idea.
            Only place where it's really used and can make sense is Maya. There
            workspace.mel can modify subfolders where to look for maya files.

        Args:
            session (dict): Session context data.

        Returns:
            str: Path to new workdir.
        """

        return session["AVALON_WORKDIR"]

    # --- Deprecated method names ---
    def file_extensions(self):
        """Deprecated variant of 'get_workfile_extensions'.

        Todo:
            Remove when all usages are replaced.
        """
        return self.get_workfile_extensions()

    def save_file(self, dst_path=None):
        """Deprecated variant of 'save_workfile'.

        Todo:
            Remove when all usages are replaced.
        """

        self.save_workfile()

    def open_file(self, filepath):
        """Deprecated variant of 'open_workfile'.

        Todo:
            Remove when all usages are replaced.
        """

        return self.open_workfile(filepath)

    def current_file(self):
        """Deprecated variant of 'get_current_workfile'.

        Todo:
            Remove when all usages are replaced.
        """

        return self.get_current_workfile()

    def has_unsaved_changes(self):
        """Deprecated variant of 'workfile_has_unsaved_changes'.

        Todo:
            Remove when all usages are replaced.
        """

        return self.workfile_has_unsaved_changes()


class INewPublisher:
    """Functions related to new creation system in new publisher.

    New publisher is not storing information only about each created instance
    but also some global data. At this moment are data related only to context
    publish plugins but that can extend in future.
    """

    @staticmethod
    def get_missing_publish_methods(host):
        """Look for missing methods on "old type" host implementation.

        Method is used for validation of implemented functions related to
        new publish creation. Checks only existence of methods.

        Args:
            Union[ModuleType, HostBase]: Host module where to look for
                required methods.

        Returns:
            list[str]: Missing method implementations for new publsher
                workflow.
        """

        if isinstance(host, INewPublisher):
            return []

        required = [
            "get_context_data",
            "update_context_data",
        ]
        missing = []
        for name in required:
            if not hasattr(host, name):
                missing.append(name)
        return missing

    @staticmethod
    def validate_publish_methods(host):
        """Validate implemented methods of "old type" host.

        Args:
            Union[ModuleType, HostBase]: Host module to validate.

        Raises:
            MissingMethodsError: If there are missing methods on host
                implementation.
        """
        missing = INewPublisher.get_missing_publish_methods(host)
        if missing:
            raise MissingMethodsError(host, missing)

    @abstractmethod
    def get_context_data(self):
        """Get global data related to creation-publishing from workfile.

        These data are not related to any created instance but to whole
        publishing context. Not saving/returning them will cause that each
        reset of publishing resets all values to default ones.

        Context data can contain information about enabled/disabled publish
        plugins or other values that can be filled by artist.

        Returns:
            dict: Context data stored using 'update_context_data'.
        """

        pass

    @abstractmethod
    def update_context_data(self, data, changes):
        """Store global context data to workfile.

        Called when some values in context data has changed.

        Without storing the values in a way that 'get_context_data' would
        return them will each reset of publishing cause loose of filled values
        by artist. Best practice is to store values into workfile, if possible.

        Args:
            data (dict): New data as are.
            changes (dict): Only data that has been changed. Each value has
                tuple with '(<old>, <new>)' value.
        """

        pass
