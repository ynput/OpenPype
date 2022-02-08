---
id: admin_presets_nukestudio
title: Presets > NukeStudio
sidebar_label: Nukestudio
---

## TAGS.json

path: `pype-config/presets/nukestudio/tags.json`

Each tag defines defaults in `.json` file. Inside of the file you can change the default values as shown in the example (`>>>"1001"<<<`). Please be careful not to alter the `family` value.

```python
"Frame start": {
    "editable": "1",
    "note": "Starting frame for comps",
    "icon": {
        "path": "icons:TagBackground.png"
    },
    "metadata": {
        "family": "frameStart",
        "number": >>>"1001"<<<
    }
}
```

## PUBLISH.json

path: `pype-config/presets/plugins/nukestudio/publish.json`

### `CollectInstanceVersion` [dict] ###


This plugin is set to `true` by default so it will synchronize version of published instances with the version of the workfile. Set `enabled` to `false` if you wish to let publishing process decide on the next available version.

```python
{
    "CollectInstanceVersion": {
        "enabled": false
    }
}
```

### `ExtractReviewCutUpVideo` [dict] ###

path: `pype-config/presets/plugins/nukestudio/publish.json`

Plugin is responsible for cuting shorter or longer source material for review. Here you can add any additional tags you wish to be added into extract review process.

The plugin generates reedited intermediate video with handless even if it has to add empty black frames. Some productions prefer to use review material without handless so in the example, `no-handles` are added as tags. This allow further review extractor to publish review without handles, without affecting other outputs.

```python
{
    "ExtractReviewCutUpVideo": {
        "tags_addition": ["no-handles"]
      }
}
```
