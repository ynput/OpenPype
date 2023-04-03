---
id: artist_tools_loader
title: Loader
sidebar_label: Loader
description: Allows loading published subsets from the same project.
---

# Loader
Loader loads published subsets into your current scene or script.

## Usage
1. Open *Loader* from OpenPype menu.
2. Select the asset where the subset you want to load is published.
3. From subset list select the subset you want.
4. Right-click the subset.
5. From action menu select what you want to do *(load, reference, ...)*.


![tools_loader_1](assets/tools/tools_loader_1.png) <!-- picture needs to be changed -->

<div class="row markdown">
<div class="col col--6 markdown">

## Refresh data
Data are not auto-refreshed to avoid database issues. To refresh assets or subsets press refresh button.

</div>
<div class="col col--6 markdown">

![tools_loader_50](assets/tools/tools_loader_50.png)

</div>
</div>

## Load another version
Loader by default load last version, but you can of course load another versions. Double-click on the subset in the version column to expose the drop down, choose version you want to load and continue from point 4 of the [Usage](#usage-1).

<div class="row markdown">
<div class="col col--6 markdown">

  ![tools_loader_21](assets/tools/tools_loader_21.png)
</div>
<div class="col col--6 markdown">

  ![tools_loader_22](assets/tools/tools_loader_22.png)
</div>
</div>


## Filtering

### Filter Assets and Subsets by name
To filter assets/subsets by name just type name or part of name to filter text input. Only assets/subsets containing the entered string remain.

- **Assets filtering example** *(it works the same for subsets)*:

<div class="row markdown">
<div class="col col--6 markdown">

![tools_loader_4](assets/tools/tools_loader_4-small.png)

</div>
<div class="col col--6 markdown">

![tools_loader_5](assets/tools/tools_loader_5-small.png)

</div>
</div>


### Filter Subsets by Family

<div class="row markdown">
<div class="col col--6 markdown">

To filter [subsets](artist_concepts.md#subset) by their [families](artist_publish.md#families) you can use families list where you can check families you want to see or uncheck families you are not interested in.

</div>
<div class="col col--6 markdown">

![tools_loader_30](assets/tools/tools_loader_30-small.png)

</div>
</div>



## Subset groups
Subsets may be grouped which can help to make the subset list more transparent. You can toggle visibility of groups with `Enable Grouping` checkbox.

![tools_loader_40](assets/tools/tools_loader_40-small.png)


### Add to group or change current group
You can set group of selected subsets with shortcut `Ctrl + G`.

![tools_loader_41](assets/tools/tools_loader_41-small.png)


:::warning
You'll set the group in Avalon database so your changes will take effect for all users.
:::

## Site Sync support

If **Site Sync** is enabled additional widget is shown in right bottom corner.
It contains list of all representations of selected version(s). It also shows availability of representation files
on particular site (*active* - mine, *remote* - theirs). 

![site_sync_support](assets/site_sync_loader.png)

On this picture you see that representation files are available only on remote site (could be GDrive or other). 
If artist wants to work with the file(s) they need to be downloaded first. That could be done by right mouse click on
particular representation (or multiselect all) and select *Download*.

This will mark representation to be download which will happen in the background if OpenPype Tray is running.

For more details of progress, state or possible error details artist should open **[Sync Queue](#Sync-Queue)** item in Tray app.

Work in progress...

