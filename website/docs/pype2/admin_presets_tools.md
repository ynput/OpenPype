---
id: admin_presets_tools
title: Presets > Tools
sidebar_label: Tools
---

## Colorspace

We provide two examples of possible settings for nuke, but these can vary wildly between clients and projects.

### `Default` [dict]

path: `pype-config/presets/colorspace/default.json`

```python
"nuke": {
    "root": {
        "colorManagement": "Nuke",
        "OCIO_config": "nuke-default",
        "defaultViewerLUT": "Nuke Root LUTs",
        "monitorLut": "sRGB",
        "int8Lut": "sRGB",
        "int16Lut": "sRGB",
        "logLut": "Cineon",
        "floatLut": "linear"
    },
    "viewer": {
        "viewerProcess": "sRGB"
    },
    "write": {
        "render": {
            "colorspace": "linear"
        },
        "prerender": {
            "colorspace": "linear"
        },
        "still": {
            "colorspace": "sRGB"
        }
    }
},
```

### `aces103-cg` [dict]


path: `pype-config/presets/colorspace/aces103-cg.json`

```python
"nuke": {
  "root": {
    "colorManagement": "OCIO",
    "OCIO_config": "aces_1.0.3",
    "workingSpaceLUT": "ACES - ACEScg",
    "defaultViewerLUT": "OCIO LUTs",
    "monitorLut": "ACES/sRGB D60 sim.",
    "int8Lut": "Utility - sRGB - Texture",
    "int16Lut": "Utility - sRGB - Texture",
    "logLut": "Input - ARRI - V3 LogC (EI800) - Wide Gamut",
    "floatLut": "ACES - ACES2065-1"
  },
  "viewer": {
    "viewerProcess": "sRGB D60 sim. (ACES)"
  },
  "write": {
    "render": {
      "colorspace": "ACES - ACEScg"
    },
    "prerender": {
      "colorspace": "ACES - ACEScg"
    },
    "still": {
      "colorspace": "Utility - Curve - sRGB"
    }
  }
},
```


## Creator Defaults

path: `pype-config/presets/tools/creator.json`

This preset tells the creator tools what family should be pre-selected in different tasks. Keep in mind that the task is matched loosely so for example any task with 'model' in it's name will be considered a modelling task for these purposes.

`"Family name": ["list, "of, "tasks"]`

```python
"Model": ["model"],
"Render Globals": ["light", "render"],
"Layout": ["layout"],
"Set Dress": ["setdress"],
"Look": ["look"],
"Rig": ["rigging"]
```

## Project Folder Structure

path: `pype-config/presets/tools/project_folder_structure.json`

Defines the base folder structure for a project. This is supposed to act as a starting point to quickly create the base of the project. You can add `[ftrack.entityType]` after any of the folders here and they will automatically be also created in ftrack project.

### `__project_root__` [dict]

```python
"__project_root__": {
    "_prod" : {},
    "_resources" : {
      "footage": {
        "ingest": {},
        "offline": {}
      },
      "audio": {},
      "art_dept": {},
    },
    "editorial" : {},
    "assets[ftrack.Library]": {
      "characters[ftrack]": {},
      "locations[ftrack]": {}
    },
    "shots[ftrack.Sequence]": {
      "editorial[ftrack.Folder]": {}
    }
}
```

## Software Folders

path: `pype-config/presets/tools/sw_folders.json`

Defines extra folders to be created inside the work space when particular task type is launched. Mostly used for configs, that use {app} key in their work template and want to add hosts that are not supported yet.

```python
"compositing": ["nuke", "ae"],
"modeling": ["maya", "app2"],
"lookdev": ["substance"],
"animation": [],
"lighting": [],
"rigging": []
```

## Tray Items

path: `pype-config/presets/tray/menu_items.json`

This preset let's admins to turn different pype modules on and off from the tray menu, which in turn makes them unavailable across the pipeline

### `item_usage` [dict]

```python
"item_usage": {
    "User settings": false,
    "Ftrack": true,
    "Muster": false,
    "Avalon": true,
    "Clockify": false,
    "Standalone Publish": true,
    "Logging": true,
    "Idle Manager": true,
    "Timers Manager": true,
    "Rest Api": true
},
```

## Muster Templates

path: `pype-config/presets/muster/templates_mapping.json`

Muster template mapping maps Muster template ID to name of renderer. Initially it is set Muster defaults. About templates and Muster se Muster Documentation. Mapping is defined in:

Keys are renderer names and values are templates IDs.

```python
"3delight": 41,
"arnold": 46,
"arnold_sf": 57,
"gelato": 30,
"hardware": 3,
"krakatoa": 51,
"file_layers": 7,
"mentalray": 2,
"mentalray_sf": 6,
"redshift": 55,
"renderman": 29,
"software": 1,
"software_sf": 5,
"turtle": 10,
"vector": 4,
"vray": 37,
"ffmpeg": 48
```
