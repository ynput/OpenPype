---
id: artist_tools_inventory
title: Inventory
sidebar_label: Inventory
description: Manage already loaded subsets.
---

# Inventory

With Scene Inventory, you can browse, update and change subsets loaded with [Loader](artist_tools_loader) into your scene or script.

:::note
You should first understand [Key concepts](artist_concepts) to understand how you can use this tool.
:::

## Details
<!-- This part may be in Maya description? -->

Once a subset is loaded, it turns into a container within a scene. This containerization allows us to have a good overview of everything in the scene, but also makes it possible to change versions, notify user if something is outdated, replace one asset for another, etc.
<!-- END HERE -->

The scene manager has a simple GUI focused on efficiency. You can see everything that has been previously loaded into the scene, how many time it's been loaded, what version and a lot of other information. Loaded assets are grouped by their asset name, subset name and representation. This grouping gives ability to apply changes for all instances of the loaded asset *(e.g. when __tree__ is loaded 20 times you can easily update version for all of them)*.

![tools_scene_inventory_10](assets/tools/tools_scene_inventory_10-small.png) <!-- picture needs to be changed -->

To interact with any container, you need to right click it and you'll see a drop down with possible actions. The key actions for production are already implemented, but more will be added over time.

![tools_scene_inventory_20](assets/tools/tools_scene_inventory_20.png)

## Usage

### Change version
You can change versions of loaded subsets with scene inventory tool. Version of loaded assets is colored to red when newer version is available.


![tools_scene_inventory_40](assets/tools/tools_scene_inventory_40.png)

#### Update to the latest version
Select containers or subsets you want to update, right-click selection and press `Update to latest`.

#### Change to specific version
Select containers or subsets you want to change, right-click selection, press `Set version`, select from dropdown version you want change to and press `OK` button to confirm.


![tools_scene_inventory_30](assets/tools/tools_scene_inventory_30.png)


### Switch Asset
It's tool in Scene inventory tool that gives ability to switch asset, subset and representation of loaded assets.


![tools_scene_inventory_50](assets/tools/tools_scene_inventory_50.png) <!-- picture needs to be changed -->


Because loaded asset is in fact representation of version published in asset's subset it is possible to switch each of this part *(representation, version, subset and asset)*, but with limitations. Limitations are obvious as you can imagine when you have loaded `.ma` representation of `modelMain` subset from `car` asset it is not possible to switch subset to `modelHD` and keep same representation if `modelHD` does not have published `.ma` representation. It is possible to switch multiple loaded assets at once that makes this tool very powerful helper if all published assets contain same subsets and representations.

Switch tool won't let you cross the border of limitations and inform you when you have to specify more if impossible combination occurs *(It is also possible that there will be no possible combination for selected assets)*. Border is colored to red and confirm button is not enabled when specification is required.


![tools_scene_inventory_55](assets/tools/tools_scene_inventory_55.png) <!-- picture needs to be changed -->


Possible switches:
- switch **representation** (`.ma` to `.abc`, `.exr` to `.dpx`, etc.)
- switch **subset** (`modelMain` to `modelHD`, etc.)
    - `AND` keep same **representation** *(with limitations)*
    - `AND` switch **representation** *(with limitations)*
- switch **asset** (`oak` to `elm`, etc.)
    - `AND` keep same **subset** and **representation** *(with limitations)*
    - `AND` keep same **subset** and switch **representation** *(with limitations)*
    - `AND` switch **subset** and keep same **representation** *(with limitations)*
    - `AND` switch **subset** and **representation** *(with limitations)*

We added one more switch layer above subset for LOD (Level Of Depth). That requires to have published subsets with name ending with **"_LOD{number}"** where number represents level (e.g. modelMain_LOD1). Has the same limitations as mentioned above. This is handy when you want to change only subset but keep same LOD or keep same subset but change LOD for multiple assets. This option is hidden if you didn't select subset that have published subset with LODs.

![tools_scene_inventory_54](assets/tools/tools_scene_inventory_54.png) <!-- picture needs to be changed -->
  
## Filtering

### Filter by name

There is a search bar on the top for cases when you have a complex scene with many assets and need to find a specific one.

<div class="row markdown">
<div class="col col--6 markdown">

![tools_scene_inventory_60](assets/tools/tools_scene_inventory_60-small.png)

</div>
<div class="col col--6 markdown">

![tools_scene_inventory_61](assets/tools/tools_scene_inventory_61-small.png)

</div>
</div>


### Filter with Cherry-pick selection

<div class="row markdown">
<div class="col col--6 markdown">

To keep only selected subsets right-click selection and press `Cherry-Pick (Hierarchy)` *(Border of subset list change to **orange** color when Cherry-pick filtering is set so you know filter is applied).*

</div>
<div class="col col--6 markdown">

![tools_scene_inventory_62-small](assets/tools/tools_scene_inventory_62-small.png)

</div>
</div>

<div class="row markdown">
<div class="col col--6 markdown">

To return to original state right-click anywhere in subsets list and press `Back to Full-View`.

</div>
<div class="col col--6 markdown">

![tools_scene_inventory_63-small](assets/tools/tools_scene_inventory_63-small.png)

</div>
</div>


:::tip
You can Cherry-pick from Cherry-picked subsets.
:::
