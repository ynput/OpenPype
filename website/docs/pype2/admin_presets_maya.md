---
id: admin_presets_maya
title: Presets > Maya
sidebar_label: Maya
---

## CAPTURE.json

path: `pype-config/presets/maya/capture.json`

All the viewport settings for maya playblasts.

### `Codec` [dict] ###

```python
  "Codec": {
      "compression": "jpg",
      "format": "image",
      "quality": 95
  }
```


### `Display Options` [dict] ###

```python
"Display Options": {
    "background": [
        0.7137254901960784,
        0.7137254901960784,
        0.7137254901960784
    ],
    "backgroundBottom": [
        0.7137254901960784,
        0.7137254901960784,
        0.7137254901960784
    ],
    "backgroundTop": [
      0.7137254901960784,
      0.7137254901960784,
      0.7137254901960784
    ],
    "override_display": true
  }
```

### `Generic` [dict] ###
```python
"Generic": {
    "isolate_view": true,
    "off_screen": true
},
```

### `IO` [dict] ###

```python
"IO": {
    "name": "",
    "open_finished": false,
    "raw_frame_numbers": false,
    "recent_playblasts": [],
    "save_file": false
},
```

### `PanZoom` [dict] ###

```python
"PanZoom": {
    "pan_zoom": true
},
```

### `Viewport Options` [dict] ###

```python
"Viewport Options": {
    "cameras": false,
    "clipGhosts": false,
    "controlVertices": false,
    "deformers": false,
    "dimensions": false,
    "displayLights": 0,
    "dynamicConstraints": false,
    "dynamics": false,
    "fluids": false,
    "follicles": false,
    "gpuCacheDisplayFilter": false,
    "greasePencils": false,
    "grid": false,
    "hairSystems": false,
    "handles": false,
    "high_quality": true,
    "hud": false,
    "hulls": false,
    "ikHandles": false,
    "imagePlane": false,
    "joints": false,
    "lights": false,
    "locators": false,
    "manipulators": false,
    "motionTrails": false,
    "nCloths": false,
    "nParticles": false,
    "nRigids": false,
    "nurbsCurves": false,
    "nurbsSurfaces": false,
    "override_viewport_options": true,
    "particleInstancers": false,
    "pivots": false,
    "planes": false,
    "pluginShapes": false,
    "polymeshes": true,
    "shadows": false,
    "strokes": false,
    "subdivSurfaces": false,
    "textures": false,
    "twoSidedLighting": true
}
```

## Maya instance scene types

It is possible to set when to use `.ma` or `.mb` for:

- camera
- setdress
- layout
- model
- rig
- yetiRig

Just put `ext_mapping.json` into `presets/maya`. Inside is simple mapping:

```JSON
{
  "rig": "mb",
  "camera": "mb"
}
```

*Note that default type is `ma`*
