---
id: artist_hosts_houdini
title: Houdini
sidebar_label: Houdini
---

## OpenPype global tools

- [Work Files](artist_tools.md#workfiles)
- [Create](artist_tools.md#creator)
- [Load](artist_tools.md#loader)
- [Manage (Inventory)](artist_tools.md#inventory)
- [Publish](artist_tools.md#publisher)
- [Library Loader](artist_tools.md#library-loader)

## Publishing
### Publishing Alembic Cameras
You can publish baked camera in Alembic format. Select your camera and go **OpenPype -> Create** and select **Camera (abc)**.
This will create Alembic Driver node in **out** with path and frame range already set. This node will have a name you've
assigned in the **Creator** menu. For example if you name the subset `Default`, output Alembic Driver will be named
`cameraDefault`. After that, you can **OpenPype -> Publish** and after some validations your camera will be published
to `abc` file.

### Composite - Image Sequence
You can publish image sequence directly from Houdini. You can use any `cop` network you have and publish image
sequence generated from it.