---
id: artist_tools_creator
title: Creator
sidebar_label: Creator
description: A tool to generate metadata for asset publishing.
---

# Creator

## Details

Despite the name, Creator isn't for making new content in your scene, but rather taking what's already in it and creating all the metadata your content needs to be published.

In Maya this means creating a set with everything you want to publish and assigning custom attributes to it so it gets picked up during publishing stage.

In Nuke it's either converting an existing write node to a publishable one, or simply creating a write node with all the correct settings and outputs already set.

## Usage

1.  Select what you want to publish from your scenes.
2.  Open *Creator* from OpenPype menu.
3.  Choose what family (data type) you need to export.
4.  Type the name for you export. This name is how others are going to be able to refer to this particular subset when loading it into their scenes. Every assets should have a Main subset, but can have any number of other variants.
5.  Click on *Create*.

