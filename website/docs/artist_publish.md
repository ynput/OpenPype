---
id: artist_publish
title: Publishing
sidebar_label: Publishing
---

## What is publishing?

A process of exporting particular data from your work scene to be shared with others.

Think of publishing as a checkpoint between two people, making sure that we catch mistakes as soon as possible and don’t let them pass through pipeline step that would eventually need to be repeated if these mistakes are not caught.

Every time you want to share a piece of work with others (be it camera, model, textures, animation or whatever), you need to publish this data. The main reason is to save time down the line and make it very clear what can and cannot be used in production.
This process should mostly be handled by publishing scripts but in certain cases might have to be done manually.

Published assets should comply to these rules:

- Clearly named, based on internal naming conventions.
- Versioned (with master version created for certain types of assets).
- Immediately usable, without any dependencies to unpublished assets or work files.
- Immutable

All of these go into the publish folder for the given entity (shot, asset, sequence)

:::note
Keep in mind that while publishing the data might take you some extra time, it will save much more time in the long run when your colleagues don’t need to dig through your work files trying to understand them and find that model you saved by hand.
:::

## Families:

The Instances are categorized into ‘families’ based on what type of data they contain. Some instances might have multiple families if needed. A shot camera will for example have families 'camera' and  'review' to indicate that it's going to be used for review quicktime, but also exported into a file on disk.

Following family definitions and requirements are OpenPype defaults and what we consider good industry practice, but most of the requirements can be easily altered to suit the studio or project needs.
Here's a list of supported families

| Family                  | Comment                                          | Example Subsets           |
| ----------------------- | ------------------------------------------------ | ------------------------- |
| [Model](#model)         | Cleaned geo without materials                    | main, proxy, broken       |
| [Look](#look)           | Package of shaders, assignments and textures     | main, wet, dirty          |
| [Rig](#rig)             | Characters or props with animation controls      | main, deform, sim         |
| [Assembly](#assembly)   | A complex model made from multiple other models. | main, deform, sim         |
| [Layout](#layout)       | Simple representation of the environment         | main,                     |
| [Setdress](#setdress)   | Environment containing only referenced assets    | main,                     |
| [Camera](#camera)       | May contain trackers or proxy geo                | main, tracked, anim       |
| [Animation](#animation) | Animation exported from a rig.                   | characterA, vehicleB      |
| [Cache](#cache)         | Arbitrary animated geometry or fx cache          | rest, ROM , pose01        |
| MayaAscii               | Maya publishes that don't fit other categories   |                           |
| [Render](#render)       | Rendered frames from CG or Comp                  |                           |
| RenderSetup             | Scene render settings, AOVs and layers           |                           |
| Plate                   | Ingested, transcode, conformed footage           | raw, graded, imageplane   |
| Write                   | Nuke write nodes for rendering                   |                           |
| Image                   | Any non-plate image to be used by artists        | Reference, ConceptArt     |
| LayeredImage            | Software agnostic layered image with metadata    | Reference, ConceptArt     |
| Review                  | Reviewable video or image.                       |                           |
| Matchmove               | Matchmoved camera, potentially with geometry     | main                      |
| Workfile                | Backup of the workfile with all its content      | uses the task name        |
| Nukenodes               | Any collection of nuke nodes                     | maskSetup, usefulBackdrop |
| Yeticache               | Cached out yeti fur setup                        |                           |
| YetiRig                 | Yeti groom ready to be applied to geometry cache | main, destroyed           |
| VrayProxy               | Vray proxy geometry for rendering                |                           |
| VrayScene               | Vray full scene export                           |                           |
| ArnodldStandin          | All arnold .ass archives for rendering           | main, wet, dirty          |
| LUT                     |                                                  |                           |
| Nukenodes               |                                                  |                           |
| Gizmo                   |                                                  |                           |
| Nukenodes               |                                                  |                           |
| Harmony.template        |                                                  |                           |
| Harmony.palette        |                                                  |                           |



### Model

Clean geometry without any material assignments. Published model can be as small as a single mesh, or as complex as a full building. That is purely up to the artist or the supervisor. Models can contain hierarchy defined by groups or nulls for better organisation.

Apart from model subsets, we also support LODs as extra level on top of subset. To publish LODs, you just need to prepare subsets for publishing names `modelMySubsetName_LOD##`, if OpenPype finds `_LOD##` (hashes replaced with LOD level), it will automatically be considered a LOD of the given subset.

Example Subsets:
`modelMain`, `modelProxy`, `modelSculpt`, `modelBroken`, `modelMain_LOD01`, `modelMain_LOD02`

Example representations:
`.ABC`, `.MA`, `.MB`, `.BLEND`, `.OBJ`, `.FBX`


### Look

A package of materials, shaders, assignments, textures and attributes that collectively define a look of a model for rendering or preview purposes. This can usually be applied only to the model is was authored for, or its corresponding cache, however, material sharing across multiple models is also possible. A look should be fully self-contained and ready for rendering.

Example Subsets:
`lookMain`, `lookProxy`, `lookWet`, `lookDirty`, `lookBlue`, `lookRed`

Example Representations:
`.MA + .JSON`, `.MTLX (yet unsupported)`, `.BLEND`

Please note that a look is almost never a single representation, but a combination of multiple.
For example in Maya a look consists of `.ma` file with the shaders, `.json` file which
contains the attributes and assignments and `/resources` folder with all the required textures.


### Rig

Characters or props with animation controls or other parameters, ready to be referenced into a scene and animated. Animation Rigs tend to be very software specific, but in general they tend to consist of Geometry, Bones or Joints, Controllers and Deformers. OpenPype in maya supports both, self-contained rigs, that include everything in one file, but also rigs that use nested references to bring in geometry, or even skeleton. By default we bake rigs into a single file during publishing, but that behaviour can be turned off to keep the nested references live in the animation scenes.

Example Subsets:
`rigMain`, `rigMocap`, `rigSim`, `rigCamera`, `rigMuscle`

Example Representations:
`.MA`, `.MB`, `.BLEND`, `.HDA`


### Assembly

A subset created by combining two or more smaller subsets into a composed bigger asset.
A good example would be a restaurant table asset with the cutlery and chairs included,
that will eventually be loaded into a restaurant Set. Instead of loading each individual
fork and knife for each table in the restaurant, we can first prepare `assemblyRestaurantTable` subset
which will contain the table itself, with cutlery, flowers, plates and chairs nicely arranged.

This table can then be loaded multiple times into the restaurant for easier scene management
and updates.

Extracted assembly doesn't contain any geometry directly, but rather information about all the individual subsets that are inside the assembly, their version and transformations. On top of that and alembic is exported which only holds any extra transforms and groups that are needed to fully re-create the original assembled scene.

Assembly ca also be used as a sort of collection of elements that are often used together in the shots. For example if we're set dressing lot's of forest shots, it would make sense to make and assembly of all the forest elements for scattering so we don't have to load them individually into each shot.

Example Subsets:
`assemblyTable`, `assemblyForestElements`, `assemblyRoof`

Example Representations:
`.ABC + .JSON`



### Setdress

Fully prepared environment scene assembled from other previously published assets. Setdress should be ready for rendering as is, including any instancing, material assignments and other complex setups the environment requires. Due to this complexity, setdress is currently only publishable in the native file format of the host where it was created. In maya that would be `.ma` or `.mb` file.


### Camera

Clean virtual camera without any proprietary rigging, or host specific information. Considering how widely across the hosts published cameras are used in production, published camera should ideally be as simple and clean as possible to ensure consistency when loaded into various hosts.


Example Representations:
`.MA`, `.ABC`


### Cache

Geometry or effect with baked animation. Cache is usually exported as alembic,
but can be potentially any other representation that makes sense in the given scenario.
Cache is defined by the artist directly in the fx or animation scene.

Example Subsets:
`assemblyTable`, `assemblyForestElements`, `assemblyRoof`

Example Representations:
`.ABC`, `.VDB`, `.BGEO`


### Animation

Published result of an animation created with a rig. Animation can be extracted
as animation curves, cached out geometry or even fully animated rig with all the controllers.  
Animation cache is usually defined by a rigger in the rig file of a character or
by FX TD in the effects rig, to ensure consistency of outputs.

Example Subsets:
`animationBob_01`, `animationJack_02`, `animationVehicleA`

Example Representations:
`.MA`, `.ABC`, `.JSON`


### Yeti Cache

Cached out yeti fur simulation that originates from a yeti rig applied in the shot context.


### Yeti Rig

Yeti groom setup ready to be applied to a cached out character in the shot context.

### Render
