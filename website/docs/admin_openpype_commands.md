---
id: admin_openpype_commands
title: OpenPype Commands Reference
sidebar_label: OpenPype Commands
---

:::info
You can substitute `openpype_console` with `poetry run python start.py` if you want to run it
directly from sources.
:::

:::note
Running OpenPype without any commands will default to `tray`.
:::

## Common arguments
`--use-version` to specify explicit version to use:
```shell
openpype_console --use-version=3.0.0-foo+bar
```
`--headless` - to run OpenPype in headless mode (without using graphical UI)

`--use-staging` - to use staging versions of OpenPype.

`--list-versions` - to list available versions.

`--validate-version` - to validate integrity of given version

`--verbose` `<level>` - change log verbose level of OpenPype loggers

`--debug` - set debug flag affects logging

For more information [see here](admin_use.md#run-openpype).

## Commands

| Command | Description | Arguments |
| --- | --- |: --- :|
| contextselection | Open Context selection dialog. |  |
| module | Run command line arguments for modules. |  |
| repack-version | Tool to re-create version zip. | [📑](#repack-version-arguments) |
| tray | Launch OpenPype Tray. | [📑](#tray-arguments)
| publish | Pype takes JSON from provided path and use it to publish data in it. | [📑](#publish-arguments) |
| extractenvironments | Extract environment variables for entered context to a json file. | [📑](#extractenvironments-arguments) |
| run | Execute given python script within OpenPype environment. | [📑](#run-arguments) |
| interactive | Start python like interactive console session. | |
| projectmanager | Launch Project Manager UI | [📑](#projectmanager-arguments) |
| settings | Open Settings UI | [📑](#settings-arguments) |

---
### `tray` arguments {#tray-arguments}

```shell
openpype_console tray
```

---
### `publish` arguments {#publish-arguments}

Run publishing based on metadata passed in json file e.g. on farm.

| Argument | Description |
| --- | --- |
| `--targets` | define publishing targets (e.g. "farm") |
| `--gui` (`-g`) | Show publishing |
| Positional argument | Path to metadata json file |

```shell
openpype publish <PATH_TO_JSON> --targes farm
```

---
### `extractenvironments` arguments {#extractenvironments-arguments}

Entered output filepath will be created if does not exists.
All context options must be passed otherwise only openpype's global environments will be extracted.
Context options are `project`, `asset`, `task`, `app`

| Argument | Description |
| --- | --- |
| `output_json_path` | Absolute path to the exported json file |
| `--project` | Project name |
| `--asset` | Asset name |
| `--task` | Task name |
| `--app` | Application name |

```shell
openpype_console /home/openpype/env.json --project Foo --asset Bar --task modeling --app maya-2019
```

---
### `run` arguments {#run-arguments}

| Argument | Description |
| `--script` | run specified python script |

Note that additional arguments are passed to the script.

```shell
openpype_console run --script /foo/bar/baz.py arg1 arg2
```

---
### `projectmanager` arguments {#projectmanager-arguments}
`projectmanager` has no command-line arguments.
```shell
openpype_console projectmanager
```

---
### `settings` arguments {#settings-arguments}

| Argument | Description |
| `-d` / `--dev` | Run settings in developer mode. |

```shell
openpypeconsole settings
```

---
### `repack-version` arguments {#repack-version-arguments}
Takes path to unzipped and possibly modified OpenPype version. Files will be
zipped, checksums recalculated and version will be determined by folder name
(and written to `version.py`).

```shell
./openpype_console repack-version /path/to/some/modified/unzipped/version/openpype-v3.8.3-modified
```
