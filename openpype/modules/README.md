# OpenPype modules/addons
OpenPype modules should contain separated logic of specific kind of implementation, such as Ftrack connection and its usage code, Deadline farm rendering or may contain only special plugins. Addons work the same way currently, there is no difference between module and addon functionality.

## Modules concept
- modules and addons are dynamically imported to virtual python module `openpype_modules` from which it is possible to import them no matter where is the module located
- modules or addons should never be imported directly, even if you know possible full import path
 - it is because all of their content must be imported in specific order and should not be imported without defined functions as it may also break few implementation parts

### TODOs
- add module/addon manifest
 - definition of module (not 100% defined content e.g. minimum required OpenPype version etc.)
 - defining a folder as a content of a module or an addon

## Base class `OpenPypeModule`
- abstract class as base for each module
- implementation should contain module's api without GUI parts
- may implement `get_global_environments` method which should return dictionary of environments that are globally applicable and value is the same for whole studio if launched at any workstation (except os specific paths)
- abstract parts:
 - `name` attribute - name of a module
 - `initialize` method - method for own initialization of a module (should not override `__init__`)
 - `connect_with_modules` method - where module may look for it's interfaces implementations or check for other modules
- `__init__` should not be overridden and `initialize` should not do time consuming part but only prepare base data about module
 - also keep in mind that they may be initialized in headless mode
- connection with other modules is made with help of interfaces
- `cli` method - add cli commands specific for the module
    - command line arguments are handled using `click` python module
    - `cli` method should expect single argument which is click group on which can be called any group specific methods (e.g. `add_command` to add another click group as children see `ExampleAddon`)
    - it is possible to add trigger cli commands using `./openpype_console module <module_name> <command> *args`

## Addon class `OpenPypeAddOn`
- inherits from `OpenPypeModule` but is enabled by default and doesn't have to implement `initialize` and `connect_with_modules` methods
 - that is because it is expected that addons don't need to have system settings and `enabled` value on it (but it is possible...)

## How to add addons/modules
- in System settings go to `modules/addon_paths` (`Modules/OpenPype AddOn Paths`) where you have to add path to addon root folder
- for openpype example addons use `{OPENPYPE_REPOS_ROOT}/openpype/modules/example_addons`

## Addon/module settings
- addons/modules may have defined custom settings definitions with default values
- it is based on settings type `dynamic_schema` which has `name`
 - that item defines that it can be replaced dynamically with any schemas from module or module which won't be saved to openpype core defaults
 - they can't be added to any schema hierarchy
 - item must not be in settings group (under overrides) or in dynamic item (e.g. `list` of `dict-modifiable`)
 - addons may define it's dynamic schema items
- they can be defined with class which inherits from `BaseModuleSettingsDef`
 - it is recommended to use pre implemented `JsonFilesSettingsDef` which defined structure and use json files to define dynamic schemas, schemas and default values
 - check it's docstring and check for `example_addon` in example addons
- settings definition returns schemas by dynamic schemas names

# Interfaces
- interface is class that has defined abstract methods to implement and may contain pre implemented helper methods
- module that inherit from an interface must implement those abstract methods otherwise won't be initialized
- it is easy to find which module object inherited from which interfaces with 100% chance they have implemented required methods
- interfaces can be defined in `interfaces.py` inside module directory
 - the file can't use relative imports or import anything from other parts
 of module itself at the header of file
 - this is one of reasons why modules/addons can't be imported directly without using defined functions in OpenPype modules implementation

## Base class `OpenPypeInterface`
- has nothing implemented
- has ABCMeta as metaclass
- is defined to be able find out classes which inherit from this base to be
 able tell this is an Interface

## Global interfaces
- few interfaces are implemented for global usage

### IPluginPaths
- module wants to add directory path/s to avalon or publish plugins
- module must implement `get_plugin_paths` which must return dictionary with possible keys `"publish"`, `"load"`, `"create"` or `"actions"`
 - each key may contain list or string with a path to directory with plugins

### ITrayModule
- module has more logic when used in a tray
 - it is possible that module can be used only in the tray
- abstract methods
 - `tray_init` - initialization triggered after `initialize` when used in `TrayModulesManager` and before `connect_with_modules`
 - `tray_menu` - add actions to tray widget's menu that represent the module
 - `tray_start` - start of module's login in tray
 - module is initialized and connected with other modules
 - `tray_exit` - module's cleanup like stop and join threads etc.
 - order of calling is based on implementation this order is how it works with `TrayModulesManager`
 - it is recommended to import and use GUI implementation only in these methods
- has attribute `tray_initialized` (bool) which is set to False by default and is set by `TrayModulesManager` to True after `tray_init`
 - if module has logic only in tray or for both then should be checking for `tray_initialized` attribute to decide how should handle situations

### ITrayService
- inherits from `ITrayModule` and implements `tray_menu` method for you
 - adds action to submenu "Services" in tray widget menu with icon and label
- abstract attribute `label`
 - label shown in menu
- interface has pre implemented methods to change icon color
 - `set_service_running` - green icon
 - `set_service_failed` - red icon
 - `set_service_idle` - orange icon
 - these states must be set by module itself `set_service_running` is default state on initialization

### ITrayAction
- inherits from `ITrayModule` and implements `tray_menu` method for you
 - adds action to tray widget menu with label
- abstract attribute `label`
 - label shown in menu
- abstract method `on_action_trigger`
 - what should happen when an action is triggered
- NOTE: It is a good idea to implement logic in `on_action_trigger` to the api method and trigger that method on callbacks. This gives ability to trigger that method outside tray

## Modules interfaces
- modules may have defined their own interfaces to be able to recognize other modules that would want to use their features

### Example:
- Ftrack module has `IFtrackEventHandlerPaths` which helps to tell Ftrack module which other modules want to add paths to server/user event handlers
 - Clockify module use `IFtrackEventHandlerPaths` and returns paths to clockify ftrack synchronizers

- Clockify inherits from more interfaces. It's class definition looks like:
```
class ClockifyModule(
 OpenPypeModule, # Says it's Pype module so ModulesManager will try to initialize.
 ITrayModule, # Says has special implementation when used in tray.
 IPluginPaths, # Says has plugin paths that want to register (paths to clockify actions for launcher).
 IFtrackEventHandlerPaths, # Says has Ftrack actions/events for user/server.
 ITimersManager # Listen to other modules with timer and can trigger changes in other module timers through `TimerManager` module.
):
```

### ModulesManager
- collects module classes and tries to initialize them
- important attributes
 - `modules` - list of available attributes
 - `modules_by_id` - dictionary of modules mapped by their ids
 - `modules_by_name` - dictionary of modules mapped by their names
 - all these attributes contain all found modules even if are not enabled
- helper methods
 - `collect_global_environments` to collect all global environments from enabled modules with calling `get_global_environments` on each of them
 - `collect_plugin_paths` collects plugin paths from all enabled modules
 - output is always dictionary with all keys and values as an list
 ```
 {
 "publish": [],
 "create": [],
 "load": [],
 "actions": []
 }
 ```

### TrayModulesManager
- inherits from `ModulesManager`
- has specific implementation for Pype Tray tool and handle `ITrayModule` methods
