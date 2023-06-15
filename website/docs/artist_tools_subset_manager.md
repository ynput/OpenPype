---
id: artist_tools_subset_manager
title: Subset Manager
sidebar_label: Subset Manager
description: Manage all the publish-able elements.
---

# Subset Manager

Subset Manager lists all items which are meant for publishig and will be published if Publish is triggered

## Details

One or more items (instances) could be published any time Publish process is started. Each this publishable
item must be created by Creator tool previously. Subset Manager provides easy way how to check which items, 
and how many, will be published. 

It also provides clean and preferable way how to remove unwanted item from publishing.

## Usage

Subset Manager has GUI is made of two parts. On the left you will see the list of all the available publishable items in the scene and on the right side, details about these items.

<div class="col col--6 markdown">

![subset_manager](assets/tools_subset_manager.png)
</div>

Any time new item is Created, it will show up here.

Currently there is only single action, 'Remove instance' which cleans workfile file from publishable item metadata.
This might not remove underlying host item, it depends on host and implementation!

It might also happen that user deletes underlying host item(for example layer in Photoshop) directly in the host, but metadata will stay.
This could result in phantom issues during publishing. Use Subset Manager to purge workfile from abandoned items.

Please check behaviour in host of your choice.

