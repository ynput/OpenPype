---
id: admin_openpype_commands
title: OpenPype Commands Reference
sidebar_label: OpenPype Commands
---


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


## `publish`

Pype takes JSON from provided path and use it to publish data in it.
```sh
pype publish <PATH_TO_JSON>
```

### `--debug`
- print more verbose infomation

--------------------

## `extractenvironments`

Extract environment variables for entered context to a json file.

Entered output filepath will be created if does not exists.

All context options must be passed otherwise only openpype's global environments will be extracted.

Context options are "project", "asset", "task", "app"

### `output_json_path`
- Absolute path to the exported json file

### `--project`
- Project name

### `--asset`
- Asset name

### `--task`
- Task name

### `--app`
- Application name