---
id: artist_hosts_tvpaint
title: TVPaint
sidebar_label: TVPaint
---

-   [Work Files](artist_tools.md#workfiles)
-   [Load](artist_tools.md#loader)
-   [Create](artist_tools.md#creator)
-   [Subset Manager](artist_tools.md#subset-manager)
-   [Scene Inventory](artist_tools.md#scene-inventory)
-   [Publish](artist_tools.md#publisher)
-   [Library](artist_tools.md#library)


## Setup
When you launch TVPaint with OpenPype for the very first time it is necessary to do some additional steps. Right after the TVPaint launching a few system windows will pop up. 

![permission](assets/tvp_permission.png)

Choose `Replace the file in the destination`. Then another window shows up. 

![permission2](assets/tvp_permission2.png)

Click on `Continue`.

After opening TVPaint go to the menu bar: `Windows → Plugins → OpenPype`. 

![pypewindow](assets/tvp_hidden_window.gif)

Another TVPaint window pop up. Please press `Yes`. This window will be presented in every single TVPaint launching. Unfortunately, there is no other way how to workaround it. 

![writefile](assets/tvp_write_file.png)

Now OpenPype Tools menu is in your TVPaint work area. 

![openpypetools](assets/tvp_openpype_menu.png)

You can start your work. 

---

## Usage
In TVPaint you can find the Tools in OpenPype menu extension. The OpenPype Tools menu should be available in your work area. However, sometimes it happens that the Tools menu is hidden. You can display the extension panel by going to `Windows -> Plugins -> OpenPype`.


## Create 
In TVPaint you can create and publish **[Reviews](#review)**, **[Render Passes](#render-pass)**, and **[Render Layers](#render-layer)**. 

You have the possibility to organize your layers by using `Color group`.  

On the bottom left corner of your timeline, you will note a `Color group` button.

![colorgroups](assets/tvp_color_groups.png)

It allows you to choose a group by checking one of the colors of the color list. 

![colorgroups](assets/tvp_color_groups2.png)

The timeline's animation layer can be marked by the color you pick from your Color group. Layers in the timeline with the same color are gathered into a group represents one render layer. 

![timeline](assets/tvp_timeline_color.png)

:::important
OpenPype specifically never tries to guess what you want to publish from the scene. Therefore, you have to tell OpenPype what you want to publish. There are three ways how to publish render from the scene. 
:::

When you want to publish `review` or `render layer` or `render pass`, open the `Creator` through the Tools menu `Create` button.

### Review 

<div class="row markdown">
<div class="col col--6 markdown">

`Review` renders the whole file as is and sends the resulting QuickTime to Ftrack. 

To create reviewable quicktime of your animation:

- select `Review` in the `Creator`
- press `Create`
- When you run [publish](#publish), file will be rendered and converted to quicktime.`

</div>
<div class="col col--6 markdown">

![createreview](assets/tvp_create_review.png)

</div>
</div>

### Render Layer

<div class="row markdown">
<div class="col col--6 markdown">


Render Layer bakes all the animation layers of one particular color group together. 

- Choose any amount of animation layers that need to be rendered together and assign them a color group. 
- Select any layer of a particular color
- Go to `Creator` and choose `RenderLayer`. 
- In the `Subset`, type in the name that the final published RenderLayer should have according to the naming convention in your studio. *(L10, BG, Hero, etc.)* 
- Press `Create`
- When you run [publish](#publish), the whole color group will be rendered together and published as a single `RenderLayer`

</div>
<div class="col col--6 markdown">

![createlayer](assets/tvp_create_layer.png)

</div>
</div>





### Render Pass

Render Passes are smaller individual elements of a Render Layer. A `character` render layer might
consist of multiple render passes such as `Line`, `Color` and `Shadow`.


<div class="row markdown">
<div class="col col--6 markdown">
Render Passes are specific because they have to belong to a particular layer. If you try to create a render pass and did not create any render layers before, an error message will pop up. 

When you want to create `RenderPass`
- choose one or several animation layers within one color group that you want to publish
- In the Creator, pick `RenderPass`
- Fill the `Subset` with the name of your pass, e.g. `Color`. 
- Press `Create`

</div>
<div class="col col--6 markdown">

![createpass](assets/tvp_create_pass.png)

</div>
</div>

<br></br>

In this example, OpenPype will render selected animation layers within the given color group. E.i. the layers *L020_colour_fx*, *L020_colour_mouth*, and *L020_colour_eye* will be rendered as one pass belonging to the yellow RenderLayer.  

![renderpass](assets/tvp_timeline_color2.png)


:::note
You can check your RendrePasses and RenderLayers in [Subset Manager](#subset-manager) or you can start publishing. The publisher will show you a collection of all instances on the left side.
:::


---

## Publish 

<div class="row markdown">
<div class="col col--6 markdown">

Now that you have created the required instances, you can publish them via `Publish` tool. 
- Click on `Publish` in OpenPype Tools menu.
- wait until all instances are collected. 
- You can check on the left side whether all your instances have been created and are ready for publishing. 
- Fill the comment on the bottom of the window.
- Press the `Play` button to publish

</div>
<div class="col col--6 markdown">

![pyblish](assets/tvp_pyblish_render.png)

</div>
</div>

Once the `Publisher` turns gets green your renders have been published. 

---

## Subset Manager
All created instances (render layers, passes, and reviews) will be shown as a simple list. If you don't want to publish some, right click on the item in the list and select `Remove instance`.

![subsetmanager](assets/tvp_subset_manager.png)

---

## Load 
When you want to load existing published work you can reach the `Loader` through the OpenPype Tools `Load` button.

The supported families for TVPaint are:

- `render`
- `image`
- `background`
- `plate`

To load a family item, right-click on the subset you want and import their representations, switch among the versions, delete older versions, copy files, etc.

![Loader](assets/tvp_loader.gif)

---

## Scene Inventory
Scene Inventory shows you everything that you have loaded into your scene using OpenPype. You can reach it through the extension's `Scene Inventory` button.

![sceneinventory](assets/tvp_scene_inventory.png)

You can switch to a previous version of the file or update it to the latest or delete items. 
