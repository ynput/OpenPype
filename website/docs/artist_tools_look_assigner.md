---
id: artist_tools_look_assigner
title: Look Assigner
sidebar_label: Look Assigner
description: Manage published looks to their respective model(s).
---

# Look Assigner

The Look Manager takes care of assigning published looks to the correct model in the scene.

## Details

When a look is published it also stores the information about what shading networks need to be assigned to which models, but it also stores all the render attributes on the mesh necessary for a successful render.

## Usage

Look Assigner has GUI is made of two parts. On the left you will see the list of all the available models in the scene and on the right side, all the looks that can be associate with them. To assign a look to a model you just need to:

1.  Click on "load all subsets".
2.  Choose a subset from the menu on the left.
3.  Right click on a look from the list on the right.
4.  Choose "Assign".

At this point you should have a model with all it's shaders applied correctly. The tool automatically loads the latest look available.

