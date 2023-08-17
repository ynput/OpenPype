from __future__ import annotations

import datetime
import os
import sharktools_base.api as st_api
import stat
import threading
import uuid
import tool_settings.tool_settings as tool_settings
import reporting.log as log

from . import p4_errors

_typing = False
if _typing:
    from typing import Any
    from typing import Callable
    from typing import Iterable
del _typing


class P4ConnectionManager:
    @property
    def log(self):
        if not hasattr(self, "_log"):
            self._log = log.get_advanced_logger(__name__)

        return self._log

    def checkout(
        self,
        paths: Iterable[str],
        change_description: str | None = None
    ) -> list[bool]:
        result = []
        writable_files = []
        for path in paths:
            path = st_api.path.NiftyPath(path)
            path.chmod(stat.S_IWRITE)
            is_writable = os.access(path, os.R_OK, follow_symlinks=True)
            result.append(is_writable)
            if is_writable:
                writable_files.append(path)

        return result

    def revert(self, *args, **kwargs):
        raise p4_errors.P4UnsafeOfflineCommandError("revert")

    def submit(self, *args, **kwargs):
        raise p4_errors.P4UnsafeOfflineCommandError("submit")

    def reconcile_checkout(
        self,
        paths: Iterable[str],
        change_description: str | None = None
    ):
        for path in paths:
            path = st_api.path.NiftyPath(path)
            path.chmod(stat.S_IREAD)
            # is_writable = os.access(path, os.R_OK, follow_symlinks=True)

        # return result

    def run_function(self, function: Callable[..., Any], args: tuple[Any], kwargs: dict[str, Any]):
        function_name = function.__name__.replace("_connect_", "")
        offline_function = getattr(self, function_name, None)  # type: Callable[..., Any] | None
        result = offline_function(*args, **kwargs) if offline_function else None
        self.cache_action(function_name, *args, **kwargs)
        return result

    def cache_action(self, action: str, *args: Any, **kwargs: Any):
        actions = self.load_cache()
        actions.append(
            {
                "action": action,
                "date": str(datetime.datetime.now().strftime("%A: %d/%m/%y %H:%M")),
                "id": str(uuid.uuid1()),
                "args": args,
                "kwargs": kwargs
            }
        )
        tool_settings.save_setting("p4_offline_cache", "actions", actions)

    def _reconcile(self, actions: list[dict[str, Any]] | None = None):
        """
        Attempt to run all the cached actions from when the user was offline.
        """
        from p4 import p4

        actions = actions or tool_settings.get_setting(
            "p4_offline_cache", "actions", default_setting_value=[]
        )
        if not actions:
            raise RuntimeError("No cached actions found!")

        for data in actions:
            action, _, _, args, kwargs = data.values()
            self.log.info(f"Running action: {action}")
            reconcile_function = getattr(self, f"reconcile_{action}", None)
            if reconcile_function:
                self.log.info(f"Running reconcile_function: {reconcile_function.__name__}")
                reconcile_function(*args, **kwargs)
            else:
                self.log.warning(f"No reconcile function found for action: {action}")

            p4_function = getattr(p4, action, None)
            if not p4_function:
                self.log.warning(f"No p4 function found for action: {action}")
                continue

            self.log.info(f"Running p4_function: {p4_function.__name__}")
            result = p4_function(*args, **kwargs)
            yield result

    def get_reconcile_generator(self, actions: list[dict[str, Any]] | None = None):
        return self._reconcile(actions=actions)

    def reconcile(self, actions: list[dict[str, Any]] | None = None):
        _reconcile = self._reconcile(actions=actions)
        results = []
        while True:
            try:
                result = next(_reconcile)
                results.append(result)
            except StopIteration:
                break

        return results

    def load_cache(self) -> dict[str, Any]:
        return tool_settings.get_setting(
            "p4_offline_cache", "actions", default_setting_value=[]
        )

    def save_cache(self, actions: list[dict[str, Any]]):
        return tool_settings.save_setting("p4_offline_cache", "actions", actions)

    def delete_actions(self, actions: list[dict[str, Any]]):
        actions_to_keep = []
        action_ids_to_delete = (action["id"]for action in actions)
        for action in self.load_cache():
            if action["id"] in action_ids_to_delete:
                continue
            actions_to_keep.append(action)

        self.save_cache(actions_to_keep)



_connection_manager = None


def _get_connection_manager() -> P4ConnectionManager:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError(
            (
                "This function can only be called in the main thread!\n"
                " - For P4 use in a thread use a new instance of P4ConnectionManager."
            )
        )

    global _connection_manager
    if _connection_manager is None:
        _connection_manager = P4ConnectionManager()

    return _connection_manager


def show_offline_manager_if_actions_are_cached(force: bool = False):
    connection_manager = _get_connection_manager()
    if not connection_manager.load_cache() and not force:
        return

    from . import p4

    if p4.is_offline and not force:
        return

    from . import ui
    import qt_sm.environment as sm_environment

    return sm_environment.create_native_widget_from_class(
        ui.P4OfflineWidget, "p4_offline_widget"
    )


__all__ = (
    "P4ConnectionManager",
    "cache_action",  # type: ignore
    "checkout",  # type: ignore
    "load_cache",  # type: ignore
    "save_cache",  # type: ignore
    "delete_actions",  # type: ignore
    "show_offline_manager_if_actions_are_cached",  # type: ignore
)


def __getattr__(attribute_name: str) -> Any:
    """
    Custom __getattr__ for this module that will return
    the method of the module level P4ConnectionManager.

        This achieves two things:
            1. Allows a single P4ConnectionManager to be used for one off calls
                in the main thread, without the need to init a new P4ConnectionManager
                for each call.
            2. Reduces the boilerplate required to expose the calls of the single
                P4ConnectionManager, whilst still making the functionality
                accessible at the module level.

        Args:
            attribute_name (str): The name of the module level attribute to access.

        Returns:
            Any: The accessed attribute.
    """

    connection_manager = _get_connection_manager()
    if hasattr(connection_manager, attribute_name):
        return getattr(connection_manager, attribute_name)

    _globals = globals()
    if attribute_name in _globals:
        return getattr(_globals, attribute_name)

    raise AttributeError(f"{__name__} has no attribute: {attribute_name}!")


def __dir__():
    return __all__


if __name__ == "__main__":
    def _connect_checkout():
        pass

    def _connect_revert():
        pass

    path = ["C:/p4ws/sharkmob/Tools/tech_art/base/_standalone/python/sharktools/p4/p4_test/checkout_test.txt"]
    cm = P4ConnectionManager()
    cm.run_function(_connect_checkout, (path,), {})
    # cm.run_function(_connect_revert, (path,), {})
    # path = ["C:/p4ws/sharkmob/Tools/tech_art/base/_standalone/python/sharktools/p4/p4_test/submit_test.txt"]
    # cm.run_function(_connect_checkout, (path,), {})
    # cm.reconcile()
