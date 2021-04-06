---
id: artist_hosts_nuke
title: Nuke
sidebar_label: Nuke
---

:::important
After Nuke starts it will automatically **Apply All Settings** for you. If you are sure the settings are wrong just contact your supervisor and he will set them correctly for you in project database.
:::

:::note
The workflows are identical for both. We are supporting versions **`11.0`** and above.
:::

## OpenPype global tools

-   [Set Context](artist_tools.md#set-context)
-   [Work Files](artist_tools.md#workfiles)
-   [Create](artist_tools.md#creator)
-   [Load](artist_tools.md#loader)
-   [Manage (Inventory)](artist_tools.md#inventory)
-   [Publish](artist_tools.md#publisher)
-   [Library Loader](artist_tools.md#library-loader)

## Nuke specific tools

<div class="row markdown">
<div class="col col--6 markdown">

### Set Frame Ranges

Use this feature in case you are not sure the frame range is correct.

##### Result

-   setting Frame Range in script settings
-   setting Frame Range in viewers (timeline)

</div>
<div class="col col--6 markdown">

![Set Frame Ranges](assets/nuke_setFrameRanges.png) <!-- picture needs to be changed -->

</div>
</div>


<figure>

![Set Frame Ranges Timeline](assets/nuke_setFrameRanges_timeline.png)

<figcaption>

1.  limiting to Frame Range without handles
2.  **Input** handle on start
3.  **Output** handle on end

</figcaption>
</figure>

### Set Resolution

<div class="row markdown">
<div class="col col--6 markdown">


This menu item will set correct resolution format for you defined by your production.

##### Result

-   creates new item in formats with project name
-   sets the new format as used

</div>
<div class="col col--6 markdown">

![Set Resolution](assets/nuke_setResolution.png) <!-- picture needs to be changed -->

</div>
</div>


### Set Colorspace

<div class="row markdown">
<div class="col col--6 markdown">

This menu item will set correct Colorspace definitions for you. All has to be configured by your production (Project coordinator).

##### Result

-   set Colorspace in your script settings
-   set preview LUT to your viewers
-   set correct colorspace to all discovered Read nodes (following expression set in settings)

</div>
<div class="col col--6 markdown">

![Set Colorspace](assets/nuke_setColorspace.png) <!-- picture needs to be changed -->

</div>
</div>


### Apply All Settings

<div class="row markdown">
<div class="col col--6 markdown">

It is usually enough if you once per while use this option just to make yourself sure the workfile is having set correct properties.

##### Result

-   set Frame Ranges
-   set Colorspace
-   set Resolution

</div>
<div class="col col--6 markdown">

![Apply All Settings](assets/nuke_applyAllSettings.png) <!-- picture needs to be changed -->

</div>
</div>

### Build Workfile

<div class="row markdown">
<div class="col col--6 markdown">

This tool will append all available subsets into an actual node graph. It will look into database and get all last [versions](artist_concepts.md#version) of available [subsets](artist_concepts.md#subset).


##### Result

-   adds all last versions of subsets (rendered image sequences) as read nodes
-   adds publishable write node as `renderMain` subset

</div>
<div class="col col--6 markdown">

![Build First Work File](assets/nuke_buildFirstWorkfile.png)

</div>
</div>