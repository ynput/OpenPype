---
id: artist_concepts
title: Key concepts
sidebar_label: Key Concepts
---

## Glossary

### Asset

In our pipeline all the main entities the project is made from are internally considered *'Assets'*. Episode, sequence, shot, character, prop, etc. All of these behave identically in the pipeline. Asset names need to be absolutely unique within the project because they are their key identifier.

OpenPype has a limitation regarding duplicated names. Name of assets must be unique across whole project.

### Subset

A published output from an asset results in a subset.

The subset type is referred to as [family](#family), for example a rig, pointcache, look.
A single asset can have many subsets, even of a single family, named [variants](#variant).
By default a subset is named as a combination of family + variant, sometimes prefixed with the task name (like workfile).

### Variant

Usually, an asset needs to be created in multiple *'flavours'*. A character might have multiple different looks, model needs to be published in different resolutions, a standard animation rig might not be usable in a crowd system and so on. 'Variants' are here to accommodate all this variety that might be needed within a single asset. A model might have variant: *'main'*, *'proxy'*, *'sculpt'*, while data of *'look'* family could have subsets *'main'*, *'dirty'*, *'damaged'*. Variants have some recommendations for their names, but ultimately it's up to the artist to use them for separation of publishes when needed.

### Version

A numbered iteration of a given subset. Each version contains at least one [representation](#representation).

#### Hero version

A hero version is a version that is always the latest published version. When a new publish is generated its written over the previous hero version replacing it in-place as opposed to regular versions where each new publish is a higher version number.

This is an optional feature. The generation of hero versions can be completely disabled in OpenPype by an admin through the Studio Settings.

### Representation

Each published subset version can come out of the software in multiple representations. All of them hold exactly the same data, but in different formats. A model, for example, might be saved as `.OBJ`, Alembic, Maya geometry or as all of them, to be ready for pickup in any other applications supporting these formats.


#### Naming convention

At this moment names of assets, tasks, subsets or representations can contain only letters, numbers and underscore.

### Family

Each published [subset](#subset) can have exactly one family assigned to it. Family determines the type of data that the subset holds. Family doesn't dictate the file type, but can enforce certain technical specifications. For example OpenPype default configuration expects `model` family to only contain geometry without any shaders or joints when it is published.

### Task

A task defines a work area for an asset where an artist can work in. For example asset *characterA* can have tasks named *modeling* and *rigging*. Tasks also have types. Multiple tasks of the same type may exist on an asset. A task with type `fx` could for example appear twice as *fx_fire* and *fx_cloth*.

Without a task you cannot launch a host application.

### Workfile

The source scene file an artist works in within their task. These are versioned scene files and can be loaded and saved (automatically named) through the [workfiles tool](artist_tools_workfiles.md).

### Host

General term for Software or Application supported by OpenPype and Avalon. These are usually DCC applications like Maya, Houdini or Nuke, but can also be a web based service like Ftrack or Clockify.

### Tool

Small piece of software usually dedicated to a particular purpose. Most of OpenPype and Avalon tools have GUI, but some are command line only.


### Publish

Process of exporting data from your work scene to versioned, immutable file that can be used by other artists in the studio.

#### (Publish) Instance

A publish instance is a single entry which defines a publish output. Publish instances persist within the workfile. This way we can expect that a publish from a newer workfile will produce similar consistent versioned outputs.

### Load

Process of importing previously published subsets into your current scene, using any of the OpenPype tools.
Loading asset using proper tools will ensure that all your scene content stays version controlled and updatable at a later point.
