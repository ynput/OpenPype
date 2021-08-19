---
id: artist_hosts_nuke_tut
title: Nuke QuickStart
sidebar_label: Nuke QuickStart
---

# Nuke QuickStart
- [Nuke QuickStart](#nuke-quickstart)
  - [Run Nuke - Shot and Task Context](#run-nuke---shot-and-task-context)
  - [Save Nuke script – the Work File](#save-nuke-script--the-work-file)
  - [Load plate – Asset Loader](#load-plate--asset-loader)
  - [Create Write Node – Instance Creator](#create-write-node--instance-creator)
  - [What Nuke Publish Does](#what-nuke-publish-does)
      - [Publish steps](#publish-steps)
      - [Pyblish Note and Intent](#pyblish-note-and-intent)
      - [Pyblish Checkbox](#pyblish-checkbox)
      - [Pyblish Dialog](#pyblish-dialog)
  - [Review](#review)
  - [Render and Publish](#render-and-publish)
  - [Version-less Render](#version-less-render)
  - [Fixing Validate Containers](#fixing-validate-containers)
  - [Fixing Validate Version](#fixing-validate-version)

This QuickStart is just a small introduction to what OpenPype can do for you. It attempts to make an overview for compositing artists, and simplifies processes that are better described in specific parts of the documentation.

## Run Nuke - Shot and Task Context
OpenPype has to know what shot and task you are working on. You need to run Nuke in context of the task, using Ftrack Action or OpenPype Launcher to select the task and run Nuke.

![Run Nuke From Ftrack](assets/nuke_tut/nuke_RunNukeFtrackAction_p2.png)
![Run Nuke From Launcher](assets/nuke_tut/nuke_RunNukeLauncher_p2.png)


OpenPype menu shows the current context - shot and task.

If you use Ftrack, executing Nuke with context stops your timer, and starts the Ftrack clock on the shot and task you picked.

![Context](assets/nuke_tut/nuke_Context.png)

:::tip Admin Tip - Nuke version
You can [configure](admin_settings_project_anatomy.md#Attributes) which version(s) will be available for current project in **Studio Settings → Project → Anatomy → Attributes → Applications**
:::

## Save Nuke script – the Work File
Use OpenPype - Work files menu to create a new Nuke script. Openpype offers you the preconfigured naming. 
![Context](assets/nuke_tut/nuke_AssetLoader.png)

Openpype makes initial setup for your Nuke script. It is the same as running [Apply All Settings](artist_hosts_nuke.md#apply-all-settings) from the OpenPype menu.
Reads frame range and resolution from Avalon database, sets it in Nuke Project Settings
Creates Viewer node, sets it’s range and indicates handles by In and Out points
Reads Color settings from the project configuration, and sets it in Nuke Project Settings and Viewer
Sets project directory in the Nuke Project Settings to the Nuke Script Directory

:::tip Admin Tip - Workfile Naming
The [workfile naming](admin_settings_project_anatomy#templates) is configured in anatomy, see **Studio Settings → Project → Anatomy → Templates → Work**
:::

:::tip Admin Tip - Open Workfile
You can [configure](project_settings/settings_project_nuke#create-first-workfile) Nuke to automatically open the last version, or create a file on startup. See **Studio Settings → Project → Global → Tools → Workfiles**
:::

:::tip Admin Tip - Nuke Color Settings
[Color setting](project_settings/settings_project_nuke) for Nuke can be found in **Studio Settings → Project → Anatomy → Color Management and Output Formats → Nuke**
:::

## Load plate – Asset Loader
If your IO or editorial prepared plates and references, or your CG team has a render to be composited, we need to load it.

![OpenPype Load](assets/nuke_tut/nuke_Load.png)
![Asset Load](assets/nuke_tut/nuke_AssetLoader.png)

Pick the plate asset, right click and choose Load Image Sequence to create a Read node in Nuke. Note that the Read node created by OpenPype is green and has an OpenPype Tab. Green color indicates the highest version available.

## Create Write Node – Instance Creator
To create OpenPype managed Write node, select the Read node you just created, from OpenPype menu, pick Create.
In the Instance Creator, pick Create Write Render, and Create.

![OpenPype Create](assets/nuke_tut/nuke_Create.png)
![OpenPype Create](assets/nuke_tut/nuke_Creator.png)

This will create a Group with a Write node inside.

:::tip Admin Tip - Configuring write node
You can configure write node parameters in **Studio Settings → Project → Anatomy → Color Management and Output Formats → Nuke → Nodes**
:::

## What Nuke Publish Does
From Artist perspective, Nuke publish gathers all the stuff found in the Nuke script with Publish checkbox set to on, exports stuff and raises the Nuke script (workfile) version.
The Pyblish dialog shows the progress of the process.

![OpenPype Publish](assets/nuke_tut/nuke_Publish.png)

![OpenPype Publish](assets/nuke_tut/nuke_PyblishDialogNuke.png)

#### Publish steps
- gathers all the stuff found in the Nuke script with Publish checkbox set to on (1)
- collects all the info (from the script, database…) (2)
- validates components to be published (checks render range and resolution...) (3)
- extracts data from the script (generates thumbnail, creates reviews like h264 ...) (4)
- copies and renames components (render, reviews, thumbnail, Nuke script...) to publish folder
- integrates components (writes to database, sends preview of the render to Ftrack ...) (5)
- increments Nuke script version, cleans up the render directory (6)

#### Pyblish Note and Intent
Artist can add Note and Intent before firing the publish (7) button. The Note and Intent is ment for easy communication between artist and supervisor. After publish, Note and Intent can be seen in Ftrack notes.

#### Pyblish Checkbox
Some may say Pyblish Dialog looks unnecessarily complex; it just tries to put a lot of info in a small area. One of the more tricky parts is that it uses non-standard checkboxes. Some squares can be turned on and off by the artist, some are mandatory.

#### Pyblish Dialog
The left column of the dialog shows what will be published. If you run the publish and decide to not publish the Nuke script, you can turn it off right in the Pyblish dialog by clicking on the checkbox. If you decide to render and  publish the shot in lower resolution to speed up the turnaround, you have to turn off the Write Resolution validator. If you want to use an older version of the asset (older version of the plate...), you have to turn off the Validate containers, and so on.

Time wise, gathering all the info and validating usually takes just a few seconds, but creating reviews for long, high resolution shots can take too much time on the artist machine.

More info about [Using Pyblish](artist_tools#using-pyblish)

:::tip Admin Tip - Configuring validators
You can configure Nuke validators like Output Resolution in **Studio Settings → Project → Nuke → Publish plugins**
:::

## Review
When you turn the review checkbox on in your OpenPype write node, here is what happens:
- OpenPype uses the current Nuke script to 
  - Load the render
  - Optionally apply LUT
  - Render Prores 4444 with the same resolution as your render
- Use Ffmpeg to convert the Prores to whatever review(s) you defined
- Use Ffmpeg to add (optional) burnin to the review(s) from previous step

Creating reviews is a part of the publishing process. If you choose to do a local publish or to use existing frames, review will be processed also on the artist's machine.
If you choose to publish on the farm, you will render and do reviews on the farm.

So far there is no option for using existing frames (from your local / check render) and just do the review on the farm.

More info about [configuring reviews](pype2/admin_presets_plugins#extractreview).

:::tip Admin Tip - Configuring Reviews
You can configure reviewsin **Studio Settings → Project → Global → Publish plugins → ExtractReview / ExtractBurnin**
Reviews can be configured separately for each host, task, or family. For example Maya can produce different review to Nuke, animation task can have different burnin then modelling, and plate can have different review then model.
:::

## Render and Publish
Let’s say you want to render and publish the shot right now, with only a Read and Write node. You need to decide if you want to render, check the render and then publish it, or you want to execute the render and publish in one go.

If you wish to check your render before publishing, you can use your local machine or your farm to render the write node as you would do without OpenPype, load and check your render (OpenPype Write has a convenience button for that), and if happy, use publish with Use existing frames option selected in the write node to generate the review on your local machine.

If you want to render and publish on the farm in one go, run publish with On farm option selected in the write node to render and make the review on farm.

![OpenPype Create](assets/nuke_tut/nuke_WriteNode.png)


## Version-less Render
OpenPype is configured so your render file names have no version number. The main advantage is that you can keep the render from the previous version and re-render only part of the shot. With care, this is handy.

Main disadvantage of this approach is that you can render only one version of your shot at one time. Otherwise you risk to partially overwrite your shot render before publishing copies and renames the rendered files to the properly versioned publish folder.

When making quick farm publishes, like making two versions with different color correction, care must be taken to let the first job (first version) completely finish before the second version starts rendering.

![Versionless](assets/nuke_tut/nuke_versionless.png)

## Fixing Validate Containers
If your Pyblish dialog fails on Validate Containers, you might have an old asset loaded. Use OpenPype - Manage... to switch the asset(s) to the latest greatest version.

## Fixing Validate Version
If your Pyblish dialog fails on Validate Version, you might be trying to publish already published version. Rise your version in the OpenPype WorkFiles SaveAs.

Or maybe you accidentaly copied write node from different shot to your current one. Check the write publishes on the left side of the Pyblish dialog. Typically you publish only one write. Locate and delete the stray write from other shot.