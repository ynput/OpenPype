---
id: admin_pype_commands
title: Pype Commands Reference
sidebar_label: Pype Commands
---



## Help

To get all available commands:
```sh
pype --help
```

To get help on particular command:
```sh
pype <command> --help
```

--------------------
## `clean`

Command to clean Python bytecode files from Pype and it's environment. Useful
for developers after code or environment update.

--------------------

## `coverage`

### `--pype`
- without this option, tests are run on *pype-setup* only.

Generate code coverage report.
```sh
pype coverage --pype
```

--------------------

## `deploy`

To deploy Pype:
```sh
pype deploy
```

### `--force`

To force re-deploy:
```sh
pype deploy --force
```

---------------------------

## `download`

To download required dependencies:
```sh
pype download
```

--------------------

## `eventserver`

This command launches ftrack event server.

This should be ideally used by system service (such us systemd or upstart
on linux and window service).

You have to set either proper environment variables to provide URL and
credentials or use option to specify them. If you use `--store_credentials`
provided credentials will be stored for later use.

To run ftrack event server:
```sh
pype eventserver --ftrack-url=<url> --ftrack-user=<user> --ftrack-api-key=<key> --ftrack-events-path=<path> --no-stored-credentials --store-credentials
```

### `--debug`
- print debug info

### `--ftrack-url`
- URL to ftrack server

### `--ftrack-user`
- user name to log in to ftrack

### `--ftrack-api-key`
- ftrack api key

### `--ftrack-events-path`
- path to event server plugins

### `--no-stored-credentials`
- will use credential specified with options above

### `--store-credentials`
- will store credentials to file for later use

--------------------

## `install`

To install Pype:

```sh
pype install
```

### `--force`

To reinstall Pype:
```sh
pype install --force
```

### `--offline`

To install Pype in offline mode:
```sh
pype install --offline
```

To reinstall Pype in offline mode:
```sh
pype install --offline --force
```

--------------------

## `launch`

Launch application in Pype environment.

### `--app`

Application name - this should be the same as it's [defining toml](admin_hosts#launchers) file (without .toml)

### `--project`
Project name

### `--asset`
Asset name

### `--task`
Task name

### `--tools`
*Optional: Additional tools environment files to add*

### `--user`
*Optional: User on behalf to run*

### `--ftrack-server` / `-fs`
*Optional: Ftrack server URL*

### `--ftrack-user` / `-fu`
*Optional: Ftrack user*

### `--ftrack-key` / `-fk`
*Optional: Ftrack API key*

For example to run Python interactive console in Pype context:
```sh
pype launch --app python --project my_project --asset my_asset --task my_task
```

--------------------

## `make_docs`

Generate API documentation into `docs/build`
```sh
pype make_docs
```

--------------------

## `mongodb`

To run testing mongodb database (requires mongoDB installed on the workstation):
```sh
pype mongodb
```

--------------------

## `publish`

Pype takes JSON from provided path and use it to publish data in it.
```sh
pype publish <PATH_TO_JSON>
```

### `--gui`
- run Pyblish GUI

### `--debug`
- print more verbose information

--------------------

## `test`

### `--pype`
- without this option, tests are run on *pype-setup* only.

Run test suite on Pype:
```sh
pype test --pype
```
:::note Pytest
For more information about testing see [Pytest documentation](https://docs.pytest.org/en/latest/)
:::

--------------------

## `texturecopy`

Copy specified textures to provided asset path.

It validates if project and asset exists. Then it will
copy all textures found in all directories under `--path` to destination
folder, determined by template texture in **anatomy**. I will use source
filename and automatically rise version number on directory.

Result will be copied without directory structure so it will be flat then.
Nothing is written to database.

### `--project`

### `--asset`

### `--path`

```sh
pype texturecopy --project <PROJECT_NAME> --asset <ASSET_NAME> --path <PATH_TO_JSON>
```

--------------------

## `tray`

To launch Tray:
```sh
pype tray
```

### `--debug`

To launch Tray with debugging information:
```sh
pype tray --debug
```

--------------------

## `update-requirements`

Synchronize dependencies in your virtual environment with requirement.txt file.
Equivalent of running `pip freeze > pypeapp/requirements.txt` from your virtual
environment. This is useful for development purposes.

```sh
pype update-requirements
```

--------------------

## `validate`

To validate deployment:
```sh
pype validate
```

--------------------

## `validate-config`

To validate JSON configuration files for syntax errors:
```sh
pype validate-config
```
