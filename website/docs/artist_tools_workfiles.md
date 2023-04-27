---
id: artist_tools_workfiles
title: Workfiles
sidebar_label: Workfiles
description: Save versioned progress files.
---

# Workfiles

Save new working scenes or scripts, or open the ones you previously worked on.

## Details

Instead of digging through your software native file browser, you can simply open the workfiles app and see all the files for the asset or shot you're currently working with. The app takes care of all the naming and the location of your work files.

When saving a scene you can also add a comment. It is completely up to you how you use this, however we recommend using it for subversion within your current working version.

Let's say that the last version of the comp you published was v003 and now you're working on the file prj_sh010_compositing_v004.nk if you want to keep snapshots of your work, but not iterate on the main version because the supervisor is expecting next publish to be v004, you can use the comment to do this, so you can save the file under the name prj_sh010_compositing_v004_001 , prj_sh010_compositing_v004_002. the main version is automatically iterated every time you publish something.

## Usage

<div class="row markdown">
<div class="col col--6 markdown">

### To open existing file:

1. Open Workfiles tool from OpenPype menu
2. Select file from list - the latest version is the highest *(descendent ordering)*
3. Press `Open` button

</div>
<div class="col col--6 markdown">

![workfiles_1](assets/workfiles_1.png)

</div>
</div>


### To save new workfile
1. Open Workfiles tool from OpenPype menu
2. Press `Save As` button
3. You can add optional comment to the filename, that will be appended at the end
4. Press `OK`

:::note
You can manually override the workfile version by unticking next available version and using the version menu to choose your own.
:::

