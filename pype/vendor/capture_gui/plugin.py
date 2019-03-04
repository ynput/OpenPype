"""Plug-in system

Works similar to how OSs look for executables; i.e. a number of
absolute paths are searched for a given match. The predicate for
executables is whether or not an extension matches a number of
options, such as ".exe" or ".bat".

In this system, the predicate is whether or not a fname ends with ".py"

"""

# Standard library
import os
import sys
import types
import logging
import inspect

from .vendor.Qt import QtCore, QtWidgets

log = logging.getLogger(__name__)

_registered_paths = list()
_registered_plugins = dict()


class classproperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class Plugin(QtWidgets.QWidget):
    """Base class for Option plug-in Widgets.

    This is a regular Qt widget that can be added to the capture interface
    as an additional component, like a plugin.
    
    The plug-ins are sorted in the interface by their `order` attribute and
    will be displayed in the main interface when `section` is set to "app"
    and displayed in the additional settings pop-up when set to "config".
    
    When `hidden` is set to True the widget will not be shown in the interface.
    This could be useful as a plug-in that supplies solely default values to
    the capture GUI command.

    """

    label = ""
    section = "app"  # "config" or "app"
    hidden = False
    options_changed = QtCore.Signal()
    label_changed = QtCore.Signal(str)
    order = 0
    highlight = "border: 1px solid red;"
    validate_state = True

    def on_playblast_finished(self, options):
        pass

    def validate(self):
        """
        Ensure outputs of the widget are possible, when errors are raised it
        will return a message with what has caused the error
        :return: 
        """
        errors = []
        return errors

    def get_outputs(self):
        """Return the options as set in this plug-in widget.

        This is used to identify the settings to be used for the playblast.
        As such the values should be returned in a way that a call to
        `capture.capture()` would understand as arguments.

        Args:
            panel (str): The active modelPanel of the user. This is passed so
                values could potentially be parsed from the active panel

        Returns:
            dict: The options for this plug-in. (formatted `capture` style)

        """
        return dict()

    def get_inputs(self, as_preset):
        """Return widget's child settings.
        
        This should provide a dictionary of input settings of the plug-in
        that results in a dictionary that can be supplied to `apply_input()`
        This is used to save the settings of the preset to a widget.
        
        :param as_preset: 
        :param as_presets: Toggle to mute certain input values of the widget
        :type as_presets: bool
        
        Returns:
            dict: The currently set inputs of this widget.
         
        """
        return dict()

    def apply_inputs(self, settings):
        """Apply a dictionary of settings to the widget.
        
        This should update the widget's inputs to the settings provided in 
        the dictionary. This is used to apply settings from a preset.
        
        Returns:
            None
        
        """
        pass

    def initialize(self):
        """
        This method is used to register any callbacks
        :return: 
        """
        pass

    def uninitialize(self):
        """
        Unregister any callback created when deleting the widget
        
        A general explation:

        The deletion method is an attribute that lives inside the object to be
        deleted, and that is the problem:
        Destruction seems not to care about the order of destruction,
        and the __dict__ that also holds the onDestroy bound method
        gets destructed before it is called.
        
        Another solution is to use a weakref
        
        :return: None 
        """
        pass

    def __str__(self):
        return self.label or type(self).__name__

    def __repr__(self):
        return u"%s.%s(%r)" % (__name__, type(self).__name__, self.__str__())

    id = classproperty(lambda cls: cls.__name__)


def register_plugin_path(path):
    """Plug-ins are looked up at run-time from directories registered here

    To register a new directory, run this command along with the absolute
    path to where you"re plug-ins are located.

    Example:
        >>> import os
        >>> my_plugins = "/server/plugins"
        >>> register_plugin_path(my_plugins)
        '/server/plugins'

    Returns:
        Actual path added, including any post-processing

    """

    if path in _registered_paths:
        return log.warning("Path already registered: {0}".format(path))

    _registered_paths.append(path)

    return path


def deregister_plugin_path(path):
    """Remove a _registered_paths path

    Raises:
        KeyError if `path` isn't registered

    """

    _registered_paths.remove(path)


def deregister_all_plugin_paths():
    """Mainly used in tests"""
    _registered_paths[:] = []


def registered_plugin_paths():
    """Return paths added via registration

    ..note:: This returns a copy of the registered paths
        and can therefore not be modified directly.

    """

    return list(_registered_paths)


def registered_plugins():
    """Return plug-ins added via :func:`register_plugin`

    .. note:: This returns a copy of the registered plug-ins
        and can therefore not be modified directly

    """

    return _registered_plugins.values()


def register_plugin(plugin):
    """Register a new plug-in

    Arguments:
        plugin (Plugin): Plug-in to register

    Raises:
        TypeError if `plugin` is not callable

    """

    if not hasattr(plugin, "__call__"):
        raise TypeError("Plug-in must be callable "
                        "returning an instance of a class")

    if not plugin_is_valid(plugin):
        raise TypeError("Plug-in invalid: %s", plugin)

    _registered_plugins[plugin.__name__] = plugin


def plugin_paths():
    """Collect paths from all sources.

    This function looks at the three potential sources of paths
    and returns a list with all of them together.

    The sources are:

    - Registered paths using :func:`register_plugin_path`

    Returns:
        list of paths in which plugins may be locat

    """

    paths = list()

    for path in registered_plugin_paths():
        if path in paths:
            continue
        paths.append(path)

    return paths


def discover(paths=None):
    """Find and return available plug-ins

    This function looks for files within paths registered via
    :func:`register_plugin_path`.

    Arguments:
        paths (list, optional): Paths to discover plug-ins from.
            If no paths are provided, all paths are searched.

    """

    plugins = dict()

    # Include plug-ins from registered paths
    for path in paths or plugin_paths():
        path = os.path.normpath(path)

        if not os.path.isdir(path):
            continue

        for fname in os.listdir(path):
            if fname.startswith("_"):
                continue

            abspath = os.path.join(path, fname)

            if not os.path.isfile(abspath):
                continue

            mod_name, mod_ext = os.path.splitext(fname)

            if not mod_ext == ".py":
                continue

            module = types.ModuleType(mod_name)
            module.__file__ = abspath

            try:
                execfile(abspath, module.__dict__)

                # Store reference to original module, to avoid
                # garbage collection from collecting it's global
                # imports, such as `import os`.
                sys.modules[mod_name] = module

            except Exception as err:
                log.debug("Skipped: \"%s\" (%s)", mod_name, err)
                continue

            for plugin in plugins_from_module(module):
                if plugin.id in plugins:
                    log.debug("Duplicate plug-in found: %s", plugin)
                    continue

                plugins[plugin.id] = plugin

    # Include plug-ins from registration.
    # Directly registered plug-ins take precedence.
    for name, plugin in _registered_plugins.items():
        if name in plugins:
            log.debug("Duplicate plug-in found: %s", plugin)
            continue
        plugins[name] = plugin

    plugins = list(plugins.values())
    sort(plugins)  # In-place

    return plugins


def plugins_from_module(module):
    """Return plug-ins from module

    Arguments:
        module (types.ModuleType): Imported module from which to
            parse valid plug-ins.

    Returns:
        List of plug-ins, or empty list if none is found.

    """

    plugins = list()

    for name in dir(module):
        if name.startswith("_"):
            continue

        # It could be anything at this point
        obj = getattr(module, name)

        if not inspect.isclass(obj):
            continue

        if not issubclass(obj, Plugin):
            continue

        if not plugin_is_valid(obj):
            log.debug("Plug-in invalid: %s", obj)
            continue

        plugins.append(obj)

    return plugins


def plugin_is_valid(plugin):
    """Determine whether or not plug-in `plugin` is valid

    Arguments:
        plugin (Plugin): Plug-in to assess

    """

    if not plugin:
        return False

    return True


def sort(plugins):
    """Sort `plugins` in-place

    Their order is determined by their `order` attribute.

    Arguments:
        plugins (list): Plug-ins to sort

    """

    if not isinstance(plugins, list):
        raise TypeError("plugins must be of type list")

    plugins.sort(key=lambda p: p.order)
    return plugins


# Register default paths
default_plugins_path = os.path.join(os.path.dirname(__file__), "plugins")
register_plugin_path(default_plugins_path)
