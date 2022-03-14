---
id: artist_hosts_photoshop
title: Photoshop
sidebar_label: Photoshop
---

## Available Tools

-   [Work Files](artist_tools.md#workfiles)
-   [Create](artist_tools.md#creator)
-   [Load](artist_tools.md#loader)
-   [Publish](artist_tools.md#publisher)
-   [Manage](artist_tools.md#inventory)

## Setup

To install the extension, download, install [Anastasyi's Extension Manager](https://install.anastasiy.com/). Open Anastasyi's Extension Manager and select Photoshop in menu. Then go to `{path to pype}hosts/photoshop/api/extension.zxp`. Drag extension.zxp and drop it to Anastasyi's Extension Manager. The extension will install itself. 

## Usage

When you launch Photoshop you will be met with the Workfiles app. If dont have any previous workfiles, you can just close this window.

In Photoshop you can find the tools in the `OpenPype` extension:

![Extension](assets/photoshop_extension.PNG) <!-- picture needs to be changed -->

You can show the extension panel by going to `Window` > `Extensions` > `OpenPype`.

### Create

When you have created an image you want to publish, you will need to create special groups or tag existing groups. To do this open the `Creator` through the extensions `Create` button.

![Creator](assets/photoshop_creator.PNG)

With the `Creator` you have a variety of options to create:

- Check `Use selection` (A dialog will ask whether you want to create one image per selected layer).
    - Yes.
        - No selection.
            - This will create a single group named after the `Subset` in the `Creator`.
        - Single selected layer.
            - The selected layer will be grouped under a single group named after the selected layer.
        - Single selected group.
            - The selected group will be tagged for publishing.
        - Multiple selected items.
            - Each selected group will be tagged for publishing and each layer will be grouped individually.
    - No.
        - All selected layers will be grouped under a single group named after the `Subset` in the `Creator`.
- Uncheck `Use selection`.
    - This will create a single group named after the `Subset` in the `Creator`.

### Publish

When you are ready to share some work, you will need to publish. This is done by opening the `Pyblish` through the extensions `Publish` button.

![Publish](assets/photoshop_publish.PNG) <!-- picture needs to be changed -->

This tool will run through checks to make sure the contents you are publishing is correct. Hit the "Play" button to start publishing.

You may encounter issues with publishing which will be indicated with red squares. If these issues are within the validation section, then you can fix the issue. If there are issues outside of validation section, please let the OpenPype team know.

#### Repair Validation Issues

All validators will give some description about what the issue is. You can inspect this by going into the validator through the arrow:

![Inspect](assets/photoshop_publish_inspect.PNG) <!-- picture needs to be changed -->

You can expand the errors by clicking on them for more details:

![Expand](assets/photoshop_publish_expand.PNG) <!-- picture needs to be changed -->

Some validator have repair actions, which will fix the issue. If you can identify validators with actions by the circle icon with an "A":

![Actions](assets/photoshop_publish_actions.PNG) <!-- picture needs to be changed -->

To access the actions, you right click on the validator. If an action runs successfully, the actions icon will turn green. Once all issues are fixed, you can just hit the "Refresh" button and try to publish again.

![Repair](assets/photoshop_publish_repair.gif) <!-- picture needs to be changed -->

### Load

When you want to load existing published work, you can load in smart layers through the `Loader`. You can reach the `Loader` through the extension's `Load` button.

![Loader](assets/photoshop_loader.PNG) <!-- picture needs to be changed -->

The supported families for Photoshop are:

- `image`

To load an image, right-click on the subset you want and choose a representation:

![Loader](assets/photoshop_loader_load.gif)

### Manage

Now that we have some images loaded, we can manage which version is loaded. This is done through the `Scene Inventory`. You can reach it through the extension's `Manage` button.

:::note
Loaded images has to stay as smart layers in order to be updated. If you rasterize the layer, you cannot update it to a different version.
:::

![Loader](assets/photoshop_manage.PNG)

You can switch to a previous version of the image or update to the latest.

![Loader](assets/photoshop_manage_switch.gif)
![Loader](assets/photoshop_manage_update.gif)
