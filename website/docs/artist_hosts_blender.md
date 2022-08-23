---
id: artist_hosts_blender
title: Blender
sidebar_label: Blender
---

## OpenPype global tools

-   [Set Context](artist_tools.md#set-context)
-   [Work Files](artist_tools.md#workfiles)
-   [Create](artist_tools.md#creator)
-   [Load](artist_tools.md#loader)
-   [Manage (Inventory)](artist_tools.md#inventory)
-   [Publish](artist_tools.md#publisher)
-   [Library Loader](artist_tools.md#library-loader)

## Working with OpenPype in Blender

OpenPype is here to ease you the burden of working on project with lots of
collaborators, worrying about naming, setting stuff, browsing through endless
directories, loading and exporting and so on. To achieve that, OpenPype is using
concept of being _"data driven"_. This means that what happens when publishing
is influenced by data in scene. This can by slightly confusing so let's get to
it with few examples.


## Setting scene data

Blender settings concerning framerate, resolution and frame range are handled
by OpenPype. If set correctly in Ftrack, Blender will automatically set the 
values for you.


## Publishing models

### Intro

Publishing models in Blender is pretty straightforward. Create your model as you
need. You might need to adhere to specifications of your studio that can be different
between studios and projects but by default your geometry does not need any
other convention.

![Model example](assets/blender-model_example.jpg)

### Creating instance

Now create **Model instance** from it to let OpenPype know what in the scene you want to
publish. Go **OpenPype → Create... → Model**.

![Model create instance](assets/blender-model_create_instance.jpg)

`Asset` field is a name of asset you are working on - it should be already filled
with correct name as you've started Blender or switched context to specific asset. You
can edit that field to change it to different asset (but that one must already exists).

`Subset` field is a name you can decide on. It should describe what kind of data you
have in the model. For example, you can name it `Proxy` to indicate that this is
low resolution stuff. See [Subset](artist_concepts.md#subset).

<!-- :::note LOD support
By changing subset name you can take advantage of _LOD support_ in OpenPype. Your
asset can contain various resolution defined by different subsets. You can then
switch between them very easy using [Inventory (Manage)](artist_tools.md#inventory).
There LODs are conveniently grouped so they don't clutter Inventory view.

Name your subset like `main_LOD1`. Important part is that `_LOD1`. You can have as many LODs as you need.
::: -->

Read-only field just under it show final subset name, adding subset field to
name of the group you have selected.

`Use selection` checkbox will use whatever you have selected in Outliner to be
wrapped in Model instance. This is usually what you want. Click on **Create** button.

You'll notice then after you've created new Model instance, there is a new 
collection in Outliner called after your asset and subset, in our case it is
`character1_modelDefault`. The assets selected when creating the Model instance
are linked in the new collection.

And that's it, you have your first model ready to publish.

Now save your scene (if you didn't do it already). You will notice that path
in Save dialog is already set to place where scenes related to modeling task on
your asset should reside. As in our case we are working on asset called
**character1** and on task **modeling**, path relative to your project directory will be
`project_XY/assets/character1/work/modeling`. The default name for the file will
be `project_XY_asset_task_version`, so in our case 
`simonetest_character1_modeling_v001.blend`. Let's save it.

![Model create instance](assets/blender-save_modelling_file.jpg)

### Publishing models

Now let's publish it. Go **OpenPype → Publish...**. You will be presented with following window:

![Model publish](assets/blender-model_pre_publish.jpg)

Note that content of this window can differs by your pipeline configuration.
For more detail see [Publisher](artist_tools.md#publisher).

Items in left column are instances you will be publishing. You can disable them
by clicking on square next to them. White filled square indicate they are ready for
publishing, red means something went wrong either during collection phase
or publishing phase. Empty one with gray text is disabled.

See that in this case we are publishing from the scene file
`simonetest_character1_modeling_v001.blend` the Blender model named 
`character1_modelDefault`.

Right column lists all tasks that are run during collection, validation,
extraction and integration phase. White items are optional and you can disable
them by clicking on them.

Lets do dry-run on publishing to see if we pass all validators. Click on flask
icon at the bottom. Validators are run. Ideally you will end up with everything
green in validator section.

### Fixing problems

For the sake of demonstration, I intentionally kept the model in Edit Mode, to
trigger the validator designed to check just this.

![Failed Model Validator](assets/blender-model_publish_error.jpg)

You can see our model is now marked red in left column and in right we have
red box next to `Mesh is in Object Mode` validator.

You can click on arrow next to it to see more details:

![Failed Model Validator details](assets/blender-model_error_details.jpg)

From there you can see in **Records** entry that there is problem with the
object `Suzanne`. Some validators have option to fix problem for you or just 
select objects that cause trouble. This is the case with our failed validator.

In main overview you can notice little A in a circle next to validator
name. Right click on it and you can see menu item `select invalid`. This
will select offending object in Blender.

Fix is easy. Without closing Publisher window we just turn back the Object Mode.
Then we need to reset it to make it notice changes we've made. Click on arrow
circle button at the bottom and it will reset the Publisher to initial state. Run
validators again (flask icon) to see if everything is ok.

It should OK be now. Write some comment if you want and click play icon button
when ready.

Publish process will now take its course. Depending on data you are publishing
it can take a while. You should end up with everything green and message
**Finished successfully ...** You can now close publisher window.

To check for yourself that model is published, open
[Asset Loader](artist_tools.md#loader) - **OpenPype → Load...**.
There you should see your model, named `modelDefault`.

### Loading models

You can load model with [Loader](artist_tools.md#loader). Go **OpenPype → Load...**,
select your rig, right click on it and click **Link model (blend)**.

## Creating Rigs

Creating and publishing rigs with OpenPype follows similar workflow as with
other data types. Create your rig and mark parts of your hierarchy in sets to
help OpenPype validators and extractors to check it and publish it.

### Preparing rig for publish

When creating rigs in Blender, it is important to keep a specific structure for
the bones and the geometry. Let's first create a model and its rig. For
demonstration, I'll create a simple model for a robotic arm made of simple boxes.

![Blender - Simple model for rigging](assets/blender-rig_model_setup.jpg)

I have now created the armature `RIG_RobotArm`. While the naming is not important,
you can just adhere to your naming conventions, the hierarchy is. Once the models
are skinned to the armature, the geometry must be organized in a separate Collection.
In this case, I have the armature in the main Collection, and the geometry in 
the `Geometry` Collection.

![Blender - Rig Hierarchy Example](assets/blender-rig_hierarchy_example.jpg)

When you've prepared your hierarchy, it's time to create *Rig instance* in OpenPype.
Select your whole rig hierarchy and go **OpenPype → Create...**. Select **Rig**.

![Blender - Rig Hierarchy Example](assets/blender-rig_create.jpg)

A new collection named after the selected Asset and Subset should have been created.
In our case, it is `character1_rigDefault`. All the selected armature and models
have been linked in this new collection. You should end up with something like
this:

![Blender - Rig Hierarchy Example](assets/blender-rig_hierarchy_before_publish.jpg)

### Publishing rigs

Publishing rig is done in same way as publishing everything else. Save your scene
and go **OpenPype → Publish**. For more detail see [Publisher](artist_tools.md#publisher).

### Loading rigs

You can load rig with [Loader](artist_tools.md#loader). Go **OpenPype → Load...**,
select your rig, right click on it and click **Link rig (blend)**.

## Layouts in Blender

A layout is a set of elements that populate a scene. OpenPype allows to version
and manage those sets.

### Publishing a layout

Working with Layout is easy. Just load your assets into scene with
[Loader](artist_tools.md#loader) (**OpenPype → Load...**). Populate your scene as
you wish, translate each piece to fit your need. When ready, select all imported
stuff and go **OpenPype → Create...** and select **Layout**. When selecting rigs,
you need to select only the armature, the geometry will automatically be included.
This will create set containing your selection and marking it for publishing.

Now you can publish is with **OpenPype → Publish**.

### Loading layouts

You can load a Layout using [Loader](artist_tools.md#loader)
(**OpenPype → Load...**). Select your layout, right click on it and
select **Link Layout (blend)**. This will populate your scene with all those
models you've put into layout.