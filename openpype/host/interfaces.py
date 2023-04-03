from abc import ABCMeta, abstractmethod
import six


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
        host_name = getattr(host, "name", None)
        if not host_name:
            try:
                host_name = host.__file__.replace("\\", "/").split("/")[-3]
            except Exception:
                host_name = str(host)
        message = (
            "Host \"{}\" miss methods {}".format(host_name, joined_missing)
        )
        super(MissingMethodsError, self).__init__(message)


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
    def get_containers(self):
        """Retrieve referenced containers from scene.

        This can be implemented in hosts where referencing can be used.

        Todo:
            Rename function to something more self explanatory.
                Suggestion: 'get_containers'

        Returns:
            list[dict]: Information about loaded containers.
        """

        pass

    # --- Deprecated method names ---
    def ls(self):
        """Deprecated variant of 'get_containers'.

        Todo:
            Remove when all usages are replaced.
        """

        return self.get_containers()


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
        """Retrieve path to current opened file.

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
            We must handle this modification with more sophisticated way
            because this can't be called out of DCC so opening of last workfile
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

        self.save_workfile(dst_path)

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


class IPublishHost:
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
            list[str]: Missing method implementations for new publisher
                workflow.
        """

        if isinstance(host, IPublishHost):
            return []

        required = [
            "get_context_data",
            "update_context_data",
            "get_context_title",
            "get_current_context",
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
        missing = IPublishHost.get_missing_publish_methods(host)
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


class INewPublisher(IPublishHost):
    """Legacy interface replaced by 'IPublishHost'.

    Deprecated:
        'INewPublisher' is replaced by 'IPublishHost' please change your
        imports.
        There is no "reasonable" way hot mark these classes as deprecated
        to show warning of wrong import. Deprecated since 3.14.* will be
        removed in 3.15.*
    """

    pass
