---
id: artist_tools_library_loader
title: Library Loader
sidebar_label: Library Loader
description: Allows loading published subsets from projects of type "Library".
---

# Library Loader

Library loader is extended [loader](artist_tools_loader) which allows to load published subsets from Library projects. Controls are same but library loader has extra Combo Box which allows you to choose project you want to load from.

<div class="row markdown">
<div class="col col--6 markdown">

![tools_library_1](assets/tools/tools_library_1-small.png) <!-- picture needs to be changed -->

</div>
<div class="col col--6 markdown">

![tools_library_2](assets/tools/tools_library_2-small.png) <!-- picture needs to be changed -->

</div>
</div>

## Delivery Action

Library Loader contains functionality to export any selected asset, subsets and their version to configurable folder.
Delivery follows structure based on defined template, this template must be configured first by Admin in the Settings.

![delivery_action](assets/tools/tools_delivery_loader.png) 

* Usage
- Select all required subsets for export (you can change theirs versions by double clicking on 'Version' value)
- Right click and select **Deliver Versions** from context menu
- Select predefined Delivery template (must be configured by Admin system or project wide)
- Fill value for root folder (folder will be created if it doesn't exist)
- Filter out type of representation you are not interested in
- Push **Deliver** button
- Dialog must be kept open until export is finished
- In a case of problems with any of the representation, that one will be skipped, description of error will be provided in the dialog


