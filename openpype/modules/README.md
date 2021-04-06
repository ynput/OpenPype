# Pype modules
Pype modules should contain separated logic of specific kind of implementation, like Ftrack connection and usage code or Deadline farm rendering.

## Base class `PypeModule`
- abstract class as base for each module
- implementation should be module's api withou GUI parts
- may implement `get_global_environments` method which should return dictionary of environments that are globally appliable and value is the same for whole studio if launched at any workstation (except os specific paths)
- abstract parts:
    - `name` attribute - name of a module
    - `initialize` method - method for own initialization of a module (should not override `__init__`)
    - `connect_with_modules` method - where module may look for it's interfaces implementations or check for other modules
- `__init__` should not be overriden and `initialize` should not do time consuming part but only prepare base data about module
    - also keep in mind that they may be initialized in headless mode
- connection with other modules is made with help of interfaces

# Interfaces
- interface is class that has defined abstract methods to implement and may contain preimplemented helper methods
- module that inherit from an interface must implement those abstract methods otherwise won't be initialized
- it is easy to find which module object inherited from which interfaces withh 100% chance they have implemented required methods

## Global interfaces
- few interfaces are implemented for global usage

### IPluginPaths
- module want to add directory path/s to avalon or publish plugins
- module must implement `get_plugin_paths` which must return dictionary with possible keys `"publish"`, `"load"`, `"create"` or `"actions"`
    - each key may contain list or string with path to directory with plugins

### ITrayModule
- module has more logic when used in tray
    - it is possible that module can be used only in tray
- abstract methods
    - `tray_init` - initialization triggered after `initialize` when used in `TrayModulesManager` and before `connect_with_modules`
    - `tray_menu` - add actions to tray widget's menu that represent the module
    - `tray_start` - start of module's login in tray
        - module is initialized and connected with other modules
    - `tray_exit` - module's cleanup like stop and join threads etc.
    - order of calling is based on implementation this order is how it works with `TrayModulesManager`
    - it is recommended to import and use GUI implementaion only in these methods
- has attribute `tray_initialized` (bool) which is set to False by default and is set by `TrayModulesManager` to True after `tray_init`
    - if module has logic only in tray or for both then should be checking for `tray_initialized` attribute to decide how should handle situations

### ITrayService
- inherit from `ITrayModule` and implement `tray_menu` method for you
    - add action to submenu "Services" in tray widget menu with icon and label
- abstract atttribute `label`
    - label shown in menu
- interface has preimplemented methods to change icon color
    - `set_service_running` - green icon
    - `set_service_failed` - red icon
    - `set_service_idle` - orange icon
    - these states must be set by module itself `set_service_running` is default state on initialization

### ITrayAction
- inherit from `ITrayModule` and implement `tray_menu` method for you
    - add action to tray widget menu with label
- abstract atttribute `label`
    - label shown in menu
- abstract method `on_action_trigger`
    - what should happen when action is triggered
- NOTE: It is good idea to implement logic in `on_action_trigger` to api method and trigger that methods on callbacks this gives ability to trigger that method outside tray

## Modules interfaces
- modules may have defined their interfaces to be able recognize other modules that would want to use their features
-
### Example:
- Ftrack module has `IFtrackEventHandlerPaths` which helps to tell Ftrack module which of other modules want to add paths to server/user event handlers
    - Clockify module use `IFtrackEventHandlerPaths` and return paths to clockify ftrack synchronizers

- Clockify has more inharitance it's class definition looks like
```
class ClockifyModule(
    PypeModule, # Says it's Pype module so ModulesManager will try to initialize.
    ITrayModule, # Says has special implementation when used in tray.
    IPluginPaths, # Says has plugin paths that want to register (paths to clockify actions for launcher).
    IFtrackEventHandlerPaths, # Says has Ftrack actions/events for user/server.
    ITimersManager # Listen to other modules with timer and can trigger changes in other module timers through `TimerManager` module.
):
```

### ModulesManager
- collect module classes and tries to initialize them
- important attributes
    - `modules` - list of available attributes
    - `modules_by_id` - dictionary of modules mapped by their ids
    - `modules_by_name` - dictionary of modules mapped by their names
    - all these attributes contain all found modules even if are not enabled
- helper methods
    - `collect_global_environments` to collect all global environments from enabled modules with calling `get_global_environments` on each of them
    - `collect_plugin_paths` collect plugin paths from all enabled modules
        - output is always dictionary with all keys and values as list
            ```
            {
                "publish": [],
                "create": [],
                "load": [],
                "actions": []
            }
            ```

### TrayModulesManager
- inherit from `ModulesManager`
- has specific implementations for Pype Tray tool and handle `ITrayModule` methods
