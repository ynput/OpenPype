---
id: artist_hosts_maya_xgen
title: Xgen for Maya
sidebar_label: Xgen
---

OpenPype supports Xgen classic with the follow workflow. It eases the otherwise cumbersome issues around Xgen's side car files and hidden behaviour inside Maya. The workflow supports publishing, loading and updating of Xgen collections, along with connecting animation from geometry and (guide) curves.

## Setup

### Settings

Go to project settings > `Maya` > enable `Open Workfile Post Initialization`;

`project_settings/maya/open_workfile_post_initialization`

This is due to two errors occurring when opening workfile containing referenced xgen nodes on launch of Maya, specifically:

- ``Critical``: Duplicate collection errors on launching workfile. This is because Maya first imports Xgen when referencing in external Maya files, then imports Xgen again when the reference edits are applied.
```
Importing XGen Collections...
# Error: XGen:  Failed to find description ball_xgenMain_01_:parent in collection ball_xgenMain_01_:collection. Abort applying delta: P:/PROJECTS/OP01_CG_demo/shots/sh040/work/Lighting/cg_sh040_Lighting_v001__ball_xgenMain_01___collection.xgen  #
# Error: XGen:  Tried to import a duplicate collection, ball_xgenMain_02_:collection, from file P:/PROJECTS/OP01_CG_demo/shots/sh040/work/Lighting/cg_sh040_Lighting_v001__ball_xgenMain_02___collection.xgen. Aborting import.  #
```
- ``Non-critical``: Errors on opening workfile and failed opening of published xgen. This is because Maya imports Xgen when referencing in external Maya files but the reference edits that ensure the location of the Xgen files are correct, has not been applied yet.
```
Importing XGen Collections...
# Error: XGen:  Failed to open file: P:/PROJECTS/OP01_CG_demo/shots/sh040/work/Lighting/cg_ball_xgenMain_v035__ball_rigMain_01___collection.xgen  #
# Error: XGen:  Failed to import collection from file P:/PROJECTS/OP01_CG_demo/shots/sh040/work/Lighting/cg_ball_xgenMain_v035__ball_rigMain_01___collection.xgen  #
```

Go to project settings > `Deadline` > `Publish plugins` > `Maya Submit to Deadline` > disable `Use Published scene`;

`project_settings/deadline/publish/MayaSubmitDeadline/use_published`

This is due to temporary workaround while fixing rendering with published scenes.

## Create

Create an Xgen instance to publish. This needs to contain only **one Xgen collection**.

`OpenPype > Create... > Xgen`

You can create multiple Xgen instances if you have multiple collections to publish.

:::note
The Xgen publishing requires a namespace on the Xgen collection (palette) and the geometry used.
:::

### Publish

The publishing process will grab geometry used for Xgen along with any external files used in the collection's descriptions. This creates an isolated Maya file with just the Xgen collection's dependencies, so you can use any nested geometry when creating the Xgen description. An Xgen version will consist of:

- Maya file (`.ma`) - this contains the geometry and the connections to the Xgen collection and descriptions.
- Xgen file (`.xgen`) - this contains the Xgen collection and description.
- Resource files (`.ptx`, `.xuv`) - this contains Xgen side car files used in the collection and descriptions.

## Load

Open the Loader tool, `OpenPype > Loader...`, and navigate to the published Xgen version. On right-click you'll get the option `Reference Xgen (ma)`
When loading an Xgen version the following happens:

- References in the Maya file.
- Copies the Xgen file (`.xgen`) to the current workspace.
- Modifies the Xgen file copy to load the current workspace first then the published Xgen collection.
- Makes a custom attribute on the Xgen collection, `float_ignore`, which can be seen under the `Expressions` tab of the `Xgen` UI. This is done to initialize the Xgen delta file workflow.
- Setup an Xgen delta file (`.xgd`) to store any workspace changes of the published Xgen version.

When the loading is done, Xgen collection will be in the Xgen delta file workflow which means any changes done in the Maya workfile will be stored in the current workspace. The published Xgen collection will remain intact, even if the user assigns maps to any attributes or otherwise modifies any attribute.

### Updating

When there are changes to the Xgen version, the user will be notified when opening the workfile or publishing. Since the Xgen is referenced, it follows the standard Maya referencing system and overrides.

For example publishing `xgenMain` version 1 with the attribute `renderer` set to `None`, then version 2 has `renderer` set to `Arnold Renderer`. When updating from version 1 to 2, the `renderer` attribute will be updated to `Arnold Renderer` unless there is a local override.

### Connect Patches

When loading in an Xgen version, it does not have any connections to anything in the workfile, so its static in the position it was published in. Use the [Connect Geometry](artist_hosts_maya#connect-geometry) action to connect Xgen to any matching loaded animated geometry.

### Connect Guides

Along with patches you can also connect the Xgen guides to an Alembic cache.

#### Usage

Select 1 animation container, of family `animation` or `pointcache`, then the Xgen containers to connect to. Right-click > `Actions` > `Connect Xgen`.

***Note: Only alembic (`.abc`) representations are allowed.***

#### Details

Connecting the guide will make Xgen use the Alembic directly, setting the attributes under `Guide Animation`, so the Alembic needs to contain the same amount of curves as guides in the Xgen.

The animation container gets connected with the Xgen container, so if the animation container is updated so will the Xgen container's attribute.

## Rendering

To render with Xgen, follow the [Rendering With OpenPype](artist_hosts_maya#rendering-with-openpype) guide.

### Details

When submitting a workfile with Xgen, all Xgen related files will be collected and published as the workfiles resources. This means the published workfile is no longer referencing the workspace Xgen files.
