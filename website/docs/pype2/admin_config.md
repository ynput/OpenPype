---
id: admin_config
title: Studio Config
sidebar_label: Studio Config
---

All of the studio specific configurations are stored as simple JSON files in the **pype-config** repository.

Config is split into multiple sections described below.

## Anatomy

Defines where and how folders and files are created for all the project data. Anatomy has two parts **Roots** and **Templates**.

:::warning
It is recommended to create anatomy [overrides](#per-project-configuration) for each project even if values haven't changed. Ignoring this recommendation may cause catastrophic consequences.
:::

### Roots
Roots define where files are stored with path to shared folder. You can set them in `roots.json`.
It is required to set root path for each platform you are using in studio. All paths must point to same folder!
```json
{
    "windows": "P:/projects",
    "darwin": "/Volumes/projects",
    "linux": "/mnt/share/projects"
}
```

It is possible to set multiple roots when necessary. That may be handy when you need to store specific type of data on another disk. In that case you'll have to add one level in json.
```json
{
    "work": {
        "windows": "P:/work",
        "darwin": "/Volumes/work",
        "linux": "/mnt/share/work"
    },
    "publish": {
        "windows": "Y:/publish",
        "darwin": "/Volumes/publish",
        "linux": "/mnt/share/publish"
    }
}
```
Usage of multiple roots is explained below in templates part.

### Templates
Templates define project's folder structure and filenames. You can set them in `default.yaml`.

### Required templates
We have a few required anatomy templates for Pype to work properly, however we keep adding more when needed.

```yaml
work:
  folder: "{root}/{project[name]}/{hierarchy}/{asset}/work/{task}"
  file: "{project[code]}_{asset}_{task}_v{version:0>3}<_{comment}>.{ext}"
  path: "{root}/{project[name]}/{hierarchy}/{asset}/work/{task}/{project[code]}_{asset}_{task}_v{version:0>3}<_{comment}>.{ext}"

publish:
  folder: "{root}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/v{version:0>3}"
  file: "{project[code]}_{asset}_{subset}_v{version:0>3}<.{frame}>.{representation}"
  path: "{root}/{project[name]}/{hierarchy}/{asset}/publish/{family}/{subset}/v{version:0>3}/{project[code]}_{asset}_{subset}_v{version:0>3}<.{frame}>.{representation}"
```

Template groups `work` and `publish` must be set in all circumstances. Both must have set keys as shown `folder`, holds path template for the directory where the files are stored, `file` only holds the filename and `path` combines the two together for quicker access.

### Available keys
| Context key | Description |
| --- | --- |
| root | Path to root folder |
| root[\<root name\>] | Path to root folder when multiple roots are used.<br />Key `<root name>` represents root key specified in `roots.json` |
| project[name] | Project's full name. |
| project[code] | Project's code. |
| hierarchy | All hierarchical parents as subfolders. |
| asset | Name of asset or shot. |
| task | Name of task. |
| version | Version number. |
| subset | Subset name. |
| family | Main family name. |
| ext | File extension. (Possible to use only in `work` template atm.) |
| representation | Representation name. (Is used instead of `ext` except `work` template atm.) |
| frame | Frame number for sequence files. |
| output |  |
| comment |  |

:::warning
Be careful about using `root` key in templates when using multiple roots. It is not allowed to combine both `{root}` and `{root[<root name>]}` in templates.
:::
:::note
It is recommended to set padding for `version` which is possible with additional expression in template. Entered key `{version:0<3}` will result into `001` if version `1` is published.
**Explanation:** Expression `0<3` will add `"0"` char to the beginning(`<`) until string has `3` characters.
:::

| Date-Time key | Example result | Description |
| --- | --- | --- |
| d | 1, 30 | Day of month in shortest possible way. |
| dd | 01, 30 | Day of month with 2 digits. |
| ddd | Mon | Shortened week day name. |
| dddd | Monday | Full week day name. |
| m | 1, 12 | Month number in shortest possible way. |
| mm | 01, 12 | Month number with 2 digits. |
| mmm | Jan | Shortened month name. |
| mmmm | January | Full month name. |
| yy | 20 | Shortened year. |
| yyyy | 2020 | Full year. |
| H | 4, 17 | Shortened 24-hour number. |
| HH | 04, 17 | 24-hour number with 2 digits. |
| h | 5 | Shortened 12-hour number. |
| hh | 05 | 12-hour number with 2 digits. |
| ht | AM, PM | Midday part. |
| M | 0 | Shortened minutes number. |
| MM | 00 | Minutes number with 2 digits. |
| S | 0 | Shortened seconds number. |
| SS | 00 | Seconds number with 2 digits. |

### Optional keys
Keys may be optional for some reason when are wrapped with `<` and `>`. But it is recommended to use only for these specific keys with obvious reasons:
- `output`, `comment` are optional to fill
- `frame` is used only for sequences.

### Inner keys
It is possible to use value of one template key inside value of another template key. This can be done only per template group, which means it is not possible to use template key from `publish` group inside `work` group.

Usage is similar to using template keys but instead of `{key}` you must add `@` in front of key: `{@key}`

With this feature `work` template from example above may be much easier to read and modify.
```yaml
work:
  folder: "{root}/{project[name]}/{hierarchy}/{asset}/work/{task}"
  file: "{project[code]}_{asset}_{task}_v{version:0>3}<_{comment}>.{ext}"
  path: "{@folder}/{@file}"
  # This is how `path` key will look as result
  # path: "{root}/{project[name]}/{hierarchy}/{asset}/work/{task}/{project[code]}_{asset}_{task}_v{version:0>3}<_{comment}>.{ext}"
```

:::warning
Be aware of unsolvable recursion in inner keys.
```yaml
group:
  # Use key where source key is used in value
  key_1: "{@key_2}"
  key_2: "{@key_1}"

  # Use itself
  key_3: "{@key_3}"
```
:::

### Global keys
Global keys are keys with value outside template groups. All these keys will be available in each template group with ability to override them inside the group.

**Source**
```yaml
# Global key outside template group
global_key: "global value"

group_1:
  # `global_key` is not set
  example_key_1: "{example_value_1}"

group_2:
  # `global_key` is iverrided
  global_key: "overridden global value"
```
**Result**
```yaml
global_key: "global value"

group_1:
  # `global_key` was added
  global_key: "global value"
  example_key_1: "{example_value_1}"

group_2:
  # `global_key` kept it's value for `group_2`
  global_key: "overridden global value"
```

### Combine Inner keys with Global keys
Real power of [Inner](#inner-keys) and [Global](#global-keys) keys is their combination.

**Template source**
```yaml
# PADDING
frame_padding: 4
frame: "{frame:0>frame_padding}"
# MULTIPLE ROOT
root_name: "root_name_1"
root: {root[{@root_name}]}

group_1:
  example_key_1: "{@root}/{@frame}"

group_2:
  frame_padding: 3
  root_name: "root_name_2"
  example_key_2: "{@root}/{@frame}"

group_3:
  frame: "{frame}"
  example_key_3: "{@root}/force_value/{@frame}"
```
**Equals**
```yaml
frame_padding: 4
frame: "{frame:0>3}"
root_name: "root_name_1"
root: {root[root_name_1]}

group_1:
  frame_padding: 4
  frame: "{frame:0>3}"
  root_name: "root_name_1"
  root: {root[root_name_1]}
  # `example_key_1` result
  example_key_1: "{root[root_name_1]}/{frame:0>3}"

group_2:
  frame_padding: 3
  frame: "{frame:0>3}"
  root_name: "root_name_2"
  root: {root[root_name_2]}
  # `example_key_2` result
  example_key_2: "{root[root_name_2]}/{frame:0>2}"

group_3:
  frame_padding: 4
  frame: "{frame}"
  root_name: "root_name_1"
  root: {root[root_name_1]}
  # `example_key_3` result
  example_key_3: "{root[root_name_1]}/force_value/{frame}"
```

:::warning
Be careful about using global keys. Keep in mind that **all global keys** will be added to **all template groups** and all inner keys in their values **MUST** be in the group.
For example in [required templates](#required-templates) it seems that `path: "{@folder}/{@file}"` should be used as global key, but that would require all template groups have `folder` and `file` keys which is not true by default.
:::

## Environments

Here is where all the environment variables are set up. Each software has it's own environment file where we set all variables needed for it to function correctly. This is also a place where any extra in-house variables should be added. All of these individual configs and then loaded additively as needed based on current context.

For example when launching Pype Tray, **Global** and **Avalon** envs are loaded first. If the studio uses also *Deadline* and *Ftrack*, both of those environments get added at the same time. This sets the base environment for the rest of the pipeline that will be inherited by all the applications launched from this point on.

When user launches an application for a task, its general and versioned env files get added to the base before the software launches. When launching *Maya 2019*, both `maya.json` and `maya_2019.json` will be added.

If the project or task also has extra tools configured, say *Arnold Mtoa 3.1.1*, a config JSON with the same name will be added too.

This way the environment is completely dynamic with possibility of overrides on a granular level, from project all the way down to task.

## Launchers

Considering that different studios use different ways of deploying software to their workstations, we need to tell Pype how to launch all the individual applications available in the studio.

Each software need multiple files prepared for it to function correctly.

```text
application_name.toml
application_name.bat
application_name.sh
```

TOML file tells Pype how to work with the application across the board. Icons, Label in GUI, *Ftrack* settings but most importantly it defines what executable to run. These executable are stored in the windows and linux subfolder in the launchers folder. If `application_name.toml` defines that executable to run is `application_name`, Pype assumes that a `.bat` and `.sh` files under that name exist in the linux and windows folders in launchers. Correct version is picked automatically based on the platform Pype is running on.

These `.bat` and `.sh` scripts have only one job then. They have to point to the exact executable path on the system, or to a command that will launch the app we want. Version granularity is up to the studio to decide. We can show artists Nuke 11.3, while specifying the particular version 11.3v4 only in the .bat file, so the artist doesn't need to deal with it, or we can present him with 11.3v4 directly. the choice is mostly between artist control vs more configuration files on the system.

## Presets

This is where most of the functions configuration of the pipeline happens. Colorspace, data types, burnin setting, geometry naming conventions, ftrack attributes, playblast settings, types of exports and lot's of other settings.

Presets are categorized in folders based on what they control or what host (DCC application) they are for. We're slowly working on documenting them all, but new ones are being created regularly as well. Hopefully the categories and names are sufficiently self-explanatory.

### colorspace

Defines all available color spaces in the studio. These configs not only tell the system what OCIO to use, but also how exactly it needs to be applied in the give application. From loading the data, through previewing it all the way to rendered

### Dataflow

Defines allowed file types and data formats across the pipeline including their particular coded and compression settings.

### Plugins

All the creator, loader and publisher configurations are stored here. We can override any properties of the default plugin values and more.

#### How does it work

Overriding plugin properties is as simple as adding what needs to be changed to
JSON file along with plugin name.

Say you have name validating plugin:

```python
import pyblish.api


class ValidateModelName(pyblish.api.InstancePlugin):

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['model']
    label = 'Validate Mesh Name'

    # check for: 'foo_001_bar_GEO`
    regex = r'.*_\d*_.*_GEO'

    def process(self, instance):
      # pseudocode to get nodes
      models = get_models(instance.data.get("setMembers", None))
      r = re.compile(self.regex)
      for model in models:
            m = r.match(obj)
            if m is None:
              raise RuntimeError("invalid name on {}".format(model))

```
_This is just non-functional example_

Instead of creating new plugin with different regex, you can put:

```javascript
"ValidateModelName": {
  "regex": ".*\\d*_.*_geometry"
}
```
and put it into `repos/pype-config/presets/plugins/maya/publish.json`. There can be more entries
like that for how many plugins you need.

That will effectively replace regex defined in plugin during runtime with the one you've just
defined in JSON file. This way you can change any properties defined in plugin.

:::tip loader and creators
Similar way exist for *Loaders* and *Creators*. Use files `create.json` for Creators, `load.json`
for Loaders and `publish.json` for **Pyblish** plugins like extractors, validators, etc.

Preset resolution works by getting host name (for example *Maya*) and then looking inside
 `repos/pype-config/presets/plugins/<host>/publish.json` path. If plugin is not found, then
 `repos/pype-config/presets/plugins/global/publish.json` is tried.
:::

:::tip Per project plugin override
You can override plugins per project. See [Per-project configuration](#per-project-configuration)
:::


## Schema

Holds all database schemas for *mongoDB*, that we use. In practice these are never changed on a per studio basis, however we included them in the config for cases where a particular project might need a very individual treatment.

## Per-project configuration

You can have per-project configuration with Pype. This allows you to have for example different
validation requirements, file naming, etc.

This is very easy to set up - point `PYPE_PROJECT_CONFIGS` environment variable to place
where you want those per-project configurations. Then just create directory with project name and
that's almost it. Inside, you can follow hierarchy of **pype-config** presets. Everything put there
will override stuff in **pype-config**.

### Example

You have a project where you need to disable some validators - let's say overlapping
UVs validator in Maya.

Project name is *FooProject*.
Your `PYPE_PROJECT_CONFIGS` points to `/studio/pype/projects`.

Create projects settings directory:
```sh
mkdir $PYPE_PROJECT_CONFIGS/FooProject
```
Now you can use plugin overrides to disable validator:

Put:
```javascript
{
  "ValidateMeshHasOverlappingUVs": {
    "enabled": false
  }
}
```
into:

```sh
$PYPE_PROJECT_CONFIGS/FooPoject/presets/plugins/maya/publish.json
```

And its done. **ValidateMeshHasOverlappingUVs** is a class name of validator - you can
find that name by looking into python file containing validator code, or in Pyblish GUI.

That way you can make it optional or set whatever properties you want on plugins and those
settings will take precedence over the default site-wide settings.
