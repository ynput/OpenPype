---
id: artist_concepts
title: Key concepts
sidebar_label: Key Concepts
---

## Glossary

### Asset

In our pipeline all the main entities the project is made from are internally considered *'Assets'*. Episode, sequence, shot, character, prop, etc. All of these behave identically in the pipeline. Asset names need to be absolutely unique within the project because they are their key identifier.

### Subset

Usually, an asset needs to be created in multiple *'flavours'*. A character might have multiple different looks, model needs to be published in different resolutions, a standard animation rig might not be usable in a crowd system and so on. 'Subsets' are here to accommodate all this variety that might be needed within a single asset. A model might have subset: *'main'*, *'proxy'*, *'sculpt'*, while data of *'look'* family could have subsets *'main'*, *'dirty'*, *'damaged'*. Subsets have some recommendations for their names, but ultimately it's up to the artist to use them for separation of publishes when needed.

### Version

A numbered iteration of a given subset. Each version contains at least one [representation][daa74ebf].

  [daa74ebf]: #representation "representation"

### Representation

Each published variant can come out of the software in multiple representations. All of them hold exactly the same data, but in different formats. A model, for example, might be saved as `.OBJ`, Alembic, Maya geometry or as all of them, to be ready for pickup in any other applications supporting these formats.

### Family

Each published [subset][3b89d8e0] can have exactly one family assigned to it. Family determines the type of data that the subset holds. Family doesn't dictate the file type, but can enforce certain technical specifications. For example OpenPype default configuration expects `model` family to only contain geometry without any shaders or joints when it is published.


  [3b89d8e0]: #subset "subset"



### Host

General term for Software or Application supported by OpenPype and Avalon. These are usually DCC applications like Maya, Houdini or Nuke, but can also be a web based service like Ftrack or Clockify.


### Tool

Small piece of software usually dedicated to a particular purpose. Most of OpenPype and Avalon tools have GUI, but some are command line only.


### Publish

Process of exporting data from your work scene to versioned, immutable file that can be used by other artists in the studio.

### Load

Process of importing previously published subsets into your current scene, using any of the OpenPype tools.
Loading asset using proper tools will ensure that all your scene content stays version controlled and updatable at a later point.
