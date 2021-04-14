---
id: manager_naming
title: Naming Conventions
sidebar_label: Naming Conventions
---

:::note
This naming convention holds true for most of our pipeline. Please match it as close as possible even for projects and files that might be outside of pipeline scope at this point. Small errors count! The reason for given formatting is to allow people to understand the file at glance and that a script or a program can easily get meaningful information from your files without errors.
:::

## General rules

For more detailed rules and different file types, have a look at naming conventions for scenes and assets

-   Every file starts with file code based on a project it belongs to e.g. ‘tst_’, ‘drm_’
-   Optional subversion and comment always comes after the major version. v##.subversion_comment.
-   File names can only be composed of letters, numbers, underscores `_` and dots “.”
-   You can use snakeCase or CamelCase if you need more words in a section.  thisIsLongerSentenceInComment
-   No spaces in filenames. Ever!
-   Frame numbers are always separated by a period ”.”
-   If you're not sure use this template:

## Work files

**`{code}_{shot}_{task}_v001.ext`**

**`{code}_{asset}_{task}_v001.ext`**

**Examples:**

    prj_sh010_enviro_v001.ma
    prj_sh010_animation_v001.ma
    prj_sh010_comp_v001.nk

    prj_bob_modelling_v001.ma
    prj_bob_rigging_v001.ma
    prj_bob_lookdev_v001.ma

:::info
In all of the examples anything enclosed in curly brackets  { } is compulsory in the name.
Anything in square brackets [ ] is optional.
:::

## Published Assets

**`{code}_{asset}_{family}_{subset}_{version}_[comment].ext`**

**Examples:**

  prj_bob_model_main_v01.ma
  prj_bob_model_hires_v01.ma
  prj_bob_model_main_v01_clothes.ma
  prj_bob_model_main_v01_body.ma
  prj_bob_rig_main_v01.ma
  Prj_bob_look_main_v01.ma
  Prj_bob_look_wet_v01.ma
