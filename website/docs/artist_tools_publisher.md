---
id: artist_tools_publisher
title: Publisher
sidebar_label: Publisher
description: Publish versioned work progress into the project.
---

# Publisher

Use publish to share your work with others. It collects, validates and exports the data in standardized way.

## Details

When you run pyblish, the UI is made of 2 main parts. On the left, you see all the items pyblish will be working with (called instances), and on the right a list of actions that are going to process these items.
Even though every task type has some pre-defined settings of what should be collected from the scene and what items will be published by default. You can technically publish any output type from any task type.
Each item is passed through multiple plugins, each doing a small piece of work. These are organized into 4 areas and run in sequence.

## Using Pyblish

In the best case scenario, you open pyblish from the Avalon menu, press play, wait for it to finish, and you’re done.
These are the steps in detail, for cases, where the default settings don’t work for you or you know that the task you’re working on, requires a different treatment.

### Collect

Finds all the important data in the scene and makes it ready for publishing

### Validate

Each validator makes sure your output complies to one particular condition. This could be anything from naming conventions, scene setting, to plugin usage. An item can only be published if all validators pass.

### Extract

Extractor takes the item and saves it to the disk. Usually to temporary location. Each extractor represents one file format and there can be multiple file formats exported for each item.

### Integrate

Integrator takes the extracted files, categorizes and moves them to a correct location on the disk or on the server.

