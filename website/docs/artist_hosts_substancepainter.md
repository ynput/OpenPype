---
id: artist_hosts_substancepainter
title: Substance Painter
sidebar_label: Substance Painter
---

## OpenPype global tools

-   [Work Files](artist_tools.md#workfiles)
-   [Load](artist_tools.md#loader)
-   [Manage (Inventory)](artist_tools.md#inventory)
-   [Publish](artist_tools.md#publisher)
-   [Library Loader](artist_tools.md#library-loader)

## Working with OpenPype in Substance Painter

The Substance Painter OpenPype integration allows you to:

- Set the project mesh and easily keep it in sync with updates of the model
- Easily export your textures as versioned publishes for others to load and update.

## Setting the project mesh

Substance Painter requires a project file to have a mesh path configured.
As such, you can't start a workfile without choosing a mesh path.

To start a new project using a published model you can _without an open project_
use OpenPype > Load.. > Load Mesh on a supported publish. This will prompt you
with a New Project prompt preset to that particular mesh file.

If you already have a project open, you can also replace (reload) your mesh 
using the same Load Mesh functionality. 

After having the project mesh loaded or reloaded through the loader
tool the mesh will be _managed_ by OpenPype. For example, you'll be notified 
on workfile open whether the mesh in your workfile is outdated. You can also
set it to specific version using OpenPype > Manage.. where you can right click 
on the project mesh to perform _Set Version_

:::info
A Substance Painter project will always have only one mesh set. Whenever you 
trigger _Load Mesh_ from the loader this will **replace** your currently loaded 
mesh for your open project.
:::

## Publishing textures

To publish your textures we must first create a `textureSet` 
publish instance. 

To create a **TextureSet instance** we will use OpenPype's publisher tool. Go 
to **OpenPype → Publish... → TextureSet**

The texture set instance will define what Substance Painter export template (`.spexp`) to
use and thus defines what texture maps will be exported from your workfile. This
can be set with the **Output Template** attribute on the instance.

:::info
The TextureSet instance gets saved with your Substance Painter project. As such, 
you will only need to configure this once for your workfile. Next time you can
just click **OpenPype → Publish...** and start publishing directly with the
same settings.
:::

#### Publish per output map of the Substance Painter preset

The Texture Set instance generates a publish per output map that is defined in
the Substance Painter's export preset. For example a publish from a default
PBR Metallic Roughness texture set results in six separate published subsets 
(if all the channels exist in your file).

![Substance Painter PBR Metallic Roughness Export Preset](assets/substancepainter_pbrmetallicroughness_export_preset.png)

When publishing for example a texture set with variant **Main** six instances will
be published with the variants: 
- Main.**BaseColor**
- Main.**Emissive**
- Main.**Height**
- Main.**Metallic**
- Main.**Normal**
- Main.**Roughness**

The bold output map name for the publish is based on the string that is pulled
from the what is considered to be the static part of the filename templates in 
the export preset. The tokens like `$mesh` and `(_$colorSpace)` are ignored.
So `$mesh_$textureSet_BaseColor(_$colorSpace)(.$udim)` becomes `BaseColor`.

An example output for PBR Metallic Roughness would be:

![Substance Painter PBR Metallic Roughness Publish Example in Loader](assets/substancepainter_pbrmetallicroughness_published.png)

## Known issues

#### Can't see the OpenPype menu?

If you're unable to see the OpenPype top level menu in Substance Painter make
sure you have launched Substance Painter through OpenPype and that the OpenPype
Integration plug-in is loaded inside Substance Painter: **Python > openpype_plugin**

#### Substance Painter + Steam

Running the steam version of Substance Painter within OpenPype will require you 
to close the Steam executable before launching Substance Painter through OpenPype. 
Otherwise the Substance Painter process is launched using Steam's existing 
environment and thus will not be able to pick up the pipeline integration.

This appears to be a limitation of how Steam works.