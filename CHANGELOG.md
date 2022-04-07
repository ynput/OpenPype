# Changelog

## [3.9.3-nightly.2](https://github.com/pypeclub/OpenPype/tree/HEAD)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.2...HEAD)

### 📖 Documentation

- Website Docs: Manager Ftrack fix broken links [\#2979](https://github.com/pypeclub/OpenPype/pull/2979)

**🆕 New features**

- Ftrack: Add description integrator [\#3027](https://github.com/pypeclub/OpenPype/pull/3027)
- Publishing textures for Unreal [\#2988](https://github.com/pypeclub/OpenPype/pull/2988)
- Maya to Unreal: Static and Skeletal Meshes [\#2978](https://github.com/pypeclub/OpenPype/pull/2978)

**🚀 Enhancements**

- Ftrack: Add more options for note text of integrate ftrack note [\#3025](https://github.com/pypeclub/OpenPype/pull/3025)
- Console Interpreter: Changed how console splitter size are reused on show [\#3016](https://github.com/pypeclub/OpenPype/pull/3016)
- Deadline: Use more suitable name for sequence review logic [\#3015](https://github.com/pypeclub/OpenPype/pull/3015)
- Nuke: add concurrency attr to deadline job [\#3005](https://github.com/pypeclub/OpenPype/pull/3005)
- Deadline: priority configurable in Maya jobs [\#2995](https://github.com/pypeclub/OpenPype/pull/2995)
- Workfiles tool: Save as published workfiles [\#2937](https://github.com/pypeclub/OpenPype/pull/2937)

**🐛 Bug fixes**

- Deadline: Fixed default value of use sequence for review [\#3033](https://github.com/pypeclub/OpenPype/pull/3033)
- Settings UI: Version column can be extended so version are visible [\#3032](https://github.com/pypeclub/OpenPype/pull/3032)
- General: Fix import after movements [\#3028](https://github.com/pypeclub/OpenPype/pull/3028)
- Harmony: Added creating subset name for workfile from template [\#3024](https://github.com/pypeclub/OpenPype/pull/3024)
- AfterEffects: Added creating subset name for workfile from template [\#3023](https://github.com/pypeclub/OpenPype/pull/3023)
- General: Add example addons to ignored [\#3022](https://github.com/pypeclub/OpenPype/pull/3022)
- Maya: Remove missing import [\#3017](https://github.com/pypeclub/OpenPype/pull/3017)
- Ftrack: multiple  reviewable componets [\#3012](https://github.com/pypeclub/OpenPype/pull/3012)
- Tray publisher: Fixes after code movement [\#3010](https://github.com/pypeclub/OpenPype/pull/3010)
- Nuke: fixing unicode type detection in effect loaders [\#3002](https://github.com/pypeclub/OpenPype/pull/3002)
- Nuke: removing redundant Ftrack asset when farm publishing [\#2996](https://github.com/pypeclub/OpenPype/pull/2996)

**Merged pull requests:**

- Maya: Allow to select invalid camera contents if no cameras found [\#3030](https://github.com/pypeclub/OpenPype/pull/3030)
- General: adding limitations for pyright [\#2994](https://github.com/pypeclub/OpenPype/pull/2994)

## [3.9.2](https://github.com/pypeclub/OpenPype/tree/3.9.2) (2022-04-04)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.9.2-nightly.4...3.9.2)

### 📖 Documentation

- Documentation: Added mention of adding My Drive as a root [\#2999](https://github.com/pypeclub/OpenPype/pull/2999)
- Docs: Added MongoDB requirements [\#2951](https://github.com/pypeclub/OpenPype/pull/2951)
- Documentation: New publisher develop docs [\#2896](https://github.com/pypeclub/OpenPype/pull/2896)

**🆕 New features**

- nuke: bypass baking [\#2992](https://github.com/pypeclub/OpenPype/pull/2992)
- Multiverse: Initial Support [\#2908](https://github.com/pypeclub/OpenPype/pull/2908)

**🚀 Enhancements**

- Photoshop: create image without instance [\#3001](https://github.com/pypeclub/OpenPype/pull/3001)
- TVPaint: Render scene family [\#3000](https://github.com/pypeclub/OpenPype/pull/3000)
- Nuke: ReviewDataMov Read RAW attribute [\#2985](https://github.com/pypeclub/OpenPype/pull/2985)
- General: `METADATA\_KEYS` constant as `frozenset` for optimal immutable lookup [\#2980](https://github.com/pypeclub/OpenPype/pull/2980)
- General: Tools with host filters [\#2975](https://github.com/pypeclub/OpenPype/pull/2975)
- Hero versions: Use custom templates [\#2967](https://github.com/pypeclub/OpenPype/pull/2967)
- Slack: Added configurable maximum file size of review upload to Slack [\#2945](https://github.com/pypeclub/OpenPype/pull/2945)
- NewPublisher: Prepared implementation of optional pyblish plugin [\#2943](https://github.com/pypeclub/OpenPype/pull/2943)
- TVPaint: Extractor to convert PNG into EXR [\#2942](https://github.com/pypeclub/OpenPype/pull/2942)
- Workfiles: Open published workfiles [\#2925](https://github.com/pypeclub/OpenPype/pull/2925)
- General: Default modules loaded dynamically [\#2923](https://github.com/pypeclub/OpenPype/pull/2923)
- Nuke: Add no-audio Tag [\#2911](https://github.com/pypeclub/OpenPype/pull/2911)
- Ftrack: Fill workfile in custom attribute [\#2906](https://github.com/pypeclub/OpenPype/pull/2906)
- Nuke: improving readability [\#2903](https://github.com/pypeclub/OpenPype/pull/2903)

**🐛 Bug fixes**

- Hosts: Remove path existence checks in 'add\_implementation\_envs' [\#3004](https://github.com/pypeclub/OpenPype/pull/3004)
- Fix - remove doubled dot in workfile created from template [\#2998](https://github.com/pypeclub/OpenPype/pull/2998)
- PS: fix renaming subset incorrectly in PS [\#2991](https://github.com/pypeclub/OpenPype/pull/2991)
- Fix: Disable setuptools auto discovery [\#2990](https://github.com/pypeclub/OpenPype/pull/2990)
- AEL: fix opening existing workfile if no scene opened [\#2989](https://github.com/pypeclub/OpenPype/pull/2989)
- Maya: Don't do hardlinks on windows for look publishing [\#2986](https://github.com/pypeclub/OpenPype/pull/2986)
- Settings UI: Fix version completer on linux [\#2981](https://github.com/pypeclub/OpenPype/pull/2981)
- Photoshop: Fix creation of subset names in PS review and workfile [\#2969](https://github.com/pypeclub/OpenPype/pull/2969)
- Slack: Added default for review\_upload\_limit for Slack [\#2965](https://github.com/pypeclub/OpenPype/pull/2965)
- General: OIIO conversion for ffmeg can handle sequences [\#2958](https://github.com/pypeclub/OpenPype/pull/2958)
- Settings: Conditional dictionary avoid invalid logs [\#2956](https://github.com/pypeclub/OpenPype/pull/2956)
- General: Smaller fixes and typos [\#2950](https://github.com/pypeclub/OpenPype/pull/2950)
- LogViewer: Don't refresh on initialization [\#2949](https://github.com/pypeclub/OpenPype/pull/2949)
- nuke: python3 compatibility issue with `iteritems` [\#2948](https://github.com/pypeclub/OpenPype/pull/2948)
- General: anatomy data with correct task short key [\#2947](https://github.com/pypeclub/OpenPype/pull/2947)
- SceneInventory: Fix imports in UI [\#2944](https://github.com/pypeclub/OpenPype/pull/2944)
- Slack: add generic exception [\#2941](https://github.com/pypeclub/OpenPype/pull/2941)
- General: Python specific vendor paths on env injection [\#2939](https://github.com/pypeclub/OpenPype/pull/2939)
- General: More fail safe delete old versions [\#2936](https://github.com/pypeclub/OpenPype/pull/2936)
- Settings UI: Collapsed of collapsible wrapper works as expected [\#2934](https://github.com/pypeclub/OpenPype/pull/2934)
- Maya: Do not pass `set` to maya commands \(fixes support for older maya versions\) [\#2932](https://github.com/pypeclub/OpenPype/pull/2932)
- General: Don't print log record on OSError [\#2926](https://github.com/pypeclub/OpenPype/pull/2926)
- Flame: centos related debugging [\#2922](https://github.com/pypeclub/OpenPype/pull/2922)

**🔀 Refactored code**

- General: Move plugins register and discover [\#2935](https://github.com/pypeclub/OpenPype/pull/2935)
- General: Move Attribute Definitions from pipeline [\#2931](https://github.com/pypeclub/OpenPype/pull/2931)
- General: Removed silo references and terminal splash [\#2927](https://github.com/pypeclub/OpenPype/pull/2927)
- General: Move pipeline constants to OpenPype [\#2918](https://github.com/pypeclub/OpenPype/pull/2918)
- General: Move remaining plugins from avalon [\#2912](https://github.com/pypeclub/OpenPype/pull/2912)

**Merged pull requests:**

- Bump paramiko from 2.9.2 to 2.10.1 [\#2973](https://github.com/pypeclub/OpenPype/pull/2973)
- Bump minimist from 1.2.5 to 1.2.6 in /website [\#2954](https://github.com/pypeclub/OpenPype/pull/2954)
- Bump node-forge from 1.2.1 to 1.3.0 in /website [\#2953](https://github.com/pypeclub/OpenPype/pull/2953)
- Maya - added transparency into review creator [\#2952](https://github.com/pypeclub/OpenPype/pull/2952)

## [3.9.1](https://github.com/pypeclub/OpenPype/tree/3.9.1) (2022-03-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.9.1-nightly.3...3.9.1)

**🚀 Enhancements**

- Settings UI: Add simple tooltips for settings entities [\#2901](https://github.com/pypeclub/OpenPype/pull/2901)
- nuke: imageio adding ocio config version 1.2 [\#2897](https://github.com/pypeclub/OpenPype/pull/2897)
- Flame: support for comment with xml attribute overrides [\#2892](https://github.com/pypeclub/OpenPype/pull/2892)

**🐛 Bug fixes**

- General: Fix use of Anatomy roots [\#2904](https://github.com/pypeclub/OpenPype/pull/2904)
- Fixing gap detection in extract review [\#2902](https://github.com/pypeclub/OpenPype/pull/2902)
- Pyblish Pype - ensure current state is correct when entering new group order [\#2899](https://github.com/pypeclub/OpenPype/pull/2899)
- SceneInventory: Fix import of load function [\#2894](https://github.com/pypeclub/OpenPype/pull/2894)
- Harmony - fixed creator issue [\#2891](https://github.com/pypeclub/OpenPype/pull/2891)

**🔀 Refactored code**

- General: Reduce style usage to OpenPype repository [\#2889](https://github.com/pypeclub/OpenPype/pull/2889)

## [3.9.0](https://github.com/pypeclub/OpenPype/tree/3.9.0) (2022-03-14)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.9.0-nightly.9...3.9.0)

## [3.8.2](https://github.com/pypeclub/OpenPype/tree/3.8.2) (2022-02-07)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.8.2-nightly.3...3.8.2)

## [3.8.1](https://github.com/pypeclub/OpenPype/tree/3.8.1) (2022-02-01)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.8.1-nightly.3...3.8.1)

## [3.8.0](https://github.com/pypeclub/OpenPype/tree/3.8.0) (2022-01-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.8.0-nightly.7...3.8.0)

## [3.7.0](https://github.com/pypeclub/OpenPype/tree/3.7.0) (2022-01-04)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.7.0-nightly.14...3.7.0)

## [3.6.4](https://github.com/pypeclub/OpenPype/tree/3.6.4) (2021-11-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.7.0-nightly.1...3.6.4)

## [3.6.3](https://github.com/pypeclub/OpenPype/tree/3.6.3) (2021-11-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.6.3-nightly.1...3.6.3)

## [3.6.2](https://github.com/pypeclub/OpenPype/tree/3.6.2) (2021-11-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.6.2-nightly.2...3.6.2)

## [3.6.1](https://github.com/pypeclub/OpenPype/tree/3.6.1) (2021-11-16)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.6.1-nightly.1...3.6.1)

## [3.6.0](https://github.com/pypeclub/OpenPype/tree/3.6.0) (2021-11-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.6.0-nightly.6...3.6.0)

## [3.5.0](https://github.com/pypeclub/OpenPype/tree/3.5.0) (2021-10-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.5.0-nightly.8...3.5.0)

## [3.4.1](https://github.com/pypeclub/OpenPype/tree/3.4.1) (2021-09-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.4.1-nightly.1...3.4.1)

## [3.4.0](https://github.com/pypeclub/OpenPype/tree/3.4.0) (2021-09-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.4.0-nightly.6...3.4.0)

## [3.3.1](https://github.com/pypeclub/OpenPype/tree/3.3.1) (2021-08-20)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.3.1-nightly.1...3.3.1)

## [3.3.0](https://github.com/pypeclub/OpenPype/tree/3.3.0) (2021-08-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.3.0-nightly.11...3.3.0)

## [3.2.0](https://github.com/pypeclub/OpenPype/tree/3.2.0) (2021-07-13)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.2.0-nightly.7...3.2.0)

## [2.18.4](https://github.com/pypeclub/OpenPype/tree/2.18.4) (2021-06-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.3...2.18.4)

## [2.18.3](https://github.com/pypeclub/OpenPype/tree/2.18.3) (2021-06-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.2.0-nightly.2...2.18.3)

## [2.18.2](https://github.com/pypeclub/OpenPype/tree/2.18.2) (2021-06-16)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.1.0...2.18.2)

## [3.1.0](https://github.com/pypeclub/OpenPype/tree/3.1.0) (2021-06-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/CI/3.1.0-nightly.4...3.1.0)

# Changelog


## [3.0.0](https://github.com/pypeclub/openpype/tree/3.0.0)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.1...3.0.0)

### Configuration
- Studio Settings GUI: no more json configuration files.
- OpenPype Modules can be turned on and off.
- Easy to add Application versions.
- Per Project Environment and plugin management.
- Robust profile system for creating reviewables and burnins, with filtering based on Application, Task and data family.
- Configurable publish plugins. 
- Options to make any validator or extractor, optional or disabled.
- Color Management is now unified under anatomy settings.
- Subset naming and grouping is fully configurable.
- All project attributes can now be set directly in OpenPype settings.
- Studio Setting can be locked to prevent unwanted artist changes. 
- You can now add per project and per task type templates for workfile initialization in most hosts.
- Too many other individual configurable option to list in this changelog :)

### Local Settings
- Local Settings GUI where users can change certain option on individual basis.
    - Application executables.
    - Project roots.
    - Project site sync settings.

### Build, Installation and Deployments
- No requirements on artist machine.
- Fully distributed workflow possible.
- Self-contained installation.
- Available on all three major platforms.
- Automatic artist OpenPype updates.
- Studio OpenPype repository for updates distribution.
- Robust Build system.
- Safe studio update versioning with staging and production options.
- MacOS build generates .app and .dmg installer.
- Windows build with installer creation script.

### Misc
- System and diagnostic info tool in the tray.
- Launching application from Launcher indicates activity.
- All project roots are now named. Single root project are now achieved by having a single named root in the project anatomy.
- Every project root is cast into environment variable as well, so it can be used in DCC instead of absolute path (depends on DCC support for env vars).
- Basic support for task types, on top of task names.
- Timer now change automatically when the context is switched inside running application.
- 'Master" versions have been renamed to "Hero".
- Extract Burnins now supports file sequences and color settings.
- Extract Review support overscan cropping, better letterboxes and background colour fill.
- Delivery tool for copying and renaming any published assets in bulk.
- Harmony, Photoshop and After Effects now connect directly with OpenPype tray instead of spawning their own terminal.

### Project Manager GUI
- Create Projects.
- Create Shots and Assets.
- Create Tasks and assign task types.
- Fill required asset attributes.
- Validations for duplicated or unsupported names.
- Archive Assets.
- Move Asset within hierarchy.

### Site Sync (beta)
- Synchronization of published files between workstations and central storage.
- Ability to add arbitrary storage providers to the Site Sync system.
- Default setup includes Disk and Google Drive providers as examples.
- Access to availability information from Loader and Scene Manager.
- Sync queue GUI with filtering, error and status reporting.
- Site sync can be configured on a per-project basis.
- Bulk upload and download from the loader.

### Ftrack
- Actions have customisable roles.
- Settings on all actions are updated live and don't need openpype restart.
- Ftrack module can now be turned off completely.
- It is enough to specify ftrack server name and the URL will be formed correctly. So instead of mystudio.ftrackapp.com, it's possible to use simply: "mystudio".

### Editorial
- Fully OTIO based editorial publishing.
- Completely re-done Hiero publishing to be a lot simpler and faster.
- Consistent conforming from Resolve, Hiero and Standalone Publisher.

### Backend
- OpenPype and Avalon now always share the same database (in 2.x is was possible to split them).
- Major codebase refactoring to allow for better CI, versioning and control of individual integrations.
- OTIO is bundled with build.
- OIIO is bundled with build.
- FFMPEG is bundled with build.
- Rest API and host WebSocket servers have been unified into a single local webserver.
- Maya look assigner has been integrated into the main codebase.
- Publish GUI has been integrated into the main codebase.
- Studio and Project settings overrides are now stored in Mongo.
- Too many other backend fixes and tweaks to list :), you can see full changelog on github for those.
- OpenPype uses Poetry to manage it's virtual environment when running from code.
- all applications can be marked as python 2 or 3 compatible to make the switch a bit easier.


### Pull Requests since 3.0.0-rc.6


**Implemented enhancements:**

- settings: task types enum entity [\#1605](https://github.com/pypeclub/OpenPype/issues/1605)
- Settings: ignore keys in referenced schema [\#1600](https://github.com/pypeclub/OpenPype/issues/1600)
- Maya: support for frame steps and frame lists [\#1585](https://github.com/pypeclub/OpenPype/issues/1585)
- TVPaint: Publish workfile. [\#1548](https://github.com/pypeclub/OpenPype/issues/1548)
- Loader: Current Asset Button [\#1448](https://github.com/pypeclub/OpenPype/issues/1448)
- Hiero: publish with retiming [\#1377](https://github.com/pypeclub/OpenPype/issues/1377)
- Ask user to restart after changing global environments in settings [\#910](https://github.com/pypeclub/OpenPype/issues/910)
- add option to define paht to workfile template [\#895](https://github.com/pypeclub/OpenPype/issues/895)
- Harmony: move server console to system tray [\#676](https://github.com/pypeclub/OpenPype/issues/676)
- Standalone style [\#1630](https://github.com/pypeclub/OpenPype/pull/1630) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Faster hierarchical values push [\#1627](https://github.com/pypeclub/OpenPype/pull/1627) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Launcher tool style [\#1624](https://github.com/pypeclub/OpenPype/pull/1624) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Loader and Library loader enhancements [\#1623](https://github.com/pypeclub/OpenPype/pull/1623) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Tray style [\#1622](https://github.com/pypeclub/OpenPype/pull/1622) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya schemas cleanup [\#1610](https://github.com/pypeclub/OpenPype/pull/1610) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Settings: ignore keys in referenced schema [\#1608](https://github.com/pypeclub/OpenPype/pull/1608) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- settings: task types enum entity [\#1606](https://github.com/pypeclub/OpenPype/pull/1606) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Openpype style [\#1604](https://github.com/pypeclub/OpenPype/pull/1604) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- TVPaint: Publish workfile. [\#1597](https://github.com/pypeclub/OpenPype/pull/1597) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Nuke: add option to define path to workfile template [\#1571](https://github.com/pypeclub/OpenPype/pull/1571) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Crop overscan in Extract Review [\#1569](https://github.com/pypeclub/OpenPype/pull/1569) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Unreal and Blender: Material Workflow [\#1562](https://github.com/pypeclub/OpenPype/pull/1562) ([simonebarbieri](https://github.com/simonebarbieri))
- Harmony: move server console to system tray [\#1560](https://github.com/pypeclub/OpenPype/pull/1560) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Ask user to restart after changing global environments in settings [\#1550](https://github.com/pypeclub/OpenPype/pull/1550) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Hiero: publish with retiming [\#1545](https://github.com/pypeclub/OpenPype/pull/1545) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Fixed bugs:**

- Library loader load asset documents on OpenPype start [\#1603](https://github.com/pypeclub/OpenPype/issues/1603)
- Resolve: unable to load the same footage twice [\#1317](https://github.com/pypeclub/OpenPype/issues/1317)
- Resolve: unable to load footage [\#1316](https://github.com/pypeclub/OpenPype/issues/1316)
- Add required Python 2 modules [\#1291](https://github.com/pypeclub/OpenPype/issues/1291)
- GUi scaling with hires displays [\#705](https://github.com/pypeclub/OpenPype/issues/705)
- Maya: non unicode string in publish validation [\#673](https://github.com/pypeclub/OpenPype/issues/673)
- Nuke: Rendered Frame validation is triggered by multiple collections [\#156](https://github.com/pypeclub/OpenPype/issues/156)
- avalon-core debugging failing [\#80](https://github.com/pypeclub/OpenPype/issues/80)
- Only check arnold shading group if arnold is used [\#72](https://github.com/pypeclub/OpenPype/issues/72)
- Sync server Qt layout fix [\#1621](https://github.com/pypeclub/OpenPype/pull/1621) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Console Listener on Python 2 fix [\#1620](https://github.com/pypeclub/OpenPype/pull/1620) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Bug: Initialize blessed term only in console mode [\#1619](https://github.com/pypeclub/OpenPype/pull/1619) ([antirotor](https://github.com/antirotor))
- Settings template skip paths support wrappers [\#1618](https://github.com/pypeclub/OpenPype/pull/1618) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya capture 'isolate\_view' fix + minor corrections [\#1617](https://github.com/pypeclub/OpenPype/pull/1617) ([2-REC](https://github.com/2-REC))
- MacOs Fix launch of standalone publisher [\#1616](https://github.com/pypeclub/OpenPype/pull/1616) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- 'Delivery action' report fix + typos [\#1612](https://github.com/pypeclub/OpenPype/pull/1612) ([2-REC](https://github.com/2-REC))
- List append fix in mutable dict settings [\#1599](https://github.com/pypeclub/OpenPype/pull/1599) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Documentation: Maya: fix review [\#1598](https://github.com/pypeclub/OpenPype/pull/1598) ([antirotor](https://github.com/antirotor))
- Bugfix: Set certifi CA bundle for all platforms [\#1596](https://github.com/pypeclub/OpenPype/pull/1596) ([antirotor](https://github.com/antirotor))

**Merged pull requests:**

- Bump dns-packet from 1.3.1 to 1.3.4 in /website [\#1611](https://github.com/pypeclub/OpenPype/pull/1611) ([dependabot[bot]](https://github.com/apps/dependabot))
- Maya: Render workflow fixes [\#1607](https://github.com/pypeclub/OpenPype/pull/1607) ([antirotor](https://github.com/antirotor))
- Maya: support for frame steps and frame lists [\#1586](https://github.com/pypeclub/OpenPype/pull/1586) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- 3.0.0 - curated changelog [\#1284](https://github.com/pypeclub/OpenPype/pull/1284) ([mkolar](https://github.com/mkolar))

## [2.18.1](https://github.com/pypeclub/openpype/tree/2.18.1) (2021-06-03)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.0...2.18.1)

**Enhancements:**

- Faster hierarchical values push [\#1626](https://github.com/pypeclub/OpenPype/pull/1626)
- Feature Delivery in library loader [\#1549](https://github.com/pypeclub/OpenPype/pull/1549)
- Hiero: Initial frame publish support. [\#1172](https://github.com/pypeclub/OpenPype/pull/1172)

**Fixed bugs:**

- Maya capture 'isolate\_view' fix + minor corrections [\#1614](https://github.com/pypeclub/OpenPype/pull/1614)
- 'Delivery action' report fix +typos [\#1613](https://github.com/pypeclub/OpenPype/pull/1613)
- Delivery in LibraryLoader - fixed sequence issue [\#1590](https://github.com/pypeclub/OpenPype/pull/1590)
- FFmpeg filters in quote marks [\#1588](https://github.com/pypeclub/OpenPype/pull/1588)
- Ftrack delete action cause circular error [\#1581](https://github.com/pypeclub/OpenPype/pull/1581)
- Fix Maya playblast. [\#1566](https://github.com/pypeclub/OpenPype/pull/1566)
- More failsafes prevent errored runs. [\#1554](https://github.com/pypeclub/OpenPype/pull/1554)
- Celaction publishing [\#1539](https://github.com/pypeclub/OpenPype/pull/1539)
- celaction: app not starting [\#1533](https://github.com/pypeclub/OpenPype/pull/1533)

**Merged pull requests:**

- Maya: Render workflow fixes - 2.0 backport [\#1609](https://github.com/pypeclub/OpenPype/pull/1609)
- Maya Hardware support [\#1553](https://github.com/pypeclub/OpenPype/pull/1553)


## [CI/3.0.0-rc.6](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.6) (2021-05-27)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.5...CI/3.0.0-rc.6)

**Implemented enhancements:**

- Hiero: publish color and transformation soft-effects [\#1376](https://github.com/pypeclub/OpenPype/issues/1376)
- Get rid of `AVALON\_HIERARCHY` and `hiearchy` key on asset [\#432](https://github.com/pypeclub/OpenPype/issues/432)
- Sync to avalon do not store hierarchy key [\#1582](https://github.com/pypeclub/OpenPype/pull/1582) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Tools: launcher scripts for project manager [\#1557](https://github.com/pypeclub/OpenPype/pull/1557) ([antirotor](https://github.com/antirotor))
- Simple tvpaint publish [\#1555](https://github.com/pypeclub/OpenPype/pull/1555) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Feature Delivery in library loader [\#1546](https://github.com/pypeclub/OpenPype/pull/1546) ([kalisp](https://github.com/kalisp))
- Documentation: Dev and system build documentation [\#1543](https://github.com/pypeclub/OpenPype/pull/1543) ([antirotor](https://github.com/antirotor))
- Color entity [\#1542](https://github.com/pypeclub/OpenPype/pull/1542) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Extract review bg color [\#1534](https://github.com/pypeclub/OpenPype/pull/1534) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- TVPaint loader settings [\#1530](https://github.com/pypeclub/OpenPype/pull/1530) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender can initialize differente user script paths [\#1528](https://github.com/pypeclub/OpenPype/pull/1528) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender and Unreal: Improved Animation Workflow [\#1514](https://github.com/pypeclub/OpenPype/pull/1514) ([simonebarbieri](https://github.com/simonebarbieri))
- Hiero: publish color and transformation soft-effects [\#1511](https://github.com/pypeclub/OpenPype/pull/1511) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Fixed bugs:**

- OpenPype specific version issues [\#1583](https://github.com/pypeclub/OpenPype/issues/1583)
- Ftrack login server can't work without stderr [\#1576](https://github.com/pypeclub/OpenPype/issues/1576)
- Mac application launch [\#1575](https://github.com/pypeclub/OpenPype/issues/1575)
- Settings are not propagated to Nuke write nodes [\#1538](https://github.com/pypeclub/OpenPype/issues/1538)
- Subset names settings not applied for publishing [\#1537](https://github.com/pypeclub/OpenPype/issues/1537)
- Nuke: callback at start not setting colorspace [\#1412](https://github.com/pypeclub/OpenPype/issues/1412)
- Pype 3: Missing icon for Settings [\#1272](https://github.com/pypeclub/OpenPype/issues/1272)
- Blender: cannot initialize Avalon if BLENDER\_USER\_SCRIPTS is already used [\#1050](https://github.com/pypeclub/OpenPype/issues/1050)
- Ftrack delete action cause circular error [\#206](https://github.com/pypeclub/OpenPype/issues/206)
- Build: stop cleaning of pyc files in build directory [\#1592](https://github.com/pypeclub/OpenPype/pull/1592) ([antirotor](https://github.com/antirotor))
- Ftrack login server can't work without stderr [\#1591](https://github.com/pypeclub/OpenPype/pull/1591) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- FFmpeg filters in quote marks [\#1589](https://github.com/pypeclub/OpenPype/pull/1589) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- OpenPype specific version issues [\#1584](https://github.com/pypeclub/OpenPype/pull/1584) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Mac application launch [\#1580](https://github.com/pypeclub/OpenPype/pull/1580) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Ftrack delete action cause circular error [\#1579](https://github.com/pypeclub/OpenPype/pull/1579) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Hiero: publishing issues  [\#1578](https://github.com/pypeclub/OpenPype/pull/1578) ([jezscha](https://github.com/jezscha))
- Nuke: callback at start not setting colorspace [\#1561](https://github.com/pypeclub/OpenPype/pull/1561) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Bugfix  PS subset and quick review [\#1541](https://github.com/pypeclub/OpenPype/pull/1541) ([kalisp](https://github.com/kalisp))
- Settings are not propagated to Nuke write nodes [\#1540](https://github.com/pypeclub/OpenPype/pull/1540) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- OpenPype: Powershell scripts polishing [\#1536](https://github.com/pypeclub/OpenPype/pull/1536) ([antirotor](https://github.com/antirotor))
- Host name collecting fix [\#1535](https://github.com/pypeclub/OpenPype/pull/1535) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Handle duplicated task names in project manager [\#1531](https://github.com/pypeclub/OpenPype/pull/1531) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Validate is file attribute in settings schema [\#1529](https://github.com/pypeclub/OpenPype/pull/1529) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Merged pull requests:**

- Bump postcss from 8.2.8 to 8.3.0 in /website [\#1593](https://github.com/pypeclub/OpenPype/pull/1593) ([dependabot[bot]](https://github.com/apps/dependabot))
- User installation documentation [\#1532](https://github.com/pypeclub/OpenPype/pull/1532) ([64qam](https://github.com/64qam))

## [CI/3.0.0-rc.5](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.5) (2021-05-19)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.0...CI/3.0.0-rc.5)

**Implemented enhancements:**

- OpenPype: Build - Add progress bars [\#1524](https://github.com/pypeclub/OpenPype/pull/1524) ([antirotor](https://github.com/antirotor))
- Default environments per host imlementation [\#1522](https://github.com/pypeclub/OpenPype/pull/1522) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- OpenPype: use `semver` module for version resolution [\#1513](https://github.com/pypeclub/OpenPype/pull/1513) ([antirotor](https://github.com/antirotor))
- Feature Aftereffects setting cleanup documentation [\#1510](https://github.com/pypeclub/OpenPype/pull/1510) ([kalisp](https://github.com/kalisp))
- Feature Sync server settings enhancement [\#1501](https://github.com/pypeclub/OpenPype/pull/1501) ([kalisp](https://github.com/kalisp))
- Project manager [\#1396](https://github.com/pypeclub/OpenPype/pull/1396) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Fixed bugs:**

- Unified schema definition [\#874](https://github.com/pypeclub/OpenPype/issues/874)
- Maya: fix look assignment [\#1526](https://github.com/pypeclub/OpenPype/pull/1526) ([antirotor](https://github.com/antirotor))
- Bugfix Sync server local site issues [\#1523](https://github.com/pypeclub/OpenPype/pull/1523) ([kalisp](https://github.com/kalisp))
- Store as list dictionary check initial value with right type [\#1520](https://github.com/pypeclub/OpenPype/pull/1520) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya: wrong collection of playblasted frames [\#1515](https://github.com/pypeclub/OpenPype/pull/1515) ([mkolar](https://github.com/mkolar))
- Convert pyblish logs to string at the moment of logging [\#1512](https://github.com/pypeclub/OpenPype/pull/1512) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- 3.0 | nuke: fixing start\_at with option gui [\#1509](https://github.com/pypeclub/OpenPype/pull/1509) ([jezscha](https://github.com/jezscha))
- Tests: fix pype -\> openpype to make tests work again [\#1508](https://github.com/pypeclub/OpenPype/pull/1508) ([antirotor](https://github.com/antirotor))

**Merged pull requests:**

- OpenPype: disable submodule update with `--no-submodule-update` [\#1525](https://github.com/pypeclub/OpenPype/pull/1525) ([antirotor](https://github.com/antirotor))
- Ftrack without autosync in Pype 3 [\#1519](https://github.com/pypeclub/OpenPype/pull/1519) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Feature Harmony setting cleanup documentation [\#1506](https://github.com/pypeclub/OpenPype/pull/1506) ([kalisp](https://github.com/kalisp))
- Sync Server beginning of documentation [\#1471](https://github.com/pypeclub/OpenPype/pull/1471) ([kalisp](https://github.com/kalisp))
- Blender: publish layout json [\#1348](https://github.com/pypeclub/OpenPype/pull/1348) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

## [2.18.0](https://github.com/pypeclub/openpype/tree/2.18.0) (2021-05-18)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.4...2.18.0)

**Implemented enhancements:**

- Default environments per host imlementation [\#1405](https://github.com/pypeclub/OpenPype/issues/1405)
- Blender: publish layout json [\#1346](https://github.com/pypeclub/OpenPype/issues/1346)
- Ftrack without autosync in Pype 3 [\#1128](https://github.com/pypeclub/OpenPype/issues/1128)
- Launcher: started action indicator [\#1102](https://github.com/pypeclub/OpenPype/issues/1102)
- Launch arguments of applications [\#1094](https://github.com/pypeclub/OpenPype/issues/1094)
- Publish: instance info [\#724](https://github.com/pypeclub/OpenPype/issues/724)
- Review: ability to control review length [\#482](https://github.com/pypeclub/OpenPype/issues/482)
- Colorized recognition of creator result [\#394](https://github.com/pypeclub/OpenPype/issues/394)
- event assign user to started task [\#49](https://github.com/pypeclub/OpenPype/issues/49)
- rebuild containers from reference in maya [\#55](https://github.com/pypeclub/OpenPype/issues/55)
- nuke Load metadata [\#66](https://github.com/pypeclub/OpenPype/issues/66)
- Maya: Safer handling of expected render output names [\#1496](https://github.com/pypeclub/OpenPype/pull/1496) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- TVPaint: Increment workfile version on successfull publish. [\#1489](https://github.com/pypeclub/OpenPype/pull/1489) ([tokejepsen](https://github.com/tokejepsen))
- Use SubsetLoader and multiple contexts for delete\_old\_versions [\#1484](https://github.com/pypeclub/OpenPype/pull/1484) ([tokejepsen](https://github.com/tokejepsen))
- Maya: Use of multiple deadline servers [\#1483](https://github.com/pypeclub/OpenPype/pull/1483) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Igniter version resolution doesn't consider it's own version [\#1505](https://github.com/pypeclub/OpenPype/issues/1505)
- Maya: Safer handling of expected render output names [\#1159](https://github.com/pypeclub/OpenPype/issues/1159)
- Harmony: Invalid render output from non-conventionally named instance [\#871](https://github.com/pypeclub/OpenPype/issues/871)
- Existing subsets hints in creator [\#1503](https://github.com/pypeclub/OpenPype/pull/1503) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- nuke: space in node name breaking process [\#1494](https://github.com/pypeclub/OpenPype/pull/1494) ([jezscha](https://github.com/jezscha))
-  Maya: wrong collection of playblasted frames [\#1517](https://github.com/pypeclub/OpenPype/pull/1517) ([mkolar](https://github.com/mkolar))
- Existing subsets hints in creator [\#1502](https://github.com/pypeclub/OpenPype/pull/1502) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Use instance frame start instead of timeline. [\#1486](https://github.com/pypeclub/OpenPype/pull/1486) ([tokejepsen](https://github.com/tokejepsen))
- Maya: Redshift - set proper start frame on proxy [\#1480](https://github.com/pypeclub/OpenPype/pull/1480) ([antirotor](https://github.com/antirotor))

**Closed issues:**

- Nuke: wrong "star at" value on render load [\#1352](https://github.com/pypeclub/OpenPype/issues/1352)
- DV Resolve - loading/updating - image video [\#915](https://github.com/pypeclub/OpenPype/issues/915)

**Merged pull requests:**

- nuke: fixing start\_at with option gui [\#1507](https://github.com/pypeclub/OpenPype/pull/1507) ([jezscha](https://github.com/jezscha))

## [CI/3.0.0-rc.4](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.4) (2021-05-12)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.3...CI/3.0.0-rc.4)

**Implemented enhancements:**

- Resolve: documentation [\#1490](https://github.com/pypeclub/OpenPype/issues/1490)
- Hiero: audio to review [\#1378](https://github.com/pypeclub/OpenPype/issues/1378)
- nks color clips after publish [\#44](https://github.com/pypeclub/OpenPype/issues/44)
- Store data from modifiable dict as list [\#1504](https://github.com/pypeclub/OpenPype/pull/1504) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Use SubsetLoader and multiple contexts for delete\_old\_versions [\#1497](https://github.com/pypeclub/OpenPype/pull/1497) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Hiero: publish audio and add to review [\#1493](https://github.com/pypeclub/OpenPype/pull/1493) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Resolve: documentation [\#1491](https://github.com/pypeclub/OpenPype/pull/1491) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Change integratenew template profiles setting [\#1487](https://github.com/pypeclub/OpenPype/pull/1487) ([kalisp](https://github.com/kalisp))
- Settings tool cleanup [\#1477](https://github.com/pypeclub/OpenPype/pull/1477) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Sorted Applications and Tools in Custom attribute [\#1476](https://github.com/pypeclub/OpenPype/pull/1476) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- PS - group all published instances [\#1416](https://github.com/pypeclub/OpenPype/pull/1416) ([kalisp](https://github.com/kalisp))
- OpenPype: Support for Docker [\#1289](https://github.com/pypeclub/OpenPype/pull/1289) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Harmony: palettes publishing [\#1439](https://github.com/pypeclub/OpenPype/issues/1439)
- Photoshop: validation for already created images [\#1435](https://github.com/pypeclub/OpenPype/issues/1435)
- Nuke Extracts Thumbnail from frame out of shot range [\#963](https://github.com/pypeclub/OpenPype/issues/963)
- Instance in same Context repairing [\#390](https://github.com/pypeclub/OpenPype/issues/390)
- User Inactivity - Start timers sets wrong time [\#91](https://github.com/pypeclub/OpenPype/issues/91)
- Use instance frame start instead of timeline [\#1499](https://github.com/pypeclub/OpenPype/pull/1499) ([mkolar](https://github.com/mkolar))
- Various smaller fixes [\#1498](https://github.com/pypeclub/OpenPype/pull/1498) ([mkolar](https://github.com/mkolar))
- nuke: space in node name breaking process [\#1495](https://github.com/pypeclub/OpenPype/pull/1495) ([jezscha](https://github.com/jezscha))
- Codec determination in extract burnin [\#1492](https://github.com/pypeclub/OpenPype/pull/1492) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Undefined constant in subprocess module [\#1485](https://github.com/pypeclub/OpenPype/pull/1485) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- List entity catch add/remove item changes properly [\#1482](https://github.com/pypeclub/OpenPype/pull/1482) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Resolve: additional fixes of publishing workflow [\#1481](https://github.com/pypeclub/OpenPype/pull/1481) ([jezscha](https://github.com/jezscha))
- Photoshop: validation for already created images [\#1436](https://github.com/pypeclub/OpenPype/pull/1436) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Merged pull requests:**

- Maya: Support for looks on VRay Proxies [\#1443](https://github.com/pypeclub/OpenPype/pull/1443) ([antirotor](https://github.com/antirotor))

## [2.17.3](https://github.com/pypeclub/openpype/tree/2.17.3) (2021-05-06)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.3...2.17.3)

**Fixed bugs:**

- Nuke: workfile version synced to db version always  [\#1479](https://github.com/pypeclub/OpenPype/pull/1479) ([jezscha](https://github.com/jezscha))

## [CI/3.0.0-rc.3](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.3) (2021-05-05)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.2...CI/3.0.0-rc.3)

**Implemented enhancements:**

- Path entity with placeholder [\#1473](https://github.com/pypeclub/OpenPype/pull/1473) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Burnin custom font filepath [\#1472](https://github.com/pypeclub/OpenPype/pull/1472) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Poetry: Move to OpenPype [\#1449](https://github.com/pypeclub/OpenPype/pull/1449) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Mac SSL path needs to be relative to pype\_root [\#1469](https://github.com/pypeclub/OpenPype/issues/1469)
- Resolve: fix loading clips to timeline [\#1421](https://github.com/pypeclub/OpenPype/issues/1421)
- Wrong handling of slashes when loading on mac [\#1411](https://github.com/pypeclub/OpenPype/issues/1411)
- Nuke openpype3 [\#1342](https://github.com/pypeclub/OpenPype/issues/1342)
- Houdini launcher [\#1171](https://github.com/pypeclub/OpenPype/issues/1171)
- Fix SyncServer get\_enabled\_projects should handle global state [\#1475](https://github.com/pypeclub/OpenPype/pull/1475) ([kalisp](https://github.com/kalisp))
- Igniter buttons enable/disable fix [\#1474](https://github.com/pypeclub/OpenPype/pull/1474) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Mac SSL path needs to be relative to pype\_root [\#1470](https://github.com/pypeclub/OpenPype/pull/1470) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Resolve: 17 compatibility issues and load image sequences [\#1422](https://github.com/pypeclub/OpenPype/pull/1422) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

## [CI/3.0.0-rc.2](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.2) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.2...CI/3.0.0-rc.2)

**Implemented enhancements:**

- Extract burnins with sequences [\#1467](https://github.com/pypeclub/OpenPype/pull/1467) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Extract burnins with color setting [\#1466](https://github.com/pypeclub/OpenPype/pull/1466) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Fixed bugs:**

- Fix groups check in Python 2 [\#1468](https://github.com/pypeclub/OpenPype/pull/1468) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

## [2.17.2](https://github.com/pypeclub/openpype/tree/2.17.2) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.1...2.17.2)

**Implemented enhancements:**

- Forward/Backward compatible apps and tools with OpenPype 3 [\#1463](https://github.com/pypeclub/OpenPype/pull/1463) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

## [CI/3.0.0-rc.1](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.1) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.1...CI/3.0.0-rc.1)

**Implemented enhancements:**

- Only show studio settings to admins [\#1406](https://github.com/pypeclub/OpenPype/issues/1406)
- Ftrack specific settings save warning messages [\#1458](https://github.com/pypeclub/OpenPype/pull/1458) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Faster settings actions [\#1446](https://github.com/pypeclub/OpenPype/pull/1446) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Feature/sync server priority [\#1444](https://github.com/pypeclub/OpenPype/pull/1444) ([kalisp](https://github.com/kalisp))
- Faster settings UI loading [\#1442](https://github.com/pypeclub/OpenPype/pull/1442) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Igniter re-write [\#1441](https://github.com/pypeclub/OpenPype/pull/1441) ([mkolar](https://github.com/mkolar))
- Wrap openpype build into installers [\#1419](https://github.com/pypeclub/OpenPype/pull/1419) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Extract review first documentation [\#1404](https://github.com/pypeclub/OpenPype/pull/1404) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender PySide2 install guide [\#1403](https://github.com/pypeclub/OpenPype/pull/1403) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: deadline submission with gpu [\#1394](https://github.com/pypeclub/OpenPype/pull/1394) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Igniter: Reverse item filter for OpenPype version [\#1349](https://github.com/pypeclub/OpenPype/pull/1349) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- OpenPype Mongo URL definition [\#1450](https://github.com/pypeclub/OpenPype/issues/1450)
- Various typos and smaller fixes [\#1464](https://github.com/pypeclub/OpenPype/pull/1464) ([mkolar](https://github.com/mkolar))
- Validation of dynamic items in settings [\#1462](https://github.com/pypeclub/OpenPype/pull/1462) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- List can handle new items correctly [\#1459](https://github.com/pypeclub/OpenPype/pull/1459) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Settings actions process fix [\#1457](https://github.com/pypeclub/OpenPype/pull/1457) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Add to overrides actions fix [\#1456](https://github.com/pypeclub/OpenPype/pull/1456) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- OpenPype Mongo URL definition [\#1455](https://github.com/pypeclub/OpenPype/pull/1455) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Global settings save/load out of system settings [\#1447](https://github.com/pypeclub/OpenPype/pull/1447) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Keep metadata on remove overrides [\#1445](https://github.com/pypeclub/OpenPype/pull/1445) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: fixing undo for loaded mov and sequence [\#1432](https://github.com/pypeclub/OpenPype/pull/1432) ([jezscha](https://github.com/jezscha))
- ExtractReview skip empty strings from settings [\#1431](https://github.com/pypeclub/OpenPype/pull/1431) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Bugfix Sync server tweaks [\#1430](https://github.com/pypeclub/OpenPype/pull/1430) ([kalisp](https://github.com/kalisp))
- Hiero: missing thumbnail in review [\#1429](https://github.com/pypeclub/OpenPype/pull/1429) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Bugfix Maya in deadline for OpenPype [\#1428](https://github.com/pypeclub/OpenPype/pull/1428) ([kalisp](https://github.com/kalisp))
- AE - validation for duration was 1 frame shorter [\#1427](https://github.com/pypeclub/OpenPype/pull/1427) ([kalisp](https://github.com/kalisp))
- Houdini menu filename [\#1418](https://github.com/pypeclub/OpenPype/pull/1418) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Fix Avalon plugins attribute overrides [\#1413](https://github.com/pypeclub/OpenPype/pull/1413) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: submit to Deadline fails [\#1409](https://github.com/pypeclub/OpenPype/pull/1409) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Validate MongoDB Url on start [\#1407](https://github.com/pypeclub/OpenPype/pull/1407) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: fix set colorspace with new settings [\#1386](https://github.com/pypeclub/OpenPype/pull/1386) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- MacOs build and install issues [\#1380](https://github.com/pypeclub/OpenPype/pull/1380) ([mkolar](https://github.com/mkolar))

**Closed issues:**

- test [\#1452](https://github.com/pypeclub/OpenPype/issues/1452)

**Merged pull requests:**

- TVPaint frame range definition [\#1425](https://github.com/pypeclub/OpenPype/pull/1425) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Only show studio settings to admins [\#1420](https://github.com/pypeclub/OpenPype/pull/1420) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- TVPaint documentation [\#1305](https://github.com/pypeclub/OpenPype/pull/1305) ([64qam](https://github.com/64qam))

## [2.17.1](https://github.com/pypeclub/openpype/tree/2.17.1) (2021-04-30)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.0...2.17.1)

**Enhancements:**

- Nuke: deadline submission with gpu [\#1414](https://github.com/pypeclub/OpenPype/pull/1414)
- TVPaint frame range definition [\#1424](https://github.com/pypeclub/OpenPype/pull/1424)
- PS - group all published instances [\#1415](https://github.com/pypeclub/OpenPype/pull/1415)
- Add task name to context pop up. [\#1383](https://github.com/pypeclub/OpenPype/pull/1383)
- Enhance review letterbox feature. [\#1371](https://github.com/pypeclub/OpenPype/pull/1371)

**Fixed bugs:**

- Houdini menu filename [\#1417](https://github.com/pypeclub/OpenPype/pull/1417)
- AE - validation for duration was 1 frame shorter [\#1426](https://github.com/pypeclub/OpenPype/pull/1426)

**Merged pull requests:**

- Maya: Vray - problem getting all file nodes for look publishing [\#1399](https://github.com/pypeclub/OpenPype/pull/1399)
- Maya: Support for Redshift proxies [\#1360](https://github.com/pypeclub/OpenPype/pull/1360)

## [2.17.0](https://github.com/pypeclub/openpype/tree/2.17.0) (2021-04-20)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-beta.2...2.17.0)

**Enhancements:**

- Forward compatible ftrack group [\#1243](https://github.com/pypeclub/OpenPype/pull/1243)
- Settings in mongo as dict [\#1221](https://github.com/pypeclub/OpenPype/pull/1221)
- Maya: Make tx option configurable with presets [\#1328](https://github.com/pypeclub/OpenPype/pull/1328)
- TVPaint asset name validation [\#1302](https://github.com/pypeclub/OpenPype/pull/1302)
- TV Paint: Set initial project settings. [\#1299](https://github.com/pypeclub/OpenPype/pull/1299)
- TV Paint: Validate mark in and out. [\#1298](https://github.com/pypeclub/OpenPype/pull/1298)
- Validate project settings [\#1297](https://github.com/pypeclub/OpenPype/pull/1297)
- After Effects: added SubsetManager [\#1234](https://github.com/pypeclub/OpenPype/pull/1234)
- Show error message in pyblish UI [\#1206](https://github.com/pypeclub/OpenPype/pull/1206)

**Fixed bugs:**

- Hiero: fixing source frame from correct object [\#1362](https://github.com/pypeclub/OpenPype/pull/1362)
- Nuke: fix colourspace, prerenders and nuke panes opening [\#1308](https://github.com/pypeclub/OpenPype/pull/1308)
- AE remove orphaned instance from workfile - fix self.stub [\#1282](https://github.com/pypeclub/OpenPype/pull/1282)
- Nuke: deadline submission with search replaced env values from preset [\#1194](https://github.com/pypeclub/OpenPype/pull/1194)
- Ftrack custom attributes in bulks [\#1312](https://github.com/pypeclub/OpenPype/pull/1312)
- Ftrack optional pypclub role [\#1303](https://github.com/pypeclub/OpenPype/pull/1303)
- After Effects: remove orphaned instances [\#1275](https://github.com/pypeclub/OpenPype/pull/1275)
- Avalon schema names [\#1242](https://github.com/pypeclub/OpenPype/pull/1242)
- Handle duplication of Task name [\#1226](https://github.com/pypeclub/OpenPype/pull/1226)
- Modified path of plugin loads for Harmony and TVPaint [\#1217](https://github.com/pypeclub/OpenPype/pull/1217)
- Regex checks in profiles filtering [\#1214](https://github.com/pypeclub/OpenPype/pull/1214)
- Bulk mov strict task [\#1204](https://github.com/pypeclub/OpenPype/pull/1204)
- Update custom ftrack session attributes [\#1202](https://github.com/pypeclub/OpenPype/pull/1202)
- Nuke: write node colorspace ignore `default\(\)` label [\#1199](https://github.com/pypeclub/OpenPype/pull/1199)
- Nuke: reverse search to make it more versatile [\#1178](https://github.com/pypeclub/OpenPype/pull/1178)



## [2.16.0](https://github.com/pypeclub/pype/tree/2.16.0) (2021-03-22)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.3...2.16.0)

**Enhancements:**

- Nuke: deadline submit limit group filter [\#1167](https://github.com/pypeclub/pype/pull/1167)
- Maya: support for Deadline Group and Limit Groups - backport 2.x [\#1156](https://github.com/pypeclub/pype/pull/1156)
- Maya: fixes for Redshift support [\#1152](https://github.com/pypeclub/pype/pull/1152)
- Nuke: adding preset for a Read node name to all img and mov Loaders [\#1146](https://github.com/pypeclub/pype/pull/1146)
- nuke deadline submit with environ var from presets overrides [\#1142](https://github.com/pypeclub/pype/pull/1142)
- Change timers after task change [\#1138](https://github.com/pypeclub/pype/pull/1138)
- Nuke: shortcuts for Pype menu [\#1127](https://github.com/pypeclub/pype/pull/1127)
- Nuke: workfile template [\#1124](https://github.com/pypeclub/pype/pull/1124)
- Sites local settings by site name [\#1117](https://github.com/pypeclub/pype/pull/1117)
- Reset loader's asset selection on context change [\#1106](https://github.com/pypeclub/pype/pull/1106)
- Bulk mov render publishing [\#1101](https://github.com/pypeclub/pype/pull/1101)
- Photoshop: mark publishable instances [\#1093](https://github.com/pypeclub/pype/pull/1093)
- Added ability to define BG color for extract review [\#1088](https://github.com/pypeclub/pype/pull/1088)
- TVPaint extractor enhancement [\#1080](https://github.com/pypeclub/pype/pull/1080)
- Photoshop: added support for .psb in workfiles [\#1078](https://github.com/pypeclub/pype/pull/1078)
- Optionally add task to subset name [\#1072](https://github.com/pypeclub/pype/pull/1072)
- Only extend clip range when collecting. [\#1008](https://github.com/pypeclub/pype/pull/1008)
- Collect audio for farm reviews. [\#1073](https://github.com/pypeclub/pype/pull/1073)


**Fixed bugs:**

- Fix path spaces in jpeg extractor [\#1174](https://github.com/pypeclub/pype/pull/1174)
- Maya: Bugfix: superclass for CreateCameraRig [\#1166](https://github.com/pypeclub/pype/pull/1166)
- Maya: Submit to Deadline - fix typo in condition [\#1163](https://github.com/pypeclub/pype/pull/1163)
- Avoid dot in repre extension [\#1125](https://github.com/pypeclub/pype/pull/1125)
- Fix versions variable usage in standalone publisher [\#1090](https://github.com/pypeclub/pype/pull/1090)
- Collect instance data fix subset query [\#1082](https://github.com/pypeclub/pype/pull/1082)
- Fix getting the camera name. [\#1067](https://github.com/pypeclub/pype/pull/1067)
- Nuke: Ensure "NUKE\_TEMP\_DIR" is not part of the Deadline job environment. [\#1064](https://github.com/pypeclub/pype/pull/1064)

## [2.15.3](https://github.com/pypeclub/pype/tree/2.15.3) (2021-02-26)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.2...2.15.3)

**Enhancements:**

- Maya: speedup renderable camera collection [\#1053](https://github.com/pypeclub/pype/pull/1053)
- Harmony - add regex search to filter allowed task names for collectin… [\#1047](https://github.com/pypeclub/pype/pull/1047)

**Fixed bugs:**

- Ftrack integrate hierarchy fix [\#1085](https://github.com/pypeclub/pype/pull/1085)
- Explicit subset filter in anatomy instance data [\#1059](https://github.com/pypeclub/pype/pull/1059)
- TVPaint frame offset [\#1057](https://github.com/pypeclub/pype/pull/1057)
- Auto fix unicode strings [\#1046](https://github.com/pypeclub/pype/pull/1046)

## [2.15.2](https://github.com/pypeclub/pype/tree/2.15.2) (2021-02-19)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.1...2.15.2)

**Enhancements:**

- Maya: Vray scene publishing [\#1013](https://github.com/pypeclub/pype/pull/1013)

**Fixed bugs:**

- Fix entity move under project [\#1040](https://github.com/pypeclub/pype/pull/1040)
- smaller nuke fixes from production [\#1036](https://github.com/pypeclub/pype/pull/1036)
- TVPaint thumbnail extract fix [\#1031](https://github.com/pypeclub/pype/pull/1031)

## [2.15.1](https://github.com/pypeclub/pype/tree/2.15.1) (2021-02-12)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.0...2.15.1)

**Enhancements:**

- Delete version as loader action [\#1011](https://github.com/pypeclub/pype/pull/1011)
- Delete old versions [\#445](https://github.com/pypeclub/pype/pull/445)

**Fixed bugs:**

- PS - remove obsolete functions from pywin32 [\#1006](https://github.com/pypeclub/pype/pull/1006)
- Clone description of review session objects. [\#922](https://github.com/pypeclub/pype/pull/922)

## [2.15.0](https://github.com/pypeclub/pype/tree/2.15.0) (2021-02-09)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.6...2.15.0)

**Enhancements:**

- Resolve - loading and updating clips [\#932](https://github.com/pypeclub/pype/pull/932)
- Release/2.15.0 [\#926](https://github.com/pypeclub/pype/pull/926)
- Photoshop: add option for template.psd and prelaunch hook  [\#894](https://github.com/pypeclub/pype/pull/894)
- Nuke: deadline presets [\#993](https://github.com/pypeclub/pype/pull/993)
- Maya: Alembic only set attributes that exists. [\#986](https://github.com/pypeclub/pype/pull/986)
- Harmony: render local and handle fixes [\#981](https://github.com/pypeclub/pype/pull/981)
- PSD Bulk export of ANIM group [\#965](https://github.com/pypeclub/pype/pull/965)
- AE - added prelaunch hook for opening last or workfile from template [\#944](https://github.com/pypeclub/pype/pull/944)
- PS - safer handling of loading of workfile [\#941](https://github.com/pypeclub/pype/pull/941)
- Maya: Handling Arnold referenced AOVs [\#938](https://github.com/pypeclub/pype/pull/938)
- TVPaint: switch layer IDs for layer names during identification [\#903](https://github.com/pypeclub/pype/pull/903)
- TVPaint audio/sound loader [\#893](https://github.com/pypeclub/pype/pull/893)
- Clone review session with children. [\#891](https://github.com/pypeclub/pype/pull/891)
- Simple compositing data packager for freelancers [\#884](https://github.com/pypeclub/pype/pull/884)
- Harmony deadline submission [\#881](https://github.com/pypeclub/pype/pull/881)
- Maya: Optionally hide image planes from reviews. [\#840](https://github.com/pypeclub/pype/pull/840)
- Maya: handle referenced AOVs for Vray [\#824](https://github.com/pypeclub/pype/pull/824)
- DWAA/DWAB support on windows [\#795](https://github.com/pypeclub/pype/pull/795)
- Unreal: animation, layout and setdress updates [\#695](https://github.com/pypeclub/pype/pull/695)

**Fixed bugs:**

- Maya: Looks - disable hardlinks [\#995](https://github.com/pypeclub/pype/pull/995)
- Fix Ftrack custom attribute update [\#982](https://github.com/pypeclub/pype/pull/982)
- Prores ks in burnin script [\#960](https://github.com/pypeclub/pype/pull/960)
- terminal.py crash on import [\#839](https://github.com/pypeclub/pype/pull/839)
- Extract review handle bizarre pixel aspect ratio [\#990](https://github.com/pypeclub/pype/pull/990)
- Nuke: add nuke related env var to sumbission  [\#988](https://github.com/pypeclub/pype/pull/988)
- Nuke: missing preset's variable  [\#984](https://github.com/pypeclub/pype/pull/984)
- Get creator by name fix [\#979](https://github.com/pypeclub/pype/pull/979)
- Fix update of project's tasks on Ftrack sync [\#972](https://github.com/pypeclub/pype/pull/972)
- nuke: wrong frame offset in mov loader  [\#971](https://github.com/pypeclub/pype/pull/971)
- Create project structure action fix multiroot [\#967](https://github.com/pypeclub/pype/pull/967)
- PS: remove pywin installation from hook [\#964](https://github.com/pypeclub/pype/pull/964)
- Prores ks in burnin script [\#959](https://github.com/pypeclub/pype/pull/959)
- Subset family is now stored in subset document [\#956](https://github.com/pypeclub/pype/pull/956)
- DJV new version arguments [\#954](https://github.com/pypeclub/pype/pull/954)
- TV Paint: Fix single frame Sequence [\#953](https://github.com/pypeclub/pype/pull/953)
- nuke: missing `file` knob update  [\#933](https://github.com/pypeclub/pype/pull/933)
- Photoshop: Create from single layer was failing [\#920](https://github.com/pypeclub/pype/pull/920)
- Nuke: baking mov with correct colorspace inherited from write  [\#909](https://github.com/pypeclub/pype/pull/909)
- Launcher fix actions discover [\#896](https://github.com/pypeclub/pype/pull/896)
- Get the correct file path for the updated mov. [\#889](https://github.com/pypeclub/pype/pull/889)
- Maya: Deadline submitter - shared data access violation [\#831](https://github.com/pypeclub/pype/pull/831)
- Maya: Take into account vray master AOV switch [\#822](https://github.com/pypeclub/pype/pull/822)

**Merged pull requests:**

- Refactor blender to 3.0 format [\#934](https://github.com/pypeclub/pype/pull/934)

## [2.14.6](https://github.com/pypeclub/pype/tree/2.14.6) (2021-01-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.5...2.14.6)

**Fixed bugs:**

- Nuke: improving of hashing path  [\#885](https://github.com/pypeclub/pype/pull/885)

**Merged pull requests:**

- Hiero: cut videos with correct secons  [\#892](https://github.com/pypeclub/pype/pull/892)
- Faster sync to avalon preparation [\#869](https://github.com/pypeclub/pype/pull/869)

## [2.14.5](https://github.com/pypeclub/pype/tree/2.14.5) (2021-01-06)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.4...2.14.5)

**Merged pull requests:**

- Pype logger refactor [\#866](https://github.com/pypeclub/pype/pull/866)

## [2.14.4](https://github.com/pypeclub/pype/tree/2.14.4) (2020-12-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.3...2.14.4)

**Merged pull requests:**

- Fix - AE - added explicit cast to int [\#837](https://github.com/pypeclub/pype/pull/837)

## [2.14.3](https://github.com/pypeclub/pype/tree/2.14.3) (2020-12-16)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.2...2.14.3)

**Fixed bugs:**

- TVPaint repair invalid metadata [\#809](https://github.com/pypeclub/pype/pull/809)
- Feature/push hier value to nonhier action [\#807](https://github.com/pypeclub/pype/pull/807)
- Harmony: fix palette and image sequence loader [\#806](https://github.com/pypeclub/pype/pull/806)

**Merged pull requests:**

- respecting space in path [\#823](https://github.com/pypeclub/pype/pull/823)

## [2.14.2](https://github.com/pypeclub/pype/tree/2.14.2) (2020-12-04)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.1...2.14.2)

**Enhancements:**

- Collapsible wrapper in settings [\#767](https://github.com/pypeclub/pype/pull/767)

**Fixed bugs:**

- Harmony: template extraction and palettes thumbnails on mac [\#768](https://github.com/pypeclub/pype/pull/768)
- TVPaint store context to workfile metadata \(764\) [\#766](https://github.com/pypeclub/pype/pull/766)
- Extract review audio cut fix [\#763](https://github.com/pypeclub/pype/pull/763)

**Merged pull requests:**

- AE: fix publish after background load [\#781](https://github.com/pypeclub/pype/pull/781)
- TVPaint store members key [\#769](https://github.com/pypeclub/pype/pull/769)

## [2.14.1](https://github.com/pypeclub/pype/tree/2.14.1) (2020-11-27)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.0...2.14.1)

**Enhancements:**

- Settings required keys in modifiable dict [\#770](https://github.com/pypeclub/pype/pull/770)
- Extract review may not add audio to output [\#761](https://github.com/pypeclub/pype/pull/761)

**Fixed bugs:**

- After Effects: frame range, file format and render source scene fixes [\#760](https://github.com/pypeclub/pype/pull/760)
- Hiero: trimming review with clip event number  [\#754](https://github.com/pypeclub/pype/pull/754)
- TVPaint: fix updating of loaded subsets [\#752](https://github.com/pypeclub/pype/pull/752)
- Maya: Vray handling of default aov [\#748](https://github.com/pypeclub/pype/pull/748)
- Maya: multiple renderable cameras in layer didn't work [\#744](https://github.com/pypeclub/pype/pull/744)
- Ftrack integrate custom attributes fix [\#742](https://github.com/pypeclub/pype/pull/742)

## [2.14.0](https://github.com/pypeclub/pype/tree/2.14.0) (2020-11-23)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.7...2.14.0)

**Enhancements:**

- Render publish plugins abstraction [\#687](https://github.com/pypeclub/pype/pull/687)
- Shot asset build trigger status [\#736](https://github.com/pypeclub/pype/pull/736)
- Maya: add camera rig publishing option [\#721](https://github.com/pypeclub/pype/pull/721)
- Sort instances by label in pyblish gui  [\#719](https://github.com/pypeclub/pype/pull/719)
- Synchronize ftrack hierarchical and shot attributes [\#716](https://github.com/pypeclub/pype/pull/716)
- 686 standalonepublisher editorial from image sequences [\#699](https://github.com/pypeclub/pype/pull/699)
- Ask user to select non-default camera from scene or create a new. [\#678](https://github.com/pypeclub/pype/pull/678)
- TVPaint: image loader with options [\#675](https://github.com/pypeclub/pype/pull/675)
- Maya: Camera name can be added to burnins. [\#674](https://github.com/pypeclub/pype/pull/674)
- After Effects: base integration with loaders [\#667](https://github.com/pypeclub/pype/pull/667)
- Harmony: Javascript refactoring and overall stability improvements [\#666](https://github.com/pypeclub/pype/pull/666)

**Fixed bugs:**

- Bugfix Hiero Review / Plate representation publish [\#743](https://github.com/pypeclub/pype/pull/743)
- Asset fetch second fix [\#726](https://github.com/pypeclub/pype/pull/726)
- TVPaint extract review fix [\#740](https://github.com/pypeclub/pype/pull/740)
- After Effects: Review were not being sent to ftrack [\#738](https://github.com/pypeclub/pype/pull/738)
- Maya: vray proxy was not loading [\#722](https://github.com/pypeclub/pype/pull/722)
- Maya: Vray expected file fixes [\#682](https://github.com/pypeclub/pype/pull/682)
- Missing audio on farm submission. [\#639](https://github.com/pypeclub/pype/pull/639)

**Deprecated:**

- Removed artist view from pyblish gui [\#717](https://github.com/pypeclub/pype/pull/717)
- Maya: disable legacy override check for cameras [\#715](https://github.com/pypeclub/pype/pull/715)

**Merged pull requests:**

- Application manager [\#728](https://github.com/pypeclub/pype/pull/728)
- Feature \#664 3.0 lib refactor [\#706](https://github.com/pypeclub/pype/pull/706)
- Lib from illicit part 2 [\#700](https://github.com/pypeclub/pype/pull/700)
- 3.0 lib refactor - path tools [\#697](https://github.com/pypeclub/pype/pull/697)

## [2.13.7](https://github.com/pypeclub/pype/tree/2.13.7) (2020-11-19)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.6...2.13.7)

**Fixed bugs:**

- Standalone Publisher: getting fps from context instead of nonexistent entity  [\#729](https://github.com/pypeclub/pype/pull/729)

# Changelog

## [2.13.6](https://github.com/pypeclub/pype/tree/2.13.6) (2020-11-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.5...2.13.6)

**Fixed bugs:**

- Maya workfile version wasn't syncing with renders properly [\#711](https://github.com/pypeclub/pype/pull/711)
- Maya: Fix for publishing multiple cameras with review from the same scene [\#710](https://github.com/pypeclub/pype/pull/710)

## [2.13.5](https://github.com/pypeclub/pype/tree/2.13.5) (2020-11-12)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.4...2.13.5)

**Enhancements:**

- 3.0 lib refactor [\#664](https://github.com/pypeclub/pype/issues/664)

**Fixed bugs:**

- Wrong thumbnail file was picked when publishing sequence in standalone publisher [\#703](https://github.com/pypeclub/pype/pull/703)
- Fix: Burnin data pass and FFmpeg tool check [\#701](https://github.com/pypeclub/pype/pull/701)

## [2.13.4](https://github.com/pypeclub/pype/tree/2.13.4) (2020-11-09)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.3...2.13.4)

**Enhancements:**

- AfterEffects integration with Websocket [\#663](https://github.com/pypeclub/pype/issues/663)

**Fixed bugs:**

- Photoshop uhiding hidden layers [\#688](https://github.com/pypeclub/pype/issues/688)
- \#688 - Fix publishing hidden layers [\#692](https://github.com/pypeclub/pype/pull/692)

**Closed issues:**

- Nuke Favorite directories "shot dir" "project dir" - not working [\#684](https://github.com/pypeclub/pype/issues/684)

**Merged pull requests:**

- Nuke Favorite directories "shot dir" "project dir" - not working \#684 [\#685](https://github.com/pypeclub/pype/pull/685)

## [2.13.3](https://github.com/pypeclub/pype/tree/2.13.3) (2020-11-03)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.2...2.13.3)

**Enhancements:**

- TV paint base integration [\#612](https://github.com/pypeclub/pype/issues/612)

**Fixed bugs:**

- Fix ffmpeg executable path with spaces [\#680](https://github.com/pypeclub/pype/pull/680)
- Hotfix: Added default version number [\#679](https://github.com/pypeclub/pype/pull/679)

## [2.13.2](https://github.com/pypeclub/pype/tree/2.13.2) (2020-10-28)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.1...2.13.2)

**Fixed bugs:**

- Nuke: wrong conditions when fixing legacy write nodes [\#665](https://github.com/pypeclub/pype/pull/665)

## [2.13.1](https://github.com/pypeclub/pype/tree/2.13.1) (2020-10-23)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.0...2.13.1)

**Enhancements:**

- move maya look assigner to pype menu [\#292](https://github.com/pypeclub/pype/issues/292)

**Fixed bugs:**

- Layer name is not propagating to metadata in Photoshop [\#654](https://github.com/pypeclub/pype/issues/654)
- Loader in Photoshop fails with "can't set attribute" [\#650](https://github.com/pypeclub/pype/issues/650)
- Nuke Load mp4 wrong frame range [\#661](https://github.com/pypeclub/pype/issues/661)
- Hiero: Review video file adding one frame to the end [\#659](https://github.com/pypeclub/pype/issues/659)

## [2.13.0](https://github.com/pypeclub/pype/tree/2.13.0) (2020-10-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.5...2.13.0)

**Enhancements:**

- Deadline Output Folder [\#636](https://github.com/pypeclub/pype/issues/636)
- Nuke Camera Loader [\#565](https://github.com/pypeclub/pype/issues/565)
- Deadline publish job shows publishing output folder [\#649](https://github.com/pypeclub/pype/pull/649)
- Get latest version in lib [\#642](https://github.com/pypeclub/pype/pull/642)
- Improved publishing of multiple representation from SP [\#638](https://github.com/pypeclub/pype/pull/638)
- Launch TvPaint shot work file from within Ftrack [\#631](https://github.com/pypeclub/pype/pull/631)
- Add mp4 support for RV action. [\#628](https://github.com/pypeclub/pype/pull/628)
- Maya: allow renders to have version synced with workfile [\#618](https://github.com/pypeclub/pype/pull/618)
- Renaming nukestudio host folder to hiero [\#617](https://github.com/pypeclub/pype/pull/617)
- Harmony: More efficient publishing [\#615](https://github.com/pypeclub/pype/pull/615)
- Ftrack server action improvement [\#608](https://github.com/pypeclub/pype/pull/608)
- Deadline user defaults to pype username if present [\#607](https://github.com/pypeclub/pype/pull/607)
- Standalone publisher now has icon [\#606](https://github.com/pypeclub/pype/pull/606)
- Nuke render write targeting knob improvement [\#603](https://github.com/pypeclub/pype/pull/603)
- Animated pyblish gui [\#602](https://github.com/pypeclub/pype/pull/602)
- Maya: Deadline - make use of asset dependencies optional [\#591](https://github.com/pypeclub/pype/pull/591)
- Nuke: Publishing, loading and updating alembic cameras [\#575](https://github.com/pypeclub/pype/pull/575)
- Maya: add look assigner to pype menu even if scriptsmenu is not available [\#573](https://github.com/pypeclub/pype/pull/573)
- Store task types in the database [\#572](https://github.com/pypeclub/pype/pull/572)
- Maya: Tiled EXRs to scanline EXRs render option [\#512](https://github.com/pypeclub/pype/pull/512)
- Fusion basic integration [\#452](https://github.com/pypeclub/pype/pull/452)

**Fixed bugs:**

- Burnin script did not propagate ffmpeg output [\#640](https://github.com/pypeclub/pype/issues/640)
- Pyblish-pype spacer in terminal wasn't transparent [\#646](https://github.com/pypeclub/pype/pull/646)
- Lib subprocess without logger [\#645](https://github.com/pypeclub/pype/pull/645)
- Nuke: prevent crash if we only have single frame in sequence [\#644](https://github.com/pypeclub/pype/pull/644)
- Burnin script logs better output [\#641](https://github.com/pypeclub/pype/pull/641)
- Missing audio on farm submission. [\#639](https://github.com/pypeclub/pype/pull/639)
- review from imagesequence error [\#633](https://github.com/pypeclub/pype/pull/633)
- Hiero: wrong order of fps clip instance data collecting  [\#627](https://github.com/pypeclub/pype/pull/627)
- Add source for review instances. [\#625](https://github.com/pypeclub/pype/pull/625)
- Task processing in event sync [\#623](https://github.com/pypeclub/pype/pull/623)
- sync to avalon doesn t remove renamed task [\#619](https://github.com/pypeclub/pype/pull/619)
- Intent publish setting wasn't working with default value [\#562](https://github.com/pypeclub/pype/pull/562)
- Maya: Updating a look where the shader name changed, leaves the geo without a shader [\#514](https://github.com/pypeclub/pype/pull/514)

**Merged pull requests:**

- Avalon module without Qt [\#581](https://github.com/pypeclub/pype/pull/581)
- Ftrack module without Qt [\#577](https://github.com/pypeclub/pype/pull/577)

## [2.12.5](https://github.com/pypeclub/pype/tree/2.12.5) (2020-10-14)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.4...2.12.5)

**Enhancements:**

- Launch TvPaint shot work file from within Ftrack [\#629](https://github.com/pypeclub/pype/issues/629)

**Merged pull requests:**

- Harmony: Disable application launch logic [\#637](https://github.com/pypeclub/pype/pull/637)

## [2.12.4](https://github.com/pypeclub/pype/tree/2.12.4) (2020-10-08)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.3...2.12.4)

**Enhancements:**

- convert nukestudio to hiero host [\#616](https://github.com/pypeclub/pype/issues/616)
- Fusion basic integration  [\#451](https://github.com/pypeclub/pype/issues/451)

**Fixed bugs:**

- Sync to avalon doesn't remove renamed task [\#605](https://github.com/pypeclub/pype/issues/605)
- NukeStudio: FPS collecting into clip instances [\#624](https://github.com/pypeclub/pype/pull/624)

**Merged pull requests:**

- NukeStudio: small fixes [\#622](https://github.com/pypeclub/pype/pull/622)
- NukeStudio: broken order of plugins [\#620](https://github.com/pypeclub/pype/pull/620)

## [2.12.3](https://github.com/pypeclub/pype/tree/2.12.3) (2020-10-06)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.2...2.12.3)

**Enhancements:**

- Nuke Publish Camera [\#567](https://github.com/pypeclub/pype/issues/567)
- Harmony: open xstage file no matter of its name [\#526](https://github.com/pypeclub/pype/issues/526)
- Stop integration of unwanted data [\#387](https://github.com/pypeclub/pype/issues/387)
- Move avalon-launcher functionality to pype [\#229](https://github.com/pypeclub/pype/issues/229)
- avalon workfiles api [\#214](https://github.com/pypeclub/pype/issues/214)
- Store task types [\#180](https://github.com/pypeclub/pype/issues/180)
- Avalon Mongo Connection split [\#136](https://github.com/pypeclub/pype/issues/136)
- nk camera workflow [\#71](https://github.com/pypeclub/pype/issues/71)
- Hiero integration added [\#590](https://github.com/pypeclub/pype/pull/590)
- Anatomy instance data collection is substantially faster for many instances [\#560](https://github.com/pypeclub/pype/pull/560)

**Fixed bugs:**

- test issue [\#596](https://github.com/pypeclub/pype/issues/596)
- Harmony: empty scene contamination [\#583](https://github.com/pypeclub/pype/issues/583)
- Edit publishing in SP doesn't respect shot selection for publishing [\#542](https://github.com/pypeclub/pype/issues/542)
- Pathlib breaks compatibility with python2 hosts [\#281](https://github.com/pypeclub/pype/issues/281)
- Updating a look where the shader name changed leaves the geo without a shader [\#237](https://github.com/pypeclub/pype/issues/237)
- Better error handling [\#84](https://github.com/pypeclub/pype/issues/84)
- Harmony: function signature [\#609](https://github.com/pypeclub/pype/pull/609)
- Nuke: gizmo publishing error [\#594](https://github.com/pypeclub/pype/pull/594)
- Harmony: fix clashing namespace of called js functions [\#584](https://github.com/pypeclub/pype/pull/584)
- Maya: fix maya scene type preset exception [\#569](https://github.com/pypeclub/pype/pull/569)

**Closed issues:**

- Nuke Gizmo publishing [\#597](https://github.com/pypeclub/pype/issues/597)
- nuke gizmo publishing error [\#592](https://github.com/pypeclub/pype/issues/592)
- Publish EDL [\#579](https://github.com/pypeclub/pype/issues/579)
- Publish render from SP [\#576](https://github.com/pypeclub/pype/issues/576)
- rename ftrack custom attribute group to `pype` [\#184](https://github.com/pypeclub/pype/issues/184)

**Merged pull requests:**

- Audio file existence check [\#614](https://github.com/pypeclub/pype/pull/614)
- NKS small fixes [\#587](https://github.com/pypeclub/pype/pull/587)
- Standalone publisher editorial plugins interfering [\#580](https://github.com/pypeclub/pype/pull/580)

## [2.12.2](https://github.com/pypeclub/pype/tree/2.12.2) (2020-09-25)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.1...2.12.2)

**Enhancements:**

- pype config GUI [\#241](https://github.com/pypeclub/pype/issues/241)

**Fixed bugs:**

- Harmony: Saving heavy scenes will crash [\#507](https://github.com/pypeclub/pype/issues/507)
- Extract review a representation name with `\*\_burnin` [\#388](https://github.com/pypeclub/pype/issues/388)
- Hierarchy data was not considering active isntances [\#551](https://github.com/pypeclub/pype/pull/551)

## [2.12.1](https://github.com/pypeclub/pype/tree/2.12.1) (2020-09-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.0...2.12.1)

**Fixed bugs:**

- Pype: changelog.md is outdated [\#503](https://github.com/pypeclub/pype/issues/503)
- dependency security alert ! [\#484](https://github.com/pypeclub/pype/issues/484)
- Maya: RenderSetup is missing update [\#106](https://github.com/pypeclub/pype/issues/106)
- \<pyblish plugin\> extract effects creates new instance [\#78](https://github.com/pypeclub/pype/issues/78)

## [2.12.0](https://github.com/pypeclub/pype/tree/2.12.0) (2020-09-10)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.8...2.12.0)

**Enhancements:**

- Less mongo connections [\#509](https://github.com/pypeclub/pype/pull/509)
- Nuke: adding image loader  [\#499](https://github.com/pypeclub/pype/pull/499)
- Move launcher window to top if launcher action is clicked [\#450](https://github.com/pypeclub/pype/pull/450)
- Maya:  better tile rendering support in Pype [\#446](https://github.com/pypeclub/pype/pull/446)
- Implementation of non QML launcher [\#443](https://github.com/pypeclub/pype/pull/443)
- Optional skip review on renders. [\#441](https://github.com/pypeclub/pype/pull/441)
- Ftrack: Option to push status from task to latest version [\#440](https://github.com/pypeclub/pype/pull/440)
- Properly containerize image plane loads. [\#434](https://github.com/pypeclub/pype/pull/434)
- Option to keep the review files. [\#426](https://github.com/pypeclub/pype/pull/426)
- Isolate view on instance members. [\#425](https://github.com/pypeclub/pype/pull/425)
- Maya: Publishing of tile renderings on Deadline [\#398](https://github.com/pypeclub/pype/pull/398)
- Feature/little bit better logging gui [\#383](https://github.com/pypeclub/pype/pull/383)

**Fixed bugs:**

- Maya: Fix tile order for Draft Tile Assembler [\#511](https://github.com/pypeclub/pype/pull/511)
- Remove extra dash [\#501](https://github.com/pypeclub/pype/pull/501)
- Fix: strip dot from repre names in single frame renders [\#498](https://github.com/pypeclub/pype/pull/498)
- Better handling of destination during integrating [\#485](https://github.com/pypeclub/pype/pull/485)
- Fix: allow thumbnail creation for single frame renders [\#460](https://github.com/pypeclub/pype/pull/460)
- added missing argument to launch\_application in ftrack app handler [\#453](https://github.com/pypeclub/pype/pull/453)
- Burnins: Copy bit rate of input video to match quality. [\#448](https://github.com/pypeclub/pype/pull/448)
- Standalone publisher is now independent from tray [\#442](https://github.com/pypeclub/pype/pull/442)
- Bugfix/empty enumerator attributes [\#436](https://github.com/pypeclub/pype/pull/436)
- Fixed wrong order of "other" category collapssing in publisher [\#435](https://github.com/pypeclub/pype/pull/435)
- Multiple reviews where being overwritten to one. [\#424](https://github.com/pypeclub/pype/pull/424)
- Cleanup plugin fail on instances without staging dir [\#420](https://github.com/pypeclub/pype/pull/420)
- deprecated -intra parameter in ffmpeg to new `-g` [\#417](https://github.com/pypeclub/pype/pull/417)
- Delivery action can now work with entered path [\#397](https://github.com/pypeclub/pype/pull/397)

**Merged pull requests:**

- Review on instance.data  [\#473](https://github.com/pypeclub/pype/pull/473)

## [2.11.8](https://github.com/pypeclub/pype/tree/2.11.8) (2020-08-27)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.7...2.11.8)

**Enhancements:**

- DWAA support for Maya [\#382](https://github.com/pypeclub/pype/issues/382)
- Isolate View on Playblast [\#367](https://github.com/pypeclub/pype/issues/367)
- Maya: Tile rendering [\#297](https://github.com/pypeclub/pype/issues/297)
- single pype instance running [\#47](https://github.com/pypeclub/pype/issues/47)
- PYPE-649: projects don't guarantee backwards compatible environment [\#8](https://github.com/pypeclub/pype/issues/8)
- PYPE-663: separate venv for each deployed version [\#7](https://github.com/pypeclub/pype/issues/7)

**Fixed bugs:**

- pyblish pype - other group is collapsed before plugins are done [\#431](https://github.com/pypeclub/pype/issues/431)
- Alpha white edges in harmony on PNGs [\#412](https://github.com/pypeclub/pype/issues/412)
- harmony image loader picks wrong representations [\#404](https://github.com/pypeclub/pype/issues/404)
- Clockify crash when response contain symbol not allowed by UTF-8 [\#81](https://github.com/pypeclub/pype/issues/81)

## [2.11.7](https://github.com/pypeclub/pype/tree/2.11.7) (2020-08-21)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.6...2.11.7)

**Fixed bugs:**

- Clean Up Baked Movie [\#369](https://github.com/pypeclub/pype/issues/369)
- celaction last workfile [\#459](https://github.com/pypeclub/pype/pull/459)

## [2.11.6](https://github.com/pypeclub/pype/tree/2.11.6) (2020-08-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.5...2.11.6)

**Enhancements:**

- publisher app [\#56](https://github.com/pypeclub/pype/issues/56)

## [2.11.5](https://github.com/pypeclub/pype/tree/2.11.5) (2020-08-13)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.4...2.11.5)

**Enhancements:**

- Switch from master to equivalent [\#220](https://github.com/pypeclub/pype/issues/220)
- Standalone publisher now only groups sequence if the extension is known [\#439](https://github.com/pypeclub/pype/pull/439)

**Fixed bugs:**

- Logs have been disable for editorial by default to speed up publishing [\#433](https://github.com/pypeclub/pype/pull/433)
- additional fixes for celaction [\#430](https://github.com/pypeclub/pype/pull/430)
- Harmony: invalid variable scope in validate scene settings [\#428](https://github.com/pypeclub/pype/pull/428)
- new representation name for audio was not accepted [\#427](https://github.com/pypeclub/pype/pull/427)

## [2.11.4](https://github.com/pypeclub/pype/tree/2.11.4) (2020-08-10)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.3...2.11.4)

**Enhancements:**

- WebSocket server [\#135](https://github.com/pypeclub/pype/issues/135)
- standalonepublisher: editorial family features expansion \[master branch\] [\#411](https://github.com/pypeclub/pype/pull/411)

## [2.11.3](https://github.com/pypeclub/pype/tree/2.11.3) (2020-08-04)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.2...2.11.3)

**Fixed bugs:**

- Harmony: publishing performance issues [\#408](https://github.com/pypeclub/pype/pull/408)

## [2.11.2](https://github.com/pypeclub/pype/tree/2.11.2) (2020-07-31)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.1...2.11.2)

**Fixed bugs:**

- Ftrack to Avalon bug [\#406](https://github.com/pypeclub/pype/issues/406)

## [2.11.1](https://github.com/pypeclub/pype/tree/2.11.1) (2020-07-29)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.0...2.11.1)

**Merged pull requests:**

- Celaction: metadata json folder fixes on path  [\#393](https://github.com/pypeclub/pype/pull/393)
- CelAction - version up method taken fro pype.lib  [\#391](https://github.com/pypeclub/pype/pull/391)

<a name="2.11.0"></a>
## 2.11.0 ##

_**release date:** 27 July 2020_

**new:**
- _(blender)_ namespace support [\#341](https://github.com/pypeclub/pype/pull/341)
- _(blender)_ start end frames [\#330](https://github.com/pypeclub/pype/pull/330)
- _(blender)_ camera asset [\#322](https://github.com/pypeclub/pype/pull/322)
- _(pype)_ toggle instances per family in pyblish GUI [\#320](https://github.com/pypeclub/pype/pull/320)
- _(pype)_ current release version is now shown in the tray menu [#379](https://github.com/pypeclub/pype/pull/379)


**improved:**
- _(resolve)_ tagging for publish [\#239](https://github.com/pypeclub/pype/issues/239)
- _(pype)_ Support publishing a subset of shots with standalone editorial [\#336](https://github.com/pypeclub/pype/pull/336)
- _(harmony)_ Basic support for palettes [\#324](https://github.com/pypeclub/pype/pull/324)
- _(photoshop)_ Flag outdated containers on startup and publish. [\#309](https://github.com/pypeclub/pype/pull/309)
- _(harmony)_ Flag Outdated containers [\#302](https://github.com/pypeclub/pype/pull/302)
- _(photoshop)_ Publish review [\#298](https://github.com/pypeclub/pype/pull/298)
- _(pype)_ Optional Last workfile launch [\#365](https://github.com/pypeclub/pype/pull/365)


**fixed:**
- _(premiere)_ workflow fixes [\#346](https://github.com/pypeclub/pype/pull/346)
- _(pype)_ pype-setup does not work with space in path [\#327](https://github.com/pypeclub/pype/issues/327)
- _(ftrack)_ Ftrack delete action cause circular error [\#206](https://github.com/pypeclub/pype/issues/206)
- _(nuke)_ Priority was forced to 50 [\#345](https://github.com/pypeclub/pype/pull/345)
- _(nuke)_ Fix ValidateNukeWriteKnobs [\#340](https://github.com/pypeclub/pype/pull/340)
- _(maya)_ If camera attributes are connected, we can ignore them. [\#339](https://github.com/pypeclub/pype/pull/339)
- _(pype)_ stop appending of tools environment to existing env [\#337](https://github.com/pypeclub/pype/pull/337)
- _(ftrack)_ Ftrack timeout needs to look at AVALON\_TIMEOUT [\#325](https://github.com/pypeclub/pype/pull/325)
- _(harmony)_ Only zip files are supported. [\#310](https://github.com/pypeclub/pype/pull/310)
- _(pype)_ hotfix/Fix event server mongo uri [\#305](https://github.com/pypeclub/pype/pull/305)
- _(photoshop)_ Subset was not named or validated correctly. [\#304](https://github.com/pypeclub/pype/pull/304)



<a name="2.10.0"></a>
## 2.10.0 ##

_**release date:** 17 June 2020_

**new:**
- _(harmony)_ **Toon Boom Harmony** has been greatly extended to support rigging, scene build, animation and rendering workflows. [#270](https://github.com/pypeclub/pype/issues/270) [#271](https://github.com/pypeclub/pype/issues/271) [#190](https://github.com/pypeclub/pype/issues/190) [#191](https://github.com/pypeclub/pype/issues/191) [#172](https://github.com/pypeclub/pype/issues/172) [#168](https://github.com/pypeclub/pype/issues/168)
- _(pype)_ Added support for rudimentary **edl publishing** into individual shots. [#265](https://github.com/pypeclub/pype/issues/265)
- _(celaction)_ Simple **Celaction** integration has been added with support for workfiles and rendering. [#255](https://github.com/pypeclub/pype/issues/255)
- _(maya)_ Support for multiple job types when submitting to the farm. We can now render Maya or Standalone render jobs for Vray and Arnold (limited support for arnold) [#204](https://github.com/pypeclub/pype/issues/204)
- _(photoshop)_ Added initial support for Photoshop [#232](https://github.com/pypeclub/pype/issues/232)

**improved:**
- _(blender)_ Updated support for rigs and added support Layout family [#233](https://github.com/pypeclub/pype/issues/233) [#226](https://github.com/pypeclub/pype/issues/226)
- _(premiere)_ It is now possible to choose different storage root for workfiles of different task types. [#255](https://github.com/pypeclub/pype/issues/255)
- _(maya)_ Support for unmerged AOVs in Redshift multipart EXRs [#197](https://github.com/pypeclub/pype/issues/197)
- _(pype)_ Pype repository has been refactored in preparation for 3.0 release [#169](https://github.com/pypeclub/pype/issues/169)
- _(deadline)_ All file dependencies are now passed to deadline from maya to prevent premature start of rendering if caches or textures haven't been coppied over yet. [#195](https://github.com/pypeclub/pype/issues/195)
- _(nuke)_ Script validation can now be made optional. [#194](https://github.com/pypeclub/pype/issues/194)
- _(pype)_ Publishing can now be stopped at any time. [#194](https://github.com/pypeclub/pype/issues/194)

**fix:**
- _(pype)_ Pyblish-lite has been integrated into pype repository, plus various publishing GUI fixes. [#274](https://github.com/pypeclub/pype/issues/274) [#275](https://github.com/pypeclub/pype/issues/275) [#268](https://github.com/pypeclub/pype/issues/268) [#227](https://github.com/pypeclub/pype/issues/227) [#238](https://github.com/pypeclub/pype/issues/238)
- _(maya)_ Alembic extractor was getting wrong frame range type in certain scenarios [#254](https://github.com/pypeclub/pype/issues/254)
- _(maya)_ Attaching a render to subset in maya was not passing validation in certain scenarios  [#256](https://github.com/pypeclub/pype/issues/256)
- _(ftrack)_ Various small fixes to ftrack sync [#263](https://github.com/pypeclub/pype/issues/263) [#259](https://github.com/pypeclub/pype/issues/259)
- _(maya)_ Look extraction is now able to skp invalid connections in shaders [#207](https://github.com/pypeclub/pype/issues/207)



<a name="2.9.0"></a>
## 2.9.0 ##

_**release date:** 25 May 2020_

**new:**
- _(pype)_ Support for **Multiroot projects**. You can now store project data on multiple physical or virtual storages and target individual publishes to these locations. For instance render can be stored on a faster storage than the rest of the project. [#145](https://github.com/pypeclub/pype/issues/145), [#38](https://github.com/pypeclub/pype/issues/38)
- _(harmony)_ Basic implementation of **Toon Boom Harmony** has been added. [#142](https://github.com/pypeclub/pype/issues/142)
- _(pype)_ OSX support is in public beta now. There are issues to be expected, but the main implementation should be functional. [#141](https://github.com/pypeclub/pype/issues/141)


**improved:**

- _(pype)_ **Review extractor** has been completely rebuilt. It now supports granular filtering so you can create **multiple outputs** for different tasks, families or hosts. [#103](https://github.com/pypeclub/pype/issues/103), [#166](https://github.com/pypeclub/pype/issues/166), [#165](https://github.com/pypeclub/pype/issues/165)
- _(pype)_ **Burnin** generation had been extended to **support same multi-output filtering** as review extractor [#103](https://github.com/pypeclub/pype/issues/103)
- _(pype)_ Publishing file templates can now be specified in config for each individual family [#114](https://github.com/pypeclub/pype/issues/114)
- _(pype)_ Studio specific plugins can now be appended to pype standard publishing plugins. [#112](https://github.com/pypeclub/pype/issues/112)
- _(nukestudio)_ Reviewable clips no longer need to be previously cut, exported and re-imported to timeline. **Pype can now dynamically cut reviewable quicktimes** from continuous offline footage during publishing. [#23](https://github.com/pypeclub/pype/issues/23)
- _(deadline)_ Deadline can now correctly differentiate between staging and production pype. [#154](https://github.com/pypeclub/pype/issues/154)
- _(deadline)_ `PYPE_PYTHON_EXE` env variable can now be used to direct publishing to explicit python installation. [#120](https://github.com/pypeclub/pype/issues/120)
- _(nuke)_ Nuke now check for new version of loaded data on file open. [#140](https://github.com/pypeclub/pype/issues/140)
- _(nuke)_ frame range and limit checkboxes are now exposed on write node. [#119](https://github.com/pypeclub/pype/issues/119)



**fix:**

- _(nukestudio)_ Project Location was using backslashes which was breaking nukestudio native exporting in certains configurations [#82](https://github.com/pypeclub/pype/issues/82)
- _(nukestudio)_ Duplicity in hierarchy tags was prone to throwing publishing error [#130](https://github.com/pypeclub/pype/issues/130), [#144](https://github.com/pypeclub/pype/issues/144)
- _(ftrack)_ multiple stability improvements [#157](https://github.com/pypeclub/pype/issues/157), [#159](https://github.com/pypeclub/pype/issues/159), [#128](https://github.com/pypeclub/pype/issues/128), [#118](https://github.com/pypeclub/pype/issues/118), [#127](https://github.com/pypeclub/pype/issues/127)
- _(deadline)_ multipart EXRs were stopping review publishing on the farm. They are still not supported for automatic review generation, but the publish will go through correctly without the quicktime. [#155](https://github.com/pypeclub/pype/issues/155)
- _(deadline)_ If deadline is non-responsive it will no longer freeze host when publishing [#149](https://github.com/pypeclub/pype/issues/149)
- _(deadline)_ Sometimes deadline was trying to launch render before all the source data was coppied over. [#137](https://github.com/pypeclub/pype/issues/137) _(harmony)_ Basic implementation of **Toon Boom Harmony** has been added. [#142](https://github.com/pypeclub/pype/issues/142)
- _(nuke)_ Filepath knob wasn't updated properly. [#131](https://github.com/pypeclub/pype/issues/131)
- _(maya)_ When extracting animation, the "Write Color Set" options on the instance were not respected. [#108](https://github.com/pypeclub/pype/issues/108)
- _(maya)_ Attribute overrides for AOV only worked for the legacy render layers. Now it works for new render setup as well [#132](https://github.com/pypeclub/pype/issues/132)
- _(maya)_ Stability and usability improvements in yeti workflow [#104](https://github.com/pypeclub/pype/issues/104)



<a name="2.8.0"></a>
## 2.8.0 ##

_**release date:** 20 April 2020_

**new:**

- _(pype)_ Option to generate slates from json templates. [PYPE-628] [#26](https://github.com/pypeclub/pype/issues/26)
- _(pype)_ It is now possible to automate loading of published subsets into any scene. Documentation will follow :). [PYPE-611] [#24](https://github.com/pypeclub/pype/issues/24)

**fix:**

- _(maya)_ Some Redshift render tokens could break publishing. [PYPE-778] [#33](https://github.com/pypeclub/pype/issues/33)
- _(maya)_ Publish was not preserving maya file extension. [#39](https://github.com/pypeclub/pype/issues/39)
- _(maya)_ Rig output validator was failing on nodes without shapes. [#40](https://github.com/pypeclub/pype/issues/40)
- _(maya)_ Yeti caches can now be properly versioned up in the scene inventory. [#40](https://github.com/pypeclub/pype/issues/40)
- _(nuke)_ Build first workfiles was not accepting jpeg sequences. [#34](https://github.com/pypeclub/pype/issues/34)
- _(deadline)_ Trying to generate ffmpeg review from multipart EXRs no longer crashes publishing. [PYPE-781]
- _(deadline)_ Render publishing is more stable in multiplatform environments. [PYPE-775]



<a name="2.7.0"></a>
## 2.7.0 ##

_**release date:** 30 March 2020_

**new:**

- _(maya)_ Artist can now choose to load multiple references of the same subset at once [PYPE-646, PYPS-81]
- _(nuke)_ Option to use named OCIO colorspaces for review colour baking. [PYPS-82]
- _(pype)_ Pype can now work with `master` versions for publishing and loading. These are non-versioned publishes that are overwritten with the latest version during publish. These are now supported in all the GUIs, but their publishing is deactivated by default. [PYPE-653]
- _(blender)_ Added support for basic blender workflow. We currently support `rig`, `model` and `animation` families. [PYPE-768]
- _(pype)_ Source timecode can now be used in burn-ins. [PYPE-777]
- _(pype)_ Review outputs profiles can now specify delivery resolution different than project setting [PYPE-759]
- _(nuke)_ Bookmark to current context is now added automatically to all nuke browser windows. [PYPE-712]

**change:**

- _(maya)_ It is now possible to publish camera without. baking. Keep in mind that unbaked cameras can't be guaranteed to work in other hosts. [PYPE-595]
- _(maya)_ All the renders from maya are now grouped in the loader by their Layer name. [PYPE-482]
- _(nuke/hiero)_ Any publishes from nuke and hiero can now be versioned independently of the workfile. [PYPE-728]


**fix:**

- _(nuke)_ Mixed slashes caused issues in ocio config path.
- _(pype)_ Intent field in pyblish GUI was passing label instead of value to ftrack. [PYPE-733]
- _(nuke)_ Publishing of pre-renders was inconsistent. [PYPE-766]
- _(maya)_ Handles and frame ranges were inconsistent in various places during publishing.
- _(nuke)_ Nuke was crashing if it ran into certain missing knobs. For example DPX output missing `autocrop` [PYPE-774]
- _(deadline)_ Project overrides were not working properly with farm render publishing.
- _(hiero)_ Problems with single frame plates publishing.
- _(maya)_ Redshift RenderPass token were breaking render publishing. [PYPE-778]
- _(nuke)_ Build first workfile was not accepting jpeg sequences.
- _(maya)_ Multipart (Multilayer) EXRs were breaking review publishing due to FFMPEG incompatiblity [PYPE-781]


<a name="2.6.0"></a>
## 2.6.0 ##

_**release date:** 9 March 2020_

**change:**
- _(maya)_ render publishing has been simplified and made more robust. Render setup layers are now automatically added to publishing subsets and `render globals` family has been replaced with simple `render` [PYPE-570]
- _(avalon)_ change context and workfiles apps, have been merged into one, that allows both actions to be performed at the same time. [PYPE-747]
- _(pype)_ thumbnails are now automatically propagate to asset from the last published subset in the loader
- _(ftrack)_ publishing comment and intent are now being published to ftrack note as well as describtion. [PYPE-727]
- _(pype)_ when overriding existing version new old representations are now overriden, instead of the new ones just being appended. (to allow this behaviour, the version validator need to be disabled. [PYPE-690])
- _(pype)_ burnin preset has been significantly simplified. It now doesn't require passing function to each field, but only need the actual text template. to use this, all the current burnin PRESETS MUST BE UPDATED for all the projects.
- _(ftrack)_ credentials are now stored on a per server basis, so it's possible to switch between ftrack servers without having to log in and out. [PYPE-723]


**new:**
- _(pype)_ production and development deployments now have different colour of the tray icon. Orange for Dev and Green for production [PYPE-718]
- _(maya)_ renders can now be attached to a publishable subset rather than creating their own subset. For example it is possible to create a reviewable `look` or `model` render and have it correctly attached as a representation of the subsets [PYPE-451]
- _(maya)_ after saving current scene into a new context (as a new shot for instance), all the scene publishing subsets data gets re-generated automatically to match the new context [PYPE-532]
- _(pype)_ we now support project specific publish, load and create plugins [PYPE-740]
- _(ftrack)_ new action that allow archiving/deleting old published versions. User can keep how many of the latest version to keep when the action is ran. [PYPE-748, PYPE-715]
- _(ftrack)_ it is now possible to monitor and restart ftrack event server using ftrack action. [PYPE-658]
- _(pype)_ validator that prevent accidental overwrites of previously published versions. [PYPE-680]
- _(avalon)_ avalon core updated to version 5.6.0
- _(maya)_ added validator to make sure that relative paths are used when publishing arnold standins.
- _(nukestudio)_ it is now possible to extract and publish audio family from clip in nuke studio [PYPE-682]

**fix**:
- _(maya)_ maya set framerange button was ignoring handles [PYPE-719]
- _(ftrack)_ sync to avalon was sometime crashing when ran on empty project
- _(nukestudio)_ publishing same shots after they've been previously archived/deleted would result in a crash. [PYPE-737]
- _(nuke)_ slate workflow was breaking in certain scenarios. [PYPE-730]
- _(pype)_ rendering publish workflow has been significantly improved to prevent error resulting from implicit render collection. [PYPE-665, PYPE-746]
- _(pype)_ launching application on a non-synced project resulted in obscure [PYPE-528]
- _(pype)_ missing keys in burnins no longer result in an error. [PYPE-706]
- _(ftrack)_ create folder structure action was sometimes failing for project managers due to wrong permissions.
- _(Nukestudio)_ using `source` in the start frame tag could result in wrong frame range calculation
- _(ftrack)_ sync to avalon action and event have been improved by catching more edge cases and provessing them properly.


<a name="2.5"></a>
## 2.5.0 ##

_**release date:** 11 Feb 2020_

**change:**
- _(pype)_ added many logs for easier debugging
- _(pype)_ review presets can now be separated between 2d and 3d renders [PYPE-693]
- _(pype)_ anatomy module has been greatly improved to allow for more dynamic pulblishing and faster debugging [PYPE-685]
- _(pype)_ avalon schemas have been moved from `pype-config` to `pype` repository, for simplification. [PYPE-670]
- _(ftrack)_ updated to latest ftrack API
- _(ftrack)_ publishing comments now appear in ftrack also as a note on version with customisable category [PYPE-645]
- _(ftrack)_ delete asset/subset action had been improved. It is now able to remove multiple entities and descendants of the selected entities [PYPE-361, PYPS-72]
- _(workfiles)_ added date field to workfiles app [PYPE-603]
- _(maya)_ old deprecated loader have been removed in favour of a single unified reference loader (old scenes will upgrade automatically to the new loader upon opening) [PYPE-633, PYPE-697]
- _(avalon)_ core updated to 5.5.15 [PYPE-671]
- _(nuke)_ library loader is now available in nuke [PYPE-698]


**new:**
- _(pype)_ added pype render wrapper to allow rendering on mixed platform farms. [PYPE-634]
- _(pype)_ added `pype launch` command. It let's admin run applications with dynamically built environment based on the given context. [PYPE-634]
- _(pype)_ added support for extracting review sequences with burnins [PYPE-657]
- _(publish)_ users can now set intent next to a comment when publishing. This will then be reflected on an attribute in ftrack. [PYPE-632]
- _(burnin)_ timecode can now be added to burnin
- _(burnin)_ datetime keys can now be added to burnin and anatomy [PYPE-651]
- _(burnin)_ anatomy templates can now be used in burnins. [PYPE=626]
- _(nuke)_ new validator for render resolution
- _(nuke)_ support for attach slate to nuke renders [PYPE-630]
- _(nuke)_ png sequences were added to loaders
- _(maya)_ added maya 2020 compatibility [PYPE-677]
- _(maya)_ ability to publish and load .ASS standin sequences [PYPS-54]
- _(pype)_ thumbnails can now be published and are visible in the loader. `AVALON_THUMBNAIL_ROOT` environment variable needs to be set for this to work  [PYPE-573, PYPE-132]
- _(blender)_ base implementation of blender was added with publishing and loading of .blend files [PYPE-612]
- _(ftrack)_ new action for preparing deliveries [PYPE-639]


**fix**:
- _(burnin)_ more robust way of finding ffmpeg for burnins.
- _(pype)_ improved UNC paths remapping when sending to farm.
- _(pype)_ float frames sometimes made their way to representation context in database, breaking loaders [PYPE-668]
- _(pype)_ `pype install --force` was failing sometimes [PYPE-600]
- _(pype)_ padding in published files got calculated wrongly sometimes. It is now instead being always read from project anatomy. [PYPE-667]
- _(publish)_ comment publishing was failing in certain situations
- _(ftrack)_ multiple edge case scenario fixes in auto sync and sync-to-avalon action
- _(ftrack)_ sync to avalon now works on empty projects
- _(ftrack)_ thumbnail update event was failing when deleting entities [PYPE-561]
- _(nuke)_ loader applies proper colorspaces from Presets
- _(nuke)_ publishing handles didn't always work correctly [PYPE-686]
- _(maya)_ assembly publishing and loading wasn't working correctly




<a name="2.4.0"></a>
## 2.4.0 ##

_**release date:** 9 Dec 2019_

**change:**
- _(ftrack)_ version to status ftrack event can now be configured from Presets
  - based on preset `presets/ftracc/ftrack_config.json["status_version_to_task"]`
- _(ftrack)_ sync to avalon event has been completely re-written. It now supports most of the project management situations on ftrack including moving, renaming and deleting entities, updating attributes and working with tasks.
- _(ftrack)_ sync to avalon action has been also re-writen. It is now much faster (up to 100 times depending on a project structure), has much better logging and reporting on encountered problems, and is able to handle much more complex situations.
- _(ftrack)_ sync to avalon trigger by checking `auto-sync` toggle on ftrack [PYPE-504]
- _(pype)_ various new features in the REST api
- _(pype)_ new visual identity used across pype
- _(pype)_ started moving all requirements to pip installation rather than vendorising them in pype repository. Due to a few yet unreleased packages, this means that pype can temporarily be only installed in the offline mode.

**new:**
- _(nuke)_ support for publishing gizmos and loading them as viewer processes
- _(nuke)_ support for publishing nuke nodes from backdrops and loading them back
- _(pype)_ burnins can now work with start and end frames as keys
  - use keys `{frame_start}`, `{frame_end}` and `{current_frame}` in burnin preset to use them. [PYPS-44,PYPS-73, PYPE-602]
- _(pype)_ option to filter logs by user and level in loggin GUI
- _(pype)_ image family added to standalone publisher [PYPE-574]
- _(pype)_ matchmove family added to standalone publisher [PYPE-574]
- _(nuke)_ validator for comparing arbitrary knobs with values from presets
- _(maya)_ option to force maya to copy textures in the new look publish rather than hardlinking them
- _(pype)_ comments from pyblish GUI are now being added to ftrack version
- _(maya)_ validator for checking outdated containers in the scene
- _(maya)_ option to publish and load arnold standin sequence [PYPE-579, PYPS-54]

**fix**:
- _(pype)_ burnins were not respecting codec of the input video
- _(nuke)_ lot's of various nuke and nuke studio fixes across the board [PYPS-45]
- _(pype)_ workfiles app is not launching with the start of the app by default [PYPE-569]
- _(ftrack)_ ftrack integration during publishing was failing under certain situations [PYPS-66]
- _(pype)_ minor fixes in REST api
- _(ftrack)_ status change event was crashing when the target status was missing [PYPS-68]
- _(ftrack)_ actions will try to reconnect if they fail for some reason
- _(maya)_ problems with fps mapping when using float FPS values
- _(deadline)_ overall improvements to deadline publishing
- _(setup)_ environment variables are now remapped on the fly based on the platform pype is running on. This fixes many issues in mixed platform environments.


<a name="2.3.6"></a>
## 2.3.6 #

_**release date:** 27 Nov 2019_

**hotfix**:
- _(ftrack)_ was hiding important debug logo
- _(nuke)_ crashes during workfile publishing
- _(ftrack)_ event server crashes because of signal problems
- _(muster)_ problems with muster render submissions
- _(ftrack)_ thumbnail update event syntax errors


## 2.3.0 ##
_release date: 6 Oct 2019_

**new**:
- _(maya)_ support for yeti rigs and yeti caches
- _(maya)_ validator for comparing arbitrary attributes against ftrack
- _(pype)_ burnins can now show current date and time
- _(muster)_ pools can now be set in render globals in maya
- _(pype)_ Rest API has been implemented in beta stage
- _(nuke)_ LUT loader has been added
- _(pype)_ rudimentary user module has been added as preparation for user management
- _(pype)_ a simple logging GUI has been added to pype tray
- _(nuke)_ nuke can now bake input process into mov
- _(maya)_ imported models now have selection handle displayed by defaulting
- _(avalon)_ it's is now possible to load multiple assets at once using loader
- _(maya)_ added ability to automatically connect yeti rig to a mesh upon loading

**changed**:
- _(ftrack)_ event server now runs two parallel processes and is able to keep queue of events to process.
- _(nuke)_ task name is now added to all rendered subsets
- _(pype)_ adding more families to standalone publisher
- _(pype)_ standalone publisher now uses pyblish-lite
- _(pype)_ standalone publisher can now create review quicktimes
- _(ftrack)_ queries to ftrack were sped up
- _(ftrack)_ multiple ftrack action have been deprecated
- _(avalon)_ avalon upstream has been updated to 5.5.0
- _(nukestudio)_ published transforms can now be animated
-

**fix**:
- _(maya)_ fps popup button didn't work in some cases
- _(maya)_ geometry instances and references in maya were losing shader assignments
- _(muster)_ muster rendering templates were not working correctly
- _(maya)_ arnold tx texture conversion wasn't respecting colorspace set by the artist
- _(pype)_ problems with avalon db sync
- _(maya)_ ftrack was rounding FPS making it inconsistent
- _(pype)_ wrong icon names in Creator
- _(maya)_ scene inventory wasn't showing anything if representation was removed from database after it's been loaded to the scene
- _(nukestudio)_ multiple bugs squashed
- _(loader)_ loader was taking long time to show all the loading action when first launcher in maya

## 2.2.0 ##
_release date: 8 Sept 2019_

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(nuke)_ option to choose deadline chunk size on write nodes
- _(nukestudio)_ added option to publish soft effects (subTrackItems) from NukeStudio as subsets including LUT files. these can then be loaded in nuke or NukeStudio
- _(nuke)_ option to build nuke script from previously published latest versions of plate and render subsets.
- _(nuke)_ nuke writes now have deadline tab.
- _(ftrack)_ Prepare Project action can now be used for creating the base folder structure on disk and in ftrack, setting up all the initial project attributes and it automatically prepares `pype_project_config` folder for the given project.
- _(clockify)_ Added support for time tracking in clockify. This currently in addition to ftrack time logs, but does not completely replace them.
- _(pype)_ any attributes in Creator and Loader plugins can now be customised using pype preset system

**changed**:
- nukestudio now uses workio API for workfiles
- _(maya)_ "FIX FPS" prompt in maya now appears in the middle of the screen
- _(muster)_ can now be configured with custom templates
- _(pype)_ global publishing plugins can now be configured using presets as well as host specific ones


**fix**:
- wrong version retrieval from path in certain scenarios
- nuke reset resolution wasn't working in certain scenarios

## 2.1.0 ##
_release date: 6 Aug 2019_

A large cleanup release. Most of the change are under the hood.

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(pype)_ Added configurable option to add burnins to any generated quicktimes
- _(ftrack)_ Action that identifies what machines pype is running on.
- _(system)_ unify subprocess calls
- _(maya)_ add audio to review quicktimes
- _(nuke)_ add crop before write node to prevent overscan problems in ffmpeg
- **Nuke Studio** publishing and workfiles support
- **Muster** render manager support
- _(nuke)_ Framerange, FPS and Resolution are set automatically at startup
- _(maya)_ Ability to load published sequences as image planes
- _(system)_ Ftrack event that sets asset folder permissions based on task assignees in ftrack.
- _(maya)_ Pyblish plugin that allow validation of maya attributes
- _(system)_ added better startup logging to tray debug, including basic connection information
- _(avalon)_ option to group published subsets to groups in the loader
- _(avalon)_ loader family filters are working now

**changed**:
- change multiple key attributes to unify their behaviour across the pipeline
  - `frameRate` to `fps`
  - `startFrame` to `frameStart`
  - `endFrame` to `frameEnd`
  - `fstart` to `frameStart`
  - `fend` to `frameEnd`
  - `handle_start` to `handleStart`
  - `handle_end` to `handleEnd`
  - `resolution_width` to `resolutionWidth`
  - `resolution_height` to `resolutionHeight`
  - `pixel_aspect` to `pixelAspect`

- _(nuke)_ write nodes are now created inside group with only some attributes editable by the artist
- rendered frames are now deleted from temporary location after their publishing is finished.
- _(ftrack)_ RV action can now be launched from any entity
- after publishing only refresh button is now available in pyblish UI
- added context instance pyblish-lite so that artist knows if context plugin fails
- _(avalon)_ allow opening selected files using enter key
- _(avalon)_ core updated to v5.2.9 with our forked changes on top

**fix**:
- faster hierarchy retrieval from db
- _(nuke)_ A lot of stability enhancements
- _(nuke studio)_ A lot of stability enhancements
- _(nuke)_ now only renders a single write node on farm
- _(ftrack)_ pype would crash when launcher project level task
- work directory was sometimes not being created correctly
- major pype.lib cleanup. Removing of unused functions, merging those that were doing the same and general house cleaning.
- _(avalon)_ subsets in maya 2019 weren't behaving correctly in the outliner








