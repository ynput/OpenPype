# Architecture

OpenPype is a monolithic Python project that bundles several parts, this document will try to give a birds eye overview of the project and, to a certain degree, each of the sub-projects.
The current file structure looks like this:

```
.
├── common - Code in this folder is backend portion of Addon distribution logic for v4 server.
├── docs - Documentation of the source code.
├── igniter - The OpenPype bootstrapper, deals with running version resolution and setting up the connection to the mongodb.
├── openpype - The actual OpenPype core package.
├── schema - Collection of JSON files describing schematics of objects. This follows Avalon's convention.
├── tests - Integration and unit tests.
├── tools - Conveninece scripts to perform common actions (in both bash and ps1).
├── vendor - When using the igniter, it deploys third party tools in here, such as ffmpeg.
└── website - Source files for https://openpype.io/ which is Docusaursus (https://docusaurus.io/).
```

The core functionality of the pipeline can be found in `igniter` and `openpype`, which in turn rely on the `schema` files, whenever you build (or download a pre-built) version of OpenPype, these two are bundled in there, and `Igniter` is the entry point.


## Igniter

It's the setup and update tool for OpenPype, unless you want to package `openpype` separately and deal with all the config manually, this will most likely be your entry point.

```
igniter/
├── bootstrap_repos.py - Module that will find or install OpenPype versions in the system.
├── __init__.py - Igniter entry point.
├── install_dialog.py- Show dialog for choosing central pype repository.
├── install_thread.py - Threading helpers for the install process.
├── __main__.py - Like `__init__.py` ?
├── message_dialog.py - Qt Dialog with a message and "Ok" button.
├── nice_progress_bar.py - Fancy Qt progress bar.
├── splash.txt - ASCII art for the terminal installer.
├── stylesheet.css - Installer Qt styles.
├── terminal_splash.py - Terminal installer animation, relies in `splash.txt`.
├── tools.py - Collection of methods that don't fit in other modules.
├── update_thread.py - Threading helper to update existing OpenPype installs.
├── update_window.py - Qt UI to update OpenPype installs. 
├── user_settings.py - Interface for the OpenPype user settings.
└── version.py - Igniter's version number.
```

## OpenPype

This is the main package of the OpenPype logic, it could be loosely described as a combination of [Avalon](https://getavalon.github.io), [Pyblish](https://pyblish.com/) and glue around those with custom OpenPype only elements, things are in progress of being moved around to better prepare for V4, which will be released under a new name AYON.

```
openpype/
├── client - Interface for the MongoDB.
├── hooks - Hooks to be executed on certain OpenPype Applications defined in `openpype.lib.applications`.
├── host - Base class for the different hosts.
├── hosts - Integration with the different DCCs (hosts) using the `host` base class.
├── lib - Libraries that stitch together the package, some have been moved into other parts.
├── modules - OpenPype modules should contain separated logic of specific kind of implementation, such as Ftrack connection and its python API.
├── pipeline - Core of the OpenPype pipeline, handles creation of data, publishing, etc.
├── plugins - Global/core plugins for loader and publisher tool.
├── resources - Icons, fonts, etc.
├── scripts - Loose scipts that get run by tools/publishers.
├── settings - OpenPype settings interface.
├── style - Qt styling.
├── tests - Unit tests.
├── tools - Core tools, check out https://openpype.io/docs/artist_tools.
├── vendor - Vendoring of needed required Python packes.
├── widgets - Common re-usable Qt Widgets.
├── action.py - LEGACY: Lives now in `openpype.pipeline.publish.action` Pyblish actions.
├── cli.py - Command line interface, leverages `click`.
├── __init__.py - Sets two constants.
├── __main__.py - Entry point, calls the `cli.py`
├── plugin.py - Pyblish plugins.
├── pype_commands.py - Implementation of OpenPype commands.
└── version.py - Current version number.
```



