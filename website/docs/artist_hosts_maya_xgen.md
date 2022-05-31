---
id: artist_hosts_maya_xgen
title: Xgen for Maya
sidebar_label: Xgen
---

## Working with Xgen in OpenPype

OpenPype support publishing and loading of Xgen interactive grooms. You can publish 
them as mayaAscii files with scalps that can be loaded into another maya scene, or as
alembic caches. 

### Publishing Xgen Grooms

To prepare xgen for publishing just select all the descriptions that should be published together and the create Xgen Subset in the scene using - **OpenPype menu** → **Create**... and select **Xgen Interactive**. Leave Use selection checked.

For actual publishing of your groom to go **OpenPype → Publish** and then press ▶ to publish. This will export `.ma` file containing your grooms with any geometries they are attached to and also a baked cache in `.abc` format 


:::tip adding more descriptions
You can add multiple xgen description into the subset you are about to publish, simply by
adding them to the maya set that was created for you. Please make sure that only xgen description nodes are present inside of the set and not the scalp geometry. 
:::

### Loading Xgen

You can use published xgens by loading them using OpenPype Publisher. You can choose to reference or import xgen. We don't have any automatic mesh linking at the moment and it is expected, that groom is published with a scalp, that can then be manually attached to your animated mesh for example. 

The alembic representation can be loaded too and it contains the groom converted to curves. Keep in mind that the density of the alembic directly depends on your viewport xgen density at the point of export.
