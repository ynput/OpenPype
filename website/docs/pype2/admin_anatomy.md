---
id: admin_anatomy
title: Project Anatomy
sidebar_label: Folder Structure
---

## PROJECT Structure

This is example project structure when using Pype:

```text
Project
  ├───assets
  │   ├───Bob
  │   └───...
  └───episodes
      └───ep01
          └───sq01
              └───ep01_sq01_sh001
                  ├───publish
                  └───work
```

:::note Shot naming
We do strongly recommend to name shots with their full hierarchical name. Avalon doesn't allow two assets with same name in project. Therefore if you have for example:

```text
sequence01 / shot001
```
and then
```text
sequence02 / shot001
```
you'll run into trouble because there are now two `shot001`.

Better way is to use full qualified name for shot. So the above become:
```text
sequence01 / sequence01_shot001
```

This has two advantages: there will be no duplicities this way and artists can see just by looking at filename the whole hierarchy.
:::

## ASSET Structure

```text
Bob
  ├───publish
  │   ├───model
  │   │   ├───modelMain
  │   │   ├───modelProxy
  │   │   └───modelSculpt
  │   ├───workfile
  │   │   └───taskName
  │   ├───rig
  │   │   └───rigMain
  │   ├───look
  │   │   ├───lookMain
  │   │   │   └───v01
  │   │   │       └───texture
  │   │   └───lookWet
  │   ├───camera
  │   │   ├───camMain
  │   │   └───camLayout
  │   ├───cache
  │   │   ├───cacheChar01
  │   │   └───cacheRock01
  │   ├───vrproxy
  │   ├───fx
  │   └───setdress
  └───work
      ├───concept
      ├───fur
      ├───modelling
      ├───rig
      ├───look
      └───taskName
```
