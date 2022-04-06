---
id: artist_hosts_blender
title: Blender
sidebar_label: Blender
---

##OpenPype global tools

-   [Set Context](artist_tools.md#set-context)
-   [Work Files](artist_tools.md#workfiles)
-   [Create](artist_tools.md#creator)
-   [Load](artist_tools.md#loader)
-   [Manage (Inventory)](artist_tools.md#inventory)
-   [Publish](artist_tools.md#publisher)
-   [Library Loader](artist_tools.md#library-loader)

### Glossary:

**Avalon custon property:**

custom property stores ion the container of an asset.
It stores some data needed to find the object in the mongoDb

**Container:** 

Collection on the root of the asset hierarchy. It stores the avalon custom property. 


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

##Publishing models: 

###Intro:
Publishing models in Blender is pretty straightforward.
Create your model as you need. You might need to adhere to specifications of your studio that 
can be different between studios and projects but by default 
your geometry does not need any other convention.

![](assets/blender-simple_model.png)

###Creating instance:

Now create **Model instance** from it to let OpenPype know what in the scene you want to publish. Go **OpenPype → Create... → Model**.

![](assets/blender-instance_creator.png)

`ASSET` field is a name of asset you are working on - it should be already filled with correct name as you've started Blender or switched context to specific asset. You can edit that field to change it to different asset (but that one must already exists).

`SUBSET` field is a name you can decide on.
It should describe what kind of data you have in the model.
For example, you can name it `Proxy` to indicate that this is low resolution stuff.
See Subset.

Read-only field just under it show final subset name,
adding subset field to name of the group you have selected.

`USE SELECTION` checkbox will use whatever you have selected in Outliner to be wrapped in Model instance.
This is usually what you want.(The collections have to be add by hand). Click on **CREATE** button.

![](assets/blender-create_model.png)

You'll notice then after you've created new Model instance, there is a new collection in Outliner called after your asset and subset, in our case it is `character1_modelDefault`. The assets selected when creating the Model instance are linked in the new collection.


And that's it, you have your first model ready to publish.

### save:

Now save your scene (if you didn't do it already).
**OpenPype → Create... → Work Files**.
You will notice that path in Save dialog is already set to place where scenes related
to modeling task on your asset should reside.
As in our case we are working on asset called **Bibi** and on task **modeling**,
path relative to your project directory will be `project_XY/assets/Bibi/work/modeling`.
The default name for the file will be `project_XY_asset_task_version`,
so in our case `woolly_bibi_modeling_v001.blend`.
Let's save it.

![](assets/blender-work_files.png)

### Publish:

Now let's publish it. Go **OpenPype → Publish**.... You will be presented with following window

![](assets/blender-publish.png)

Note that content of this window can differs by your pipeline configuration. For more detail see [Publisher](artist_tools.md#publisher).

#### Left column:

Items in left column are instances you will be publishing. 
You can disable them by clicking on square next to them. 
White filled square indicate they are ready for publishing,
red means something went wrong either during collection phase or publishing phase.
Empty one with gray text is disabled.

See that in this case we are publishing from the scene file `wooly_Bibi_Modeling_v001.blend`
the Blender model named `Bibi_modelDefault`.

#### Right column:

Right column lists all tasks that are run during collection,
validation,
extraction and integration phase.
White items are optional and you can disable them by clicking on them.

#### Launch Publish:

Lets do dry-run on publishing to see if we pass all validators.
Click on flask icon at the bottom. Validators are run. 
Ideally you will end up with everything green in validator section.

### Fixing problems:

For the sake of demonstration,
I intentionally kept the model with the transform not at zero,
to trigger the validator designed to check just this.

![](assets/blender-fixing_publish.png)

You can see our model is now marked red in left column and in right we have red box next to Mesh is in Object Mode validator.



#### Error details:

You can click on arrow next to it to see more details:

From there you can see in **Records** entry that there is problem with the object `Cube`.

![](assets/blender-publish_error_detail.png)



#### Action on validator:

Some validators have option to fix problem for you or just select objects that cause trouble.
This is the case with our failed validator.

In main overview you can notice little A in a circle next to validator name.
Right click on it and you can see menu item `Select invalid`.
This will select offending object in Blender.

![](assets/blender-publish_action.png)

Fix is easy. Without closing [Publisher](artist_tools.md#publisher) window we just turn back the Object Mode.
Then we need to reset it to make it notice changes we've made.
Click on arrow circle button at the bottom and it will reset the [Publisher](artist_tools.md#publisher) to initial state.
Run validators again (flask icon) to see if everything is ok.

It should OK be now. Write some comment if you want and click play icon button when ready.

Publish process will now take its course. Depending on data you are publishing it can take a while.
You should end up with everything green and message **Finished successfully** ...
You can now close publisher window.

To check for yourself that model is published,
open Asset [Loader](artist_tools.md#loader) - **OpenPype → Load....** There you should see your model,
named `modelDefault`.



##Creating Rigs
Creating and publishing rigs with OpenPype follows similar workflow as with other data types.
Create your rig and mark parts of your hierarchy in sets to help OpenPype validators and extractors to check it and publish it.

###Loading models
You can load model with [Loader](artist_tools.md#loader). **Go OpenPype → Load...**, select your Model, right click on it and click Link model (blend).

![](assets/blender-load_model.png)

The loaded model is linked and is overridden automatically 

![](assets/blender-loaded_model.png)

###Preparing rig for publish
When creating rigs in Blender, it is important to keep a specific structure for the bones and the geometry. Let's first create a model and its rig. For demonstration, I'll create a simple model for a robotic arm made of simple boxes.

![](assets/blender-simple_rig.png)

I have now created the armature `Armature`. While the naming is not important,
you can just adhere to your naming conventions, the hierarchy is.
The geometry must be organized in a separate Collection.
In this case, I have the armature in the main Collection, and the geometry is in the `Bibi_modelDefault collection`.

![](assets/blender-rig_hierarchy.png)

You need to Make Local the objects and Meshes you want Once the models are skinned to the armature.

![](assets/blender-make_local.png)

###Creating instance:

When you've prepared your hierarchy, it's time to create Rig instance in OpenPype. Select your whole rig hierarchy and go **OpenPype → Create....** Select Rig.

![](assets/blender-create_rig.png)

A new collection named after the selected Asset and Subset should have been created. In our case, it is `Bibi_rigDefault`. All the selected armature and models have been linked in this new collection. You should end up with something like this:

![](assets/blender-rig_create2.png)

### Save:

Save your scene (if you didn't do it already). **OpenPype → Work Files**. 

### Publishing rigs:
 
Now let's publish it. Go **OpenPype → Publish**.... You will be presented with following window

The model container have local parts then the validate_object_linked validator raise an error.

![](assets/blender-validate_object_link_error.png)

A small "a" in circle appear on the left of the validator. You need to right-click on them and click on "Extract and publish not linked".

![](assets/blender-extract_and_publish.png)

At the end of the process you should have all the container linked to a library and overridden.



![](assets/blender-rig_container.png)

You can relaunch the publish. Which should now be ok.


